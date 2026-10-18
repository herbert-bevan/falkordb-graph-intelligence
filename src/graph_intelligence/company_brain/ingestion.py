"""Structured ingestion validator and executor for company graph records."""

from typing import Any, Dict, List
from graph_intelligence.common.falkordb_client import GraphStore
from graph_intelligence.common.ids import utcnow_iso
from graph_intelligence.common.schema import COMPANY_LABELS, is_valid_relationship


class IngestionEngine:
    """Executes validated, idempotent company data ingestion."""

    def __init__(self, store: GraphStore):
        self.store = store

    def ingest(
        self,
        source: Dict[str, str],
        records: List[Dict[str, Any]],
        relationships: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        source_id = source.get("id", "source_unknown")
        now = utcnow_iso()
        created_count = 0
        updated_count = 0
        skipped_count = 0
        errors: List[str] = []

        if len(records) > 200 or len(relationships) > 200:
            return {
                "ok": False,
                "error_code": "INVALID_INPUT",
                "message": "Maximum 200 records or relationships allowed per ingestion batch.",
            }

        # Step 1: Ingest nodes
        node_labels_by_id: Dict[str, str] = {}
        for rec in records:
            label = rec.get("type")
            node_id = rec.get("id")
            name = rec.get("name") or rec.get("title") or node_id
            props = rec.get("properties") or {}

            if not label or not node_id:
                errors.append(f"Record missing required 'type' or 'id': {rec}")
                skipped_count += 1
                continue

            if label not in COMPANY_LABELS:
                errors.append(f"Rejected node type '{label}' - must be a company label (not memory/user).")
                skipped_count += 1
                continue

            node_labels_by_id[node_id] = label

            cypher = f"""
            MERGE (n:{label} {{id: $id}})
            ON CREATE SET
                n.name = $name,
                n.source = 'structured_ingestion',
                n.source_ref = $source_ref,
                n.created_at = $now,
                n.updated_at = $now
            ON MATCH SET
                n.name = $name,
                n.source_ref = $source_ref,
                n.updated_at = $now
            RETURN n.id AS id
            """
            params: Dict[str, Any] = {
                "id": node_id,
                "name": name,
                "source_ref": source_id,
                "now": now,
            }

            for k, v in props.items():
                p_key = f"prop_{k}"
                cypher += f"\nSET n.{k} = ${p_key}"
                params[p_key] = v

            try:
                self.store.query(cypher, params)
                created_count += 1
            except Exception as exc:
                errors.append(f"Failed to upsert node {node_id}: {exc}")
                skipped_count += 1

        # Step 2: Ingest relationships
        rel_created_count = 0
        for rel in relationships:
            rel_type = rel.get("type")
            from_id = rel.get("from_id")
            to_id = rel.get("to_id")

            if not rel_type or not from_id or not to_id:
                errors.append(f"Relationship missing required fields: {rel}")
                continue

            from_label = node_labels_by_id.get(from_id)
            to_label = node_labels_by_id.get(to_id)

            if from_label and to_label and not is_valid_relationship(rel_type, from_label, to_label):
                errors.append(f"Disallowed relationship ({from_label})-[:{rel_type}]->({to_label})")
                continue

            cypher = f"""
            MATCH (a {{id: $from_id}})
            MATCH (b {{id: $to_id}})
            MERGE (a)-[r:{rel_type}]->(b)
            ON CREATE SET r.source = 'structured_ingestion', r.source_ref = $source_ref, r.created_at = $now
            RETURN type(r) AS rel_type
            """
            try:
                res = self.store.query(cypher, {"from_id": from_id, "to_id": to_id, "source_ref": source_id, "now": now})
                if res:
                    rel_created_count += 1
                else:
                    errors.append(f"Could not connect relationship {from_id} -> {to_id} (nodes not found)")
            except Exception as exc:
                errors.append(f"Failed to upsert edge {from_id} -> {to_id}: {exc}")

        return {
            "ok": True,
            "created": created_count,
            "updated": updated_count,
            "relationships_created": rel_created_count,
            "skipped": skipped_count,
            "errors": errors,
        }
