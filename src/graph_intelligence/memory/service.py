"""User persistent session memory domain service (Track 2)."""

import hashlib
from typing import Any, Dict, List, Optional, Set
from graph_intelligence.common.errors import DatabaseUnavailable, ValidationError
from graph_intelligence.common.falkordb_client import GraphStore
from graph_intelligence.common.ids import new_id, utcnow_iso
from graph_intelligence.common.result_models import ErrorCode, error_response, ok_response
from graph_intelligence.common.text import extract_keywords, normalize_term, squash, tokenize
from graph_intelligence.common.validation import (
    scan_for_secrets,
    validate_int_range,
    validate_list_size,
    validate_text_length,
)
from graph_intelligence.memory.queries import (
    ARCHIVE_SUMMARY_QUERY,
    CREATE_SESSION_SUMMARY_QUERY,
    CREATE_TASK_QUERY,
    FETCH_USER_CANDIDATES_QUERY,
    FIND_ACTIVE_BY_HASH_QUERY,
    LINK_ENTITY_QUERY,
    LINK_PROJECT_QUERY,
    LINK_SUPERSEDES_QUERY,
    MEMORY_STATUS_COUNTS_QUERY,
    MERGE_SESSION_QUERY,
    MERGE_USER_QUERY,
    READ_BACK_SUMMARY_QUERY,
    get_user_timeline_query,
)
from graph_intelligence.memory.retrieval import score_summary


class MemoryService:
    """Domain service managing user-scoped persistent session memory in FalkorDB."""

    def __init__(self, user_id: str, graph_name: Optional[str] = None):
        self.user_id = user_id
        self.store = GraphStore(graph_name=graph_name)

    def _resolve_project(self, project_name_or_id: Optional[str]) -> Optional[Dict[str, Any]]:
        """Resolve a project against the graph."""
        if not project_name_or_id:
            return None
        target_squashed = squash(project_name_or_id)
        projects = self.store.query("MATCH (p:Project) RETURN p.id AS id, p.name AS name")
        for p in projects:
            if squash(p.get("id", "")) == target_squashed or squash(p.get("name", "")) == target_squashed:
                return p
        return None

    def _resolve_entity(self, entity_str: str) -> Optional[Dict[str, Any]]:
        """Resolve an entity name or alias to a known company graph node."""
        target_squashed = squash(entity_str)
        cypher = """
        MATCH (n)
        WHERE any(label IN labels(n) WHERE label IN [
            'Company', 'Team', 'Person', 'Project', 'Service', 'Feature', 'Incident', 'Decision', 'Document'
        ])
        RETURN n.id AS id, n.name AS name, head(labels(n)) AS label, n.aliases AS aliases
        """
        nodes = self.store.query(cypher)
        for n in nodes:
            if squash(n.get("id", "")) == target_squashed or squash(n.get("name", "")) == target_squashed:
                return n
            aliases = n.get("aliases") or []
            if isinstance(aliases, str):
                aliases = [aliases]
            for a in aliases:
                if squash(a) == target_squashed:
                    return n
        return None

    def _find_adjacent_entity_ids(self, entity_ids: List[str]) -> Set[str]:
        """Find 1-hop adjacent entity IDs for given entity IDs."""
        if not entity_ids:
            return set()
        cypher = """
        MATCH (e)-[r]-(adj)
        WHERE e.id IN $eids
        RETURN DISTINCT adj.id AS id
        LIMIT 50
        """
        rows = self.store.query(cypher, {"eids": entity_ids})
        return {r["id"] for r in rows if r.get("id")}

    def remember_session_summary(
        self,
        title: str,
        summary: str,
        keywords: List[str],
        entities: List[Any] = [],
        project: Optional[str] = None,
        decisions: List[str] = [],
        open_tasks: List[str] = [],
        importance: str = "normal",
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Store a user-scoped session summary with entity and project links."""
        try:
            scan_for_secrets(title)
            scan_for_secrets(summary)
            for k in keywords:
                scan_for_secrets(k)
            for d in decisions:
                scan_for_secrets(d)
            for t in open_tasks:
                scan_for_secrets(t)

            validate_text_length(title, "title", 120)
            validate_text_length(summary, "summary", 4000)
            validate_list_size(keywords, "keywords", 20)
            validate_list_size(entities, "entities", 20)
            validate_list_size(decisions, "decisions", 20)
            validate_list_size(open_tasks, "open_tasks", 20)

            if importance not in ("low", "normal", "high"):
                importance = "normal"
        except ValidationError as e:
            return error_response(e.error_code, e.message)

        cleaned_keywords = extract_keywords(keywords)
        norm_title = normalize_term(title)
        norm_summary = normalize_term(summary)
        content_hash = hashlib.sha256(f"{norm_title}|{norm_summary}".encode("utf-8")).hexdigest()

        # Check deduplication against active summaries
        existing = self.store.query(
            FIND_ACTIVE_BY_HASH_QUERY,
            {"user_id": self.user_id, "content_hash": content_hash},
        )
        if existing:
            match = existing[0]
            return ok_response(
                summary_id=match["id"],
                title=match["title"],
                stored_at=match["created_at"],
                summary_version=match["summary_version"],
                status="active",
                deduplicated=True,
                message="Identical active session summary already exists for this user.",
            )

        now = utcnow_iso()
        sid = session_id or new_id("ses")
        summary_id = new_id("sum")

        # 1. Resolve project
        resolved_proj = self._resolve_project(project)
        project_id = resolved_proj["id"] if resolved_proj else None

        # 2. Resolve entities
        linked_entities: List[Dict[str, Any]] = []
        unresolved_entities: List[str] = []
        entity_keys: List[str] = []

        for item in entities:
            ent_name = item.get("name") if isinstance(item, dict) else str(item)
            if not ent_name:
                continue
            entity_keys.append(ent_name)
            resolved = self._resolve_entity(ent_name)
            if resolved:
                linked_entities.append({
                    "id": resolved["id"],
                    "name": resolved["name"],
                    "label": resolved["label"],
                })
            else:
                unresolved_entities.append(ent_name)

        # 3. DB write sequence
        # Ensure user node
        self.store.query(MERGE_USER_QUERY, {"user_id": self.user_id, "now": now})
        # Ensure session node
        self.store.query(MERGE_SESSION_QUERY, {"session_id": sid, "user_id": self.user_id, "now": now})

        # Create summary node and core edges
        create_params = {
            "id": summary_id,
            "user_id": self.user_id,
            "session_id": sid,
            "title": title,
            "summary": summary,
            "keywords": cleaned_keywords,
            "entity_keys": entity_keys,
            "decisions": decisions,
            "open_tasks_text": open_tasks,
            "project_id": project_id,
            "importance": importance,
            "status": "active",
            "summary_version": 1,
            "supersedes_id": None,
            "content_hash": content_hash,
            "now": now,
        }
        self.store.query(CREATE_SESSION_SUMMARY_QUERY, create_params)

        # Link project if resolved
        if project_id:
            self.store.query(LINK_PROJECT_QUERY, {
                "summary_id": summary_id,
                "user_id": self.user_id,
                "project_id": project_id,
            })

        # Link resolved entities
        for le in linked_entities:
            self.store.query(LINK_ENTITY_QUERY, {
                "summary_id": summary_id,
                "user_id": self.user_id,
                "entity_id": le["id"],
            })

        # Create task nodes
        for task_text in open_tasks:
            self.store.query(CREATE_TASK_QUERY, {
                "summary_id": summary_id,
                "user_id": self.user_id,
                "task_id": new_id("tsk"),
                "text": task_text,
                "status": "open",
                "now": now,
            })

        # Read back to confirm persistence
        readback = self.store.query(READ_BACK_SUMMARY_QUERY, {"id": summary_id, "user_id": self.user_id})
        if not readback:
            raise DatabaseUnavailable(f"Persistence verification failed for memory summary '{summary_id}'")

        return ok_response(
            summary_id=summary_id,
            title=title,
            stored_at=now,
            linked_entities=linked_entities,
            unresolved_entities=unresolved_entities,
            project=resolved_proj["name"] if resolved_proj else project,
            status="active",
            summary_version=1,
            deduplicated=False,
        )

    def search_user_memory(
        self,
        query: str,
        keywords: List[str] = [],
        entities: List[str] = [],
        project: Optional[str] = None,
        limit: int = 5,
        include_superseded: bool = False,
    ) -> Dict[str, Any]:
        """Search saved user summaries deterministically by relevance and scoring."""
        try:
            scan_for_secrets(query)
            for k in keywords:
                scan_for_secrets(k)
            for e in entities:
                scan_for_secrets(e)
            validate_text_length(query, "query", 300)
            limit = validate_int_range(limit, "limit", 1, 10)
        except ValidationError as e:
            return error_response(e.error_code, e.message)

        statuses = ["active"]
        if include_superseded:
            statuses.append("superseded")

        candidates = self.store.query(FETCH_USER_CANDIDATES_QUERY, {
            "user_id": self.user_id,
            "statuses": statuses,
        })

        if not candidates:
            return ok_response(
                found=False,
                results=[],
                note="No relevant saved memory.",
            )

        # Resolve entity IDs from query text/entities for graph-hop expansion
        resolved_query_entity_ids = []
        for ent_name in entities + tokenize(query):
            resolved = self._resolve_entity(ent_name)
            if resolved:
                resolved_query_entity_ids.append(resolved["id"])

        adjacent_entity_ids = self._find_adjacent_entity_ids(resolved_query_entity_ids)

        scored_results: List[Dict[str, Any]] = []
        for cand in candidates:
            score, matched_kw, matched_ent, match_reason = score_summary(
                candidate=cand,
                query_text=query,
                query_keywords=keywords,
                query_entities=entities,
                query_project=project,
                query_adjacent_entity_ids=adjacent_entity_ids,
            )
            if score >= 3.0:
                scored_results.append({
                    "summary_id": cand["id"],
                    "title": cand["title"],
                    "summary": cand["summary"],
                    "keywords": cand.get("keywords") or [],
                    "decisions": cand.get("decisions") or [],
                    "open_tasks": [t.get("text") for t in cand.get("tasks") or [] if isinstance(t, dict)] or cand.get("open_tasks_text") or [],
                    "project": cand.get("project_name") or cand.get("project_id"),
                    "status": cand["status"],
                    "summary_version": cand["summary_version"],
                    "created_at": cand["created_at"],
                    "updated_at": cand["updated_at"],
                    "score": score,
                    "matched_keywords": matched_kw,
                    "matched_entities": matched_ent,
                    "match_reason": match_reason,
                })

        scored_results.sort(key=lambda x: x["score"], reverse=True)
        top_results = scored_results[:limit]

        if not top_results:
            return ok_response(
                found=False,
                results=[],
                note="No relevant saved memory.",
            )

        return ok_response(
            found=True,
            results=top_results,
            note=f"Retrieved {len(top_results)} matching memory summary record(s).",
        )

    def update_user_memory(
        self,
        summary_id: str,
        update_type: str,
        updated_summary: Optional[str] = None,
        add_open_tasks: List[str] = [],
        complete_tasks: List[str] = [],
        reason: str = "",
        expected_version: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Update or supersede an existing user memory summary."""
        try:
            scan_for_secrets(updated_summary)
            scan_for_secrets(reason)
            for t in add_open_tasks:
                scan_for_secrets(t)
            for t in complete_tasks:
                scan_for_secrets(t)

            if update_type not in ("append_context", "correct", "supersede", "archive"):
                return error_response(ErrorCode.INVALID_INPUT, f"Invalid update_type '{update_type}'.")
        except ValidationError as e:
            return error_response(e.error_code, e.message)

        now = utcnow_iso()
        existing = self.store.query(READ_BACK_SUMMARY_QUERY, {"id": summary_id, "user_id": self.user_id})
        if not existing:
            return error_response(ErrorCode.NOT_FOUND, f"Memory summary '{summary_id}' not found.")

        old_record = existing[0]

        if expected_version is not None and old_record["summary_version"] != expected_version:
            return error_response(
                ErrorCode.CONFLICT,
                f"Version conflict: expected version {expected_version}, but summary is at version {old_record['summary_version']}.",
            )

        # 1. Archive
        if update_type == "archive":
            self.store.query(ARCHIVE_SUMMARY_QUERY, {"id": summary_id, "user_id": self.user_id, "now": now})
            return ok_response(
                summary_id=summary_id,
                status="archived",
                message=f"Memory summary '{summary_id}' has been archived.",
            )

        # 2. Append / Correct / Supersede
        new_version = old_record["summary_version"] + 1
        new_summary_id = new_id("sum")

        if update_type == "append_context":
            merged_summary = f"{old_record['summary']}\n\n[Addendum {now} - {reason}]:\n{updated_summary or ''}".strip()
        else:
            merged_summary = updated_summary or old_record["summary"]

        norm_title = normalize_term(old_record["title"])
        norm_summary = normalize_term(merged_summary)
        content_hash = hashlib.sha256(f"{norm_title}|{norm_summary}".encode("utf-8")).hexdigest()

        # Carry forward tasks
        existing_tasks = old_record.get("tasks") or []
        updated_tasks: List[Dict[str, str]] = []
        comp_task_squashed = {squash(ct) for ct in complete_tasks}

        for t in existing_tasks:
            if isinstance(t, dict):
                t_text = t.get("text", "")
                t_status = "done" if squash(t_text) in comp_task_squashed else t.get("status", "open")
                updated_tasks.append({"id": t.get("id", new_id("tsk")), "text": t_text, "status": t_status})

        for at in add_open_tasks:
            updated_tasks.append({"id": new_id("tsk"), "text": at, "status": "open"})

        open_tasks_text = [t["text"] for t in updated_tasks if t["status"] == "open"]

        # Insert new SessionSummary
        create_params = {
            "id": new_summary_id,
            "user_id": self.user_id,
            "session_id": old_record["session_id"],
            "title": old_record["title"],
            "summary": merged_summary,
            "keywords": old_record.get("keywords") or [],
            "entity_keys": old_record.get("entity_keys") or [],
            "decisions": old_record.get("decisions") or [],
            "open_tasks_text": open_tasks_text,
            "project_id": old_record.get("project_id"),
            "importance": old_record["importance"],
            "status": "active",
            "summary_version": new_version,
            "supersedes_id": summary_id,
            "content_hash": content_hash,
            "now": now,
        }
        self.store.query(CREATE_SESSION_SUMMARY_QUERY, create_params)

        # Mark old summary as superseded and link SUPERSEDES edge
        self.store.query(LINK_SUPERSEDES_QUERY, {
            "new_id": new_summary_id,
            "old_id": summary_id,
            "user_id": self.user_id,
            "now": now,
        })

        # Relink Project
        if old_record.get("project_id"):
            self.store.query(LINK_PROJECT_QUERY, {
                "summary_id": new_summary_id,
                "user_id": self.user_id,
                "project_id": old_record["project_id"],
            })

        # Relink entities
        for le in old_record.get("linked_entities") or []:
            if isinstance(le, dict) and le.get("id"):
                self.store.query(LINK_ENTITY_QUERY, {
                    "summary_id": new_summary_id,
                    "user_id": self.user_id,
                    "entity_id": le["id"],
                })

        # Re-create tasks
        for ut in updated_tasks:
            self.store.query(CREATE_TASK_QUERY, {
                "summary_id": new_summary_id,
                "user_id": self.user_id,
                "task_id": ut["id"],
                "text": ut["text"],
                "status": ut["status"],
                "now": now,
            })

        # Read back new summary
        readback = self.store.query(READ_BACK_SUMMARY_QUERY, {"id": new_summary_id, "user_id": self.user_id})
        if not readback:
            raise DatabaseUnavailable(f"Persistence verification failed for superseded memory '{new_summary_id}'")

        return ok_response(
            summary_id=new_summary_id,
            previous_id=summary_id,
            summary_version=new_version,
            status="active",
            message=f"Memory summary successfully updated from v{old_record['summary_version']} to v{new_version}.",
        )

    def get_user_memory_timeline(
        self,
        topic: Optional[str] = None,
        project: Optional[str] = None,
        include_superseded: bool = True,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """Retrieve historical timeline of summaries for the trusted user."""
        limit = min(max(1, limit), 50)
        statuses = ["active", "superseded"] if include_superseded else ["active"]

        q = get_user_timeline_query(limit=limit)
        rows = self.store.query(q, {"user_id": self.user_id, "statuses": statuses})

        items = []
        for r in rows:
            items.append({
                "summary_id": r["id"],
                "session_id": r["session_id"],
                "title": r["title"],
                "summary_version": r["summary_version"],
                "status": r["status"],
                "supersedes_id": r.get("supersedes_id"),
                "project": r.get("project_name"),
                "created_at": r["created_at"],
            })

        return ok_response(
            user_id=self.user_id,
            count=len(items),
            timeline=items,
        )

    def get_memory_status(self) -> Dict[str, Any]:
        """Return memory counts strictly for the configured trusted user."""
        res = self.store.query(MEMORY_STATUS_COUNTS_QUERY, {"user_id": self.user_id})
        if res:
            row = res[0]
            return ok_response(
                configured_user=self.user_id,
                active_count=row.get("active_count", 0),
                superseded_count=row.get("superseded_count", 0),
                archived_count=row.get("archived_count", 0),
            )
        return ok_response(
            configured_user=self.user_id,
            active_count=0,
            superseded_count=0,
            archived_count=0,
        )
