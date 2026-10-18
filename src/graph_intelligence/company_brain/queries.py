"""Cypher queries for company knowledge base (Track 3)."""

# Service comprehensive brief
SERVICE_BRIEF_QUERY = """
MATCH (s:Service {id: $service_id})
OPTIONAL MATCH (owner:Person)-[:OWNS]->(s)
OPTIONAL MATCH (owner)-[:MEMBER_OF]->(team:Team)
OPTIONAL MATCH (s)-[:PART_OF]->(p:Project)
OPTIONAL MATCH (s)-[:DEPENDS_ON]->(dep:Service)
OPTIONAL MATCH (client:Service)-[:DEPENDS_ON]->(s)
OPTIONAL MATCH (s)-[:IMPLEMENTS]->(feat:Feature)
OPTIONAL MATCH (dec:Decision)-[:AFFECTS]->(s)
OPTIONAL MATCH (inc:Incident)-[:AFFECTS]->(s)
OPTIONAL MATCH (doc:Document)-[:DESCRIBES]->(s)
RETURN
    s.id AS id, s.name AS name, s.aliases AS aliases,
    owner.id AS owner_id, owner.name AS owner_name, team.name AS team_name,
    p.id AS project_id, p.name AS project_name,
    collect(DISTINCT {id: dep.id, name: dep.name}) AS dependencies,
    collect(DISTINCT {id: client.id, name: client.name}) AS dependents,
    collect(DISTINCT {id: feat.id, name: feat.name}) AS features,
    collect(DISTINCT {id: dec.id, name: dec.name, rationale: dec.rationale}) AS decisions,
    collect(DISTINCT {id: inc.id, name: inc.name, code: inc.code}) AS incidents,
    collect(DISTINCT {id: doc.id, name: doc.name, uri: doc.uri, excerpt: doc.excerpt}) AS documents
"""

# Decision comprehensive context
DECISION_CONTEXT_QUERY = """
MATCH (d:Decision {id: $decision_id})
OPTIONAL MATCH (d)-[:MADE_FOR]->(p:Project)
OPTIONAL MATCH (d)-[:AFFECTS]->(s:Service)
OPTIONAL MATCH (d)-[:SUPPORTED_BY]->(doc:Document)
OPTIONAL MATCH (d)-[:RESPONDS_TO]->(inc:Incident)
OPTIONAL MATCH (ir_doc:Document)-[:DESCRIBES]->(inc)
RETURN
    d.id AS id, d.name AS name, d.rationale AS rationale,
    d.status AS status, d.decided_on AS decided_on,
    p.id AS project_id, p.name AS project_name,
    collect(DISTINCT {id: s.id, name: s.name}) AS affected_services,
    collect(DISTINCT {id: doc.id, name: doc.name, uri: doc.uri, excerpt: doc.excerpt}) AS supporting_docs,
    collect(DISTINCT {id: inc.id, name: inc.name, code: inc.code, ir_doc_id: ir_doc.id, ir_doc_name: ir_doc.name}) AS responding_incidents
"""

# All company entities for resolver caching
ALL_COMPANY_ENTITIES_QUERY = """
MATCH (n)
WHERE any(label IN labels(n) WHERE label IN [
    'Company', 'Team', 'Person', 'Project', 'Service', 'Feature', 'Incident', 'Decision', 'Document'
])
RETURN n.id AS id, n.name AS name, head(labels(n)) AS label, n.aliases AS aliases
"""
