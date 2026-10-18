"""Cypher queries and query builders for reasoning (Track 1)."""

# Find all services with aliases and ids for resolution
ALL_SERVICES_QUERY = """
MATCH (s:Service)
RETURN s.id AS id, s.name AS name, s.aliases AS aliases
"""


def get_outgoing_dependencies_query(depth: int, limit: int) -> str:
    return f"""
    MATCH (s:Service {{id: $service_id}})
    MATCH p = (s)-[:DEPENDS_ON*1..{int(depth)}]->(target:Service)
    RETURN target.id AS target_id, target.name AS target_name,
           length(p) AS depth,
           [n IN nodes(p) | n.id] AS node_ids,
           [n IN nodes(p) | n.name] AS node_names,
           [r IN relationships(p) | type(r)] AS rel_types
    LIMIT {int(limit)}
    """


def get_incoming_dependents_query(depth: int, limit: int) -> str:
    return f"""
    MATCH (s:Service {{id: $service_id}})
    MATCH p = (source:Service)-[:DEPENDS_ON*1..{int(depth)}]->(s)
    RETURN source.id AS source_id, source.name AS source_name,
           length(p) AS depth,
           [n IN nodes(p) | n.id] AS node_ids,
           [n IN nodes(p) | n.name] AS node_names,
           [r IN relationships(p) | type(r)] AS rel_types
    LIMIT {int(limit)}
    """


# Direct connections for service change impact
SERVICE_IMPACT_FACTS_QUERY = """
MATCH (s:Service {id: $service_id})
OPTIONAL MATCH (owner:Person)-[:OWNS]->(s)
OPTIONAL MATCH (owner)-[:MEMBER_OF]->(team:Team)
OPTIONAL MATCH (s)-[:IMPLEMENTS]->(feat:Feature)
OPTIONAL MATCH (dec:Decision)-[:AFFECTS]->(s)
OPTIONAL MATCH (inc:Incident)-[:AFFECTS]->(s)
OPTIONAL MATCH (doc:Document)-[:DESCRIBES]->(s)
RETURN
    owner.id AS owner_id, owner.name AS owner_name, team.name AS team_name,
    feat.id AS feat_id, feat.name AS feat_name,
    dec.id AS dec_id, dec.name AS dec_name, dec.rationale AS dec_rationale,
    inc.id AS inc_id, inc.name AS inc_name, inc.code AS inc_code,
    doc.id AS doc_id, doc.name AS doc_name, doc.uri AS doc_uri
"""


def get_shortest_path_query(max_hops: int) -> str:
    return f"""
    MATCH (a {{id: $source_id}}), (b {{id: $target_id}})
    MATCH p = shortestPath((a)-[*..{int(max_hops)}]-(b))
    RETURN
        [n IN nodes(p) | n.id] AS node_ids,
        [n IN nodes(p) | n.name] AS node_names,
        [n IN nodes(p) | head(labels(n))] AS node_labels,
        [r IN relationships(p) | type(r)] AS rel_types,
        [r IN relationships(p) | startNode(r).id] AS start_ids,
        [r IN relationships(p) | endNode(r).id] AS end_ids,
        length(p) AS length
    """
