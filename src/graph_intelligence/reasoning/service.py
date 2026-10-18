"""Reasoning domain service implementation (Track 1)."""

from collections import deque
from typing import Any, Dict, List, Optional
from graph_intelligence.common.errors import ValidationError, EntityNotFoundError
from graph_intelligence.common.falkordb_client import GraphStore
from graph_intelligence.common.result_models import ok_response, error_response, ErrorCode
from graph_intelligence.common.schema import COMPANY_LABELS
from graph_intelligence.common.text import squash, tokenize, normalize_term
from graph_intelligence.common.validation import scan_for_secrets, validate_int_range, validate_text_length
from graph_intelligence.reasoning.queries import (
    ALL_SERVICES_QUERY,
    SERVICE_IMPACT_FACTS_QUERY,
    get_incoming_dependents_query,
    get_outgoing_dependencies_query,
    get_shortest_path_query,
)


class ReasoningService:
    """Graph reasoning engine for dependencies, change impact, and path analysis."""

    def __init__(self, graph_name: Optional[str] = None):
        self.store = GraphStore(graph_name=graph_name)

    def _resolve_service(self, service_query: str) -> Optional[Dict[str, Any]]:
        """Resolve service identifier, name, or alias using squashed matching."""
        target_squashed = squash(service_query)
        services = self.store.query(ALL_SERVICES_QUERY)

        # 1. Exact id or name match
        for s in services:
            if squash(s.get("id", "")) == target_squashed or squash(s.get("name", "")) == target_squashed:
                return s

        # 2. Check aliases
        for s in services:
            aliases = s.get("aliases") or []
            if isinstance(aliases, str):
                aliases = [aliases]
            for alias in aliases:
                if squash(alias) == target_squashed:
                    return s

        # 3. Partial / substring match
        for s in services:
            if target_squashed in squash(s.get("name", "")) or squash(s.get("name", "")) in target_squashed:
                return s

        return None

    def _resolve_any_entity(self, query: str) -> Optional[Dict[str, Any]]:
        """Resolve any company node by id, name, or alias."""
        target_squashed = squash(query)
        cypher = """
        MATCH (n)
        WHERE any(label IN labels(n) WHERE label IN [
            'Company', 'Team', 'Person', 'Project', 'Service', 'Feature', 'Incident', 'Decision', 'Document'
        ])
        RETURN n.id AS id, n.name AS name, labels(n)[0] AS label, n.aliases AS aliases
        """
        nodes = self.store.query(cypher)
        for n in nodes:
            if squash(n.get("id", "")) == target_squashed or squash(n.get("name", "")) == target_squashed:
                return n
            aliases = n.get("aliases") or []
            if isinstance(aliases, str):
                aliases = [aliases]
            for alias in aliases:
                if squash(alias) == target_squashed:
                    return n
        return None

    def find_service_dependencies(
        self,
        service: str,
        direction: str = "both",
        max_depth: int = 2,
        limit: int = 25,
    ) -> Dict[str, Any]:
        """Find upstream dependencies and/or downstream dependents of a service."""
        try:
            scan_for_secrets(service)
            validate_text_length(service, "service", 120)
            max_depth = validate_int_range(max_depth, "max_depth", 1, 4)
            limit = validate_int_range(limit, "limit", 1, 25)
            if direction not in ("dependencies", "dependents", "both"):
                return error_response(ErrorCode.INVALID_INPUT, f"Invalid direction '{direction}'. Must be 'dependencies', 'dependents', or 'both'.")
        except ValidationError as e:
            return error_response(e.error_code, e.message)

        matched = self._resolve_service(service)
        if not matched:
            # Suggest up to 3 available services
            all_services = self.store.query(ALL_SERVICES_QUERY)
            suggestions = [s["name"] for s in all_services[:3]]
            return error_response(
                ErrorCode.UNKNOWN_ENTITY,
                f"Unknown service '{service}'.",
                suggestions=suggestions,
            )

        service_id = matched["id"]
        service_name = matched["name"]
        connections: List[Dict[str, Any]] = []

        # 1. Outgoing dependencies (services that matched service needs)
        if direction in ("dependencies", "both"):
            q = get_outgoing_dependencies_query(max_depth, limit)
            rows = self.store.query(q, {"service_id": service_id})
            for r in rows:
                connections.append({
                    "service_id": r["target_id"],
                    "service_name": r["target_name"],
                    "relation": "dependency",
                    "depth": r["depth"],
                    "path": {
                        "node_ids": r["node_ids"],
                        "node_names": r["node_names"],
                        "rel_types": r["rel_types"],
                    },
                })

        # 2. Incoming dependents (services that need matched service)
        if direction in ("dependents", "both"):
            q = get_incoming_dependents_query(max_depth, limit)
            rows = self.store.query(q, {"service_id": service_id})
            for r in rows:
                connections.append({
                    "service_id": r["source_id"],
                    "service_name": r["source_name"],
                    "relation": "dependent",
                    "depth": r["depth"],
                    "path": {
                        "node_ids": r["node_ids"],
                        "node_names": r["node_names"],
                        "rel_types": r["rel_types"],
                    },
                })

        connections.sort(key=lambda c: (c["depth"], c["service_name"]))
        evidence_summary = (
            f"Found {len(connections)} connected service(s) for {service_name} "
            f"up to depth {max_depth} (direction={direction})."
        )

        return ok_response(
            matched_service={"id": service_id, "name": service_name},
            direction=direction,
            max_depth=max_depth,
            connections=connections[:limit],
            evidence_summary=evidence_summary,
        )

    def analyze_change_impact(
        self,
        target: str,
        target_type: str = "Service",
        change_description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Analyze cascading graph impact for a change to a Service, Feature, or Decision."""
        try:
            scan_for_secrets(target)
            scan_for_secrets(change_description)
            validate_text_length(target, "target", 120)
            if change_description:
                validate_text_length(change_description, "change_description", 1000)
            if target_type not in ("Service", "Feature", "Decision"):
                return error_response(ErrorCode.INVALID_INPUT, f"Unsupported target_type '{target_type}'. Must be Service, Feature, or Decision.")
        except ValidationError as e:
            return error_response(e.error_code, e.message)

        # Handle Feature or Decision targets by mapping to their affected/implementing services
        service_node: Optional[Dict[str, Any]] = None
        if target_type == "Service":
            service_node = self._resolve_service(target)
        elif target_type == "Feature":
            feat_match = self._resolve_any_entity(target)
            if feat_match and feat_match.get("label") == "Feature":
                # Find service implementing feature
                svcs = self.store.query(
                    "MATCH (s:Service)-[:IMPLEMENTS]->(f:Feature {id: $fid}) RETURN s.id AS id, s.name AS name",
                    {"fid": feat_match["id"]},
                )
                if svcs:
                    service_node = svcs[0]
        elif target_type == "Decision":
            dec_match = self._resolve_any_entity(target)
            if dec_match and dec_match.get("label") == "Decision":
                svcs = self.store.query(
                    "MATCH (d:Decision {id: $did})-[:AFFECTS]->(s:Service) RETURN s.id AS id, s.name AS name",
                    {"did": dec_match["id"]},
                )
                if svcs:
                    service_node = svcs[0]

        if not service_node:
            return error_response(ErrorCode.UNKNOWN_ENTITY, f"Could not resolve {target_type} target '{target}'.")

        service_id = service_node["id"]
        service_name = service_node["name"]

        # 1. Dependents (incoming DEPENDS_ON, depth <= 3)
        dependents_rows = self.store.query(
            get_incoming_dependents_query(depth=3, limit=25),
            {"service_id": service_id},
        )
        dependents = [
            {
                "service_id": r["source_id"],
                "service_name": r["source_name"],
                "depth": r["depth"],
                "evidence_path": {
                    "node_ids": r["node_ids"],
                    "node_names": r["node_names"],
                    "rel_types": r["rel_types"],
                },
                "impact_note": "would be affected by interface/behavior change",
            }
            for r in dependents_rows
        ]

        # 2. Dependencies (outgoing DEPENDS_ON, depth <= 2)
        dependencies_rows = self.store.query(
            get_outgoing_dependencies_query(depth=2, limit=25),
            {"service_id": service_id},
        )
        dependencies = [
            {
                "service_id": r["target_id"],
                "service_name": r["target_name"],
                "depth": r["depth"],
                "evidence_path": {
                    "node_ids": r["node_ids"],
                    "node_names": r["node_names"],
                    "rel_types": r["rel_types"],
                },
                "impact_note": "would see changed traffic/load",
            }
            for r in dependencies_rows
        ]

        # 3. Direct connections (features, decisions, incidents, owners, documents)
        facts = self.store.query(SERVICE_IMPACT_FACTS_QUERY, {"service_id": service_id})
        features_seen = set()
        decisions_seen = set()
        incidents_seen = set()
        owners_seen = set()
        documents_seen = set()

        features = []
        decisions = []
        incidents = []
        owners = []
        documents = []

        for f in facts:
            if f.get("feat_id") and f["feat_id"] not in features_seen:
                features_seen.add(f["feat_id"])
                features.append({
                    "id": f["feat_id"],
                    "name": f["feat_name"],
                    "evidence_path": f"({service_id})-[:IMPLEMENTS]->({f['feat_id']})",
                })
            if f.get("dec_id") and f["dec_id"] not in decisions_seen:
                decisions_seen.add(f["dec_id"])
                decisions.append({
                    "id": f["dec_id"],
                    "name": f["dec_name"],
                    "rationale": f["dec_rationale"],
                    "evidence_path": f"({f['dec_id']})-[:AFFECTS]->({service_id})",
                })
            if f.get("inc_id") and f["inc_id"] not in incidents_seen:
                incidents_seen.add(f["inc_id"])
                incidents.append({
                    "id": f["inc_id"],
                    "name": f["inc_name"],
                    "code": f["inc_code"],
                    "evidence_path": f"({f['inc_id']})-[:AFFECTS]->({service_id})",
                })
            if f.get("owner_id") and f["owner_id"] not in owners_seen:
                owners_seen.add(f["owner_id"])
                owners.append({
                    "id": f["owner_id"],
                    "name": f["owner_name"],
                    "team": f["team_name"],
                    "evidence_path": f"({f['owner_id']})-[:OWNS]->({service_id})",
                })
            if f.get("doc_id") and f["doc_id"] not in documents_seen:
                documents_seen.add(f["doc_id"])
                documents.append({
                    "id": f["doc_id"],
                    "name": f["doc_name"],
                    "uri": f["doc_uri"],
                    "evidence_path": f"({f['doc_id']})-[:DESCRIBES]->({service_id})",
                })

        return ok_response(
            target={"id": service_id, "name": service_name, "type": target_type},
            change_description=change_description,
            dependents=dependents,
            dependencies=dependencies,
            features=features,
            decisions=decisions,
            incidents=incidents,
            owners=owners,
            documents=documents,
            interpretation_note=(
                "Graph facts above are authoritative; any impact reasoning beyond them is the assistant's inference."
            ),
        )

    def find_graph_path(self, source: str, target: str, max_hops: int = 4) -> Dict[str, Any]:
        """Find the undirected shortest path between two entities in the graph."""
        try:
            scan_for_secrets(source)
            scan_for_secrets(target)
            validate_text_length(source, "source", 120)
            validate_text_length(target, "target", 120)
            max_hops = validate_int_range(max_hops, "max_hops", 1, 6)
        except ValidationError as e:
            return error_response(e.error_code, e.message)

        src_node = self._resolve_any_entity(source)
        if not src_node:
            return error_response(ErrorCode.UNKNOWN_ENTITY, f"Could not resolve source entity '{source}'.")

        tgt_node = self._resolve_any_entity(target)
        if not tgt_node:
            return error_response(ErrorCode.UNKNOWN_ENTITY, f"Could not resolve target entity '{target}'.")

        if src_node["id"] == tgt_node["id"]:
            return ok_response(
                found=True,
                source={"id": src_node["id"], "name": src_node["name"]},
                target={"id": tgt_node["id"], "name": tgt_node["name"]},
                length=0,
                nodes=[{"id": src_node["id"], "name": src_node["name"], "label": src_node.get("label", "Entity")}],
                relationships=[],
            )

        # BFS in Python using bounded neighbor queries (FalkorDB undirected shortestPath fallback per spec §3)
        queue = deque([(src_node["id"], [{"id": src_node["id"], "name": src_node["name"], "label": src_node.get("label", "Entity")}], [])])
        visited = {src_node["id"]}
        found = None

        neighbor_query = """
        MATCH (a {id: $curr_id})-[r]-(b)
        RETURN b.id AS next_id, b.name AS next_name, head(labels(b)) AS next_label,
               type(r) AS rel_type, startNode(r).id AS start_id, endNode(r).id AS end_id
        LIMIT 50
        """

        while queue:
            curr_id, path_nodes, path_rels = queue.popleft()
            if len(path_rels) >= max_hops:
                continue

            rows = self.store.query(neighbor_query, {"curr_id": curr_id})
            for r in rows:
                nid = r["next_id"]
                if not nid:
                    continue
                rel = {
                    "type": r["rel_type"],
                    "from_id": r["start_id"],
                    "to_id": r["end_id"],
                }
                node = {
                    "id": nid,
                    "name": r["next_name"] or nid,
                    "label": r["next_label"] or "Entity",
                }

                if nid == tgt_node["id"]:
                    found = (path_nodes + [node], path_rels + [rel])
                    break

                if nid not in visited:
                    visited.add(nid)
                    queue.append((nid, path_nodes + [node], path_rels + [rel]))

            if found:
                break

        if not found:
            return ok_response(found=False, message=f"No path within {max_hops} hops between {source} and {target}.")

        nodes, relationships = found
        return ok_response(
            found=True,
            source={"id": src_node["id"], "name": src_node["name"]},
            target={"id": tgt_node["id"], "name": tgt_node["name"]},
            length=len(relationships),
            nodes=nodes,
            relationships=relationships,
        )

    def search_connected_entities(
        self,
        query: str,
        entity_types: Optional[List[str]] = None,
        limit: int = 10,
    ) -> Dict[str, Any]:
        """Search entities by token/alias match and return them with immediate connections."""
        try:
            scan_for_secrets(query)
            validate_text_length(query, "query", 120)
            limit = validate_int_range(limit, "limit", 1, 10)
        except ValidationError as e:
            return error_response(e.error_code, e.message)

        tokens = tokenize(query)
        target_squashed = squash(query)

        cypher = """
        MATCH (n)
        WHERE any(label IN labels(n) WHERE label IN [
            'Company', 'Team', 'Person', 'Project', 'Service', 'Feature', 'Incident', 'Decision', 'Document'
        ])
        RETURN n.id AS id, n.name AS name, labels(n)[0] AS label, n.aliases AS aliases
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
            # Check squash match
            if target_squashed in node_squashed or node_squashed in target_squashed:
                is_match = True
            elif any(target_squashed in a or a in target_squashed for a in alias_squashed):
                is_match = True
            elif any(t in node_squashed for t in tokens):
                is_match = True

            if is_match:
                matches.append(n)

        # For matched nodes, fetch immediate relationships up to 10 each
        results = []
        for m in matches[:limit]:
            node_id = m["id"]
            rel_query = """
            MATCH (n {id: $node_id})-[r]-(other)
            RETURN type(r) AS rel_type,
                   startNode(r).id AS start_id,
                   endNode(r).id AS end_id,
                   other.id AS other_id,
                   other.name AS other_name,
                   head(labels(other)) AS other_label
            LIMIT 10
            """
            rel_rows = self.store.query(rel_query, {"node_id": node_id})
            connections = [
                {
                    "relationship": r["rel_type"],
                    "direction": "outgoing" if r["start_id"] == node_id else "incoming",
                    "connected_entity": {
                        "id": r["other_id"],
                        "name": r["other_name"],
                        "label": r["other_label"],
                    },
                }
                for r in rel_rows
            ]
            results.append({
                "entity": {"id": m["id"], "name": m["name"], "label": m["label"]},
                "connections": connections,
            })

        return ok_response(results=results, count=len(results))
