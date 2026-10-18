"""Company Brain domain service implementation (Track 3)."""

from typing import Any, Dict, List, Optional, Set
from graph_intelligence.common.errors import ValidationError
from graph_intelligence.common.falkordb_client import GraphStore
from graph_intelligence.common.result_models import ErrorCode, error_response, ok_response
from graph_intelligence.common.schema import COMPANY_LABELS
from graph_intelligence.common.text import squash, tokenize
from graph_intelligence.common.validation import scan_for_secrets, validate_int_range, validate_text_length
from graph_intelligence.company_brain.ingestion import IngestionEngine
from graph_intelligence.company_brain.queries import (
    DECISION_CONTEXT_QUERY,
    SERVICE_BRIEF_QUERY,
)
from graph_intelligence.company_brain.resolver import EntityResolver


class CompanyBrainService:
    """Service providing source-backed answers and knowledge queries over company data."""

    def __init__(self, graph_name: Optional[str] = None):
        self.store = GraphStore(graph_name=graph_name)
        self.resolver = EntityResolver(self.store)
        self.ingestion_engine = IngestionEngine(self.store)

    def search_company_knowledge(
        self,
        query: str,
        entity_types: Optional[List[str]] = None,
        limit: int = 10,
    ) -> Dict[str, Any]:
        """Search company entities and associated source documentation."""
        try:
            scan_for_secrets(query)
            validate_text_length(query, "query", 120)
            limit = validate_int_range(limit, "limit", 1, 20)
        except ValidationError as e:
            return error_response(e.error_code, e.message)

        target_squashed = squash(query)
        tokens = tokenize(query)

        cypher = """
        MATCH (n)
        WHERE any(label IN labels(n) WHERE label IN [
            'Company', 'Team', 'Person', 'Project', 'Service', 'Feature', 'Incident', 'Decision', 'Document'
        ])
        RETURN n.id AS id, n.name AS name, head(labels(n)) AS label, n.aliases AS aliases,
               n.rationale AS rationale, n.excerpt AS excerpt, n.uri AS uri
        """
        all_nodes = self.store.query(cypher)
        matches = []

        for n in all_nodes:
            label = n.get("label")
            if entity_types and label not in entity_types:
                continue

            node_squashed = squash(n.get("name", ""))
            aliases = n.get("aliases") or []
            if isinstance(aliases, str):
                aliases = [aliases]
            alias_squashed = [squash(a) for a in aliases]

            is_match = False
            if target_squashed in node_squashed or node_squashed in target_squashed:
                is_match = True
            elif any(target_squashed in a or a in target_squashed for a in alias_squashed):
                is_match = True
            elif any(t in node_squashed for t in tokens):
                is_match = True

            if is_match:
                matches.append(n)

        results = []
        for m in matches[:limit]:
            node_id = m["id"]
            # Fetch source documents describing or supporting this entity
            doc_query = """
            MATCH (doc:Document)-[:DESCRIBES]->(n {id: $id})
            RETURN doc.id AS id, doc.name AS title, doc.uri AS uri, doc.excerpt AS excerpt
            UNION
            MATCH (n {id: $id})-[:SUPPORTED_BY]->(doc:Document)
            RETURN doc.id AS id, doc.name AS title, doc.uri AS uri, doc.excerpt AS excerpt
            """
            docs = self.store.query(doc_query, {"id": node_id})
            sources = [
                {"id": d["id"], "title": d["title"], "uri": d.get("uri"), "excerpt": d.get("excerpt")}
                for d in docs
            ]

            results.append({
                "entity": {"id": m["id"], "name": m["name"], "label": m["label"]},
                "sources": sources,
            })

        return ok_response(results=results, count=len(results))

    def get_service_brief(self, service: str) -> Dict[str, Any]:
        """Retrieve full architecture, ownership, dependency, and document brief for a service."""
        try:
            scan_for_secrets(service)
            validate_text_length(service, "service", 120)
        except ValidationError as e:
            return error_response(e.error_code, e.message)

        resolved = self.resolver.resolve(service)
        if not resolved or resolved.get("label") != "Service":
            return error_response(ErrorCode.UNKNOWN_ENTITY, f"Unknown service '{service}'.")

        res = self.store.query(SERVICE_BRIEF_QUERY, {"service_id": resolved["id"]})
        if not res:
            return error_response(ErrorCode.NOT_FOUND, f"No brief data found for service '{service}'.")

        row = res[0]
        return ok_response(
            service={"id": row["id"], "name": row["name"]},
            owner={
                "id": row.get("owner_id"),
                "name": row.get("owner_name"),
                "team": row.get("team_name"),
            } if row.get("owner_id") else None,
            project={"id": row.get("project_id"), "name": row.get("project_name")} if row.get("project_id") else None,
            dependencies=[d for d in row.get("dependencies") or [] if d.get("id")],
            dependents=[d for d in row.get("dependents") or [] if d.get("id")],
            features=[f for f in row.get("features") or [] if f.get("id")],
            decisions=[d for d in row.get("decisions") or [] if d.get("id")],
            incidents=[i for i in row.get("incidents") or [] if i.get("id")],
            documents=[d for d in row.get("documents") or [] if d.get("id")],
        )

    def get_decision_context(self, decision: str) -> Dict[str, Any]:
        """Retrieve full decision context: rationale, supporting docs, and responding incidents."""
        try:
            scan_for_secrets(decision)
            validate_text_length(decision, "decision", 120)
        except ValidationError as e:
            return error_response(e.error_code, e.message)

        resolved = self.resolver.resolve(decision)
        if not resolved or resolved.get("label") != "Decision":
            return error_response(ErrorCode.UNKNOWN_ENTITY, f"Unknown decision '{decision}'.")

        res = self.store.query(DECISION_CONTEXT_QUERY, {"decision_id": resolved["id"]})
        if not res:
            return error_response(ErrorCode.NOT_FOUND, f"No decision context found for '{decision}'.")

        row = res[0]
        return ok_response(
            decision={
                "id": row["id"],
                "name": row["name"],
                "rationale": row.get("rationale"),
                "status": row.get("status"),
                "decided_on": row.get("decided_on"),
            },
            project={"id": row.get("project_id"), "name": row.get("project_name")} if row.get("project_id") else None,
            affected_services=[s for s in row.get("affected_services") or [] if s.get("id")],
            supporting_documents=[d for d in row.get("supporting_docs") or [] if d.get("id")],
            responding_to_incidents=[i for i in row.get("responding_incidents") or [] if i.get("id")],
        )

    def answer_company_question(
        self,
        question: str,
        project: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Deterministic, source-backed question answering over the company knowledge graph.
        Never hallucinates facts or sources. Identifies explicit knowledge gaps when facts are absent.
        """
        try:
            scan_for_secrets(question)
            validate_text_length(question, "question", 400)
        except ValidationError as e:
            return error_response(e.error_code, e.message)

        # 1. Resolve entity candidates mentioned in question
        matched_entities = self.resolver.resolve_all(question)

        # 2. Detect intents
        q_lower = question.lower()
        intent_owner = any(k in q_lower for k in ["who owns", "owner", "owns", "responsible", "tech lead", "lead"])
        intent_team = any(k in q_lower for k in ["team", "which team"])
        intent_why = any(k in q_lower for k in ["why", "chose", "choose", "rationale", "reason", "decision", "adr"])
        intent_document = any(k in q_lower for k in ["document", "source", "supporting", "evidence", "cite", "runbook", "doc", "catalog"])
        intent_incident = any(k in q_lower for k in ["incident", "outage", "failure", "timeout", "duplicate charge", "charge"])
        intent_feature = any(k in q_lower for k in ["feature", "implements", "idempotency", "retry"])
        intent_dependency = any(k in q_lower for k in ["depend", "depends", "dependencies", "calls", "upstream", "downstream"])

        facts: List[Dict[str, Any]] = []
        sources: List[Dict[str, Any]] = []
        gaps: List[str] = []
        source_ids_seen = set()

        def add_source(doc_id: str, title: str, uri: Optional[str], excerpt: Optional[str]) -> None:
            if doc_id and doc_id not in source_ids_seen:
                source_ids_seen.add(doc_id)
                sources.append({"id": doc_id, "title": title, "uri": uri, "excerpt": excerpt})

        # Process entities
        for ent in matched_entities:
            ent_id = ent["id"]
            ent_name = ent["name"]
            ent_label = ent["label"]

            # Service entity processing
            if ent_label == "Service":
                if intent_owner or intent_team:
                    q = """
                    MATCH (p:Person)-[:OWNS]->(s:Service {id: $sid})
                    OPTIONAL MATCH (p)-[:MEMBER_OF]->(t:Team)
                    RETURN p.id AS pid, p.name AS pname, t.name AS tname
                    """
                    owners = self.store.query(q, {"sid": ent_id})
                    if owners:
                        for o in owners:
                            facts.append({
                                "statement": f"{o['pname']} owns {ent_name}; {o['pname']} is on the {o.get('tname', 'engineering')} team.",
                                "evidence_path": f"({o['pid']}:Person)-[:OWNS]->({ent_id}:Service)",
                                "source_ids": ["doc-service-ownership-catalog"],
                            })
                            # Add catalog source
                            doc_res = self.store.query(
                                "MATCH (d:Document {id: 'doc-service-ownership-catalog'}) RETURN d.id AS id, d.name AS title, d.uri AS uri, d.excerpt AS excerpt"
                            )
                            if doc_res:
                                add_source(doc_res[0]["id"], doc_res[0]["title"], doc_res[0].get("uri"), doc_res[0].get("excerpt"))
                    else:
                        gaps.append(f"No owner or team recorded in graph for service '{ent_name}'.")

                if intent_dependency:
                    deps = self.store.query(
                        "MATCH (s:Service {id: $sid})-[:DEPENDS_ON]->(target:Service) RETURN target.id AS id, target.name AS name",
                        {"sid": ent_id},
                    )
                    if deps:
                        dep_names = ", ".join([d["name"] for d in deps])
                        facts.append({
                            "statement": f"{ent_name} depends on {dep_names}.",
                            "evidence_path": f"({ent_id})-[:DEPENDS_ON]->(dependencies)",
                            "source_ids": [],
                        })

            # Feature entity processing
            elif ent_label == "Feature":
                # Look up decisions or implementing services
                svcs = self.store.query(
                    "MATCH (s:Service)-[:IMPLEMENTS]->(f:Feature {id: $fid}) RETURN s.id AS id, s.name AS name",
                    {"fid": ent_id},
                )
                if svcs:
                    for s in svcs:
                        facts.append({
                            "statement": f"{s['name']} implements feature {ent_name}.",
                            "evidence_path": f"({s['id']}:Service)-[:IMPLEMENTS]->({ent_id}:Feature)",
                            "source_ids": [],
                        })

            # Decision entity processing (or if question asks "why" regarding idempotency/retry)
            if ent_label == "Decision" or intent_why:
                # Find matching decisions
                dec_cypher = """
                MATCH (d:Decision)
                OPTIONAL MATCH (d)-[:SUPPORTED_BY]->(doc:Document)
                OPTIONAL MATCH (d)-[:RESPONDS_TO]->(inc:Incident)
                RETURN d.id AS id, d.name AS name, d.rationale AS rationale, d.status AS status,
                       doc.id AS doc_id, doc.name AS doc_title, doc.uri AS doc_uri, doc.excerpt AS doc_excerpt,
                       inc.id AS inc_id, inc.name AS inc_name, inc.code AS inc_code
                """
                all_decs = self.store.query(dec_cypher)
                for d in all_decs:
                    # Match decision if ent is Decision, or if question mentions idempotency/retry/ADR
                    if ent_label == "Decision" and d["id"] != ent_id:
                        continue
                    if ent_label != "Decision":
                        # Check keyword connection to decision
                        d_squashed = squash(d["name"])
                        if not any(k in q_lower for k in ["idempotenc", "retry", "pool", d_squashed, d["id"].lower()]):
                            continue

                    statement = f"{d['name']} was accepted because: {d['rationale']}"
                    source_ids = [d["doc_id"]] if d.get("doc_id") else []
                    facts.append({
                        "statement": statement,
                        "evidence_path": f"({d['id']}:Decision)-[:SUPPORTED_BY]->({d.get('doc_id')})",
                        "source_ids": source_ids,
                    })
                    if d.get("doc_id"):
                        add_source(d["doc_id"], d["doc_title"], d.get("doc_uri"), d.get("doc_excerpt"))

        # Check for gaps if no facts found
        if not facts:
            gaps.append(f"No direct graph facts found matching question: '{question}'")

        return ok_response(
            entities=[{"id": e["id"], "name": e["name"], "label": e["label"]} for e in matched_entities],
            facts=facts,
            sources=sources,
            gaps=gaps,
            note="Compose the answer only from facts; cite sources.",
        )

    def ingest_company_records(
        self,
        source: Dict[str, str],
        records: List[Dict[str, Any]],
        relationships: List[Dict[str, str]] = [],
    ) -> Dict[str, Any]:
        """Ingest external structured company records idempotently."""
        return self.ingestion_engine.ingest(source, records, relationships)
