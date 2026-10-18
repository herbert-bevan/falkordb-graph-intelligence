"""Cypher queries for user session memory (Track 2)."""

# Create or match User
MERGE_USER_QUERY = """
MERGE (u:User {id: $user_id})
ON CREATE SET u.name = $user_id, u.source = 'llm_mcp_write', u.created_at = $now, u.updated_at = $now
RETURN u.id AS id
"""

# Create or match Session
MERGE_SESSION_QUERY = """
MERGE (ses:Session {id: $session_id, user_id: $user_id})
ON CREATE SET ses.created_at = $now
RETURN ses.id AS id
"""

# Check for deduplication by content hash
FIND_ACTIVE_BY_HASH_QUERY = """
MATCH (s:SessionSummary {user_id: $user_id, content_hash: $content_hash, status: 'active'})
RETURN s.id AS id, s.title AS title, s.summary_version AS summary_version, s.created_at AS created_at
LIMIT 1
"""

# Insert new SessionSummary
CREATE_SESSION_SUMMARY_QUERY = """
CREATE (s:SessionSummary {
    id: $id,
    user_id: $user_id,
    session_id: $session_id,
    title: $title,
    summary: $summary,
    keywords: $keywords,
    entity_keys: $entity_keys,
    decisions: $decisions,
    open_tasks_text: $open_tasks_text,
    project_id: $project_id,
    importance: $importance,
    status: $status,
    summary_version: $summary_version,
    supersedes_id: $supersedes_id,
    content_hash: $content_hash,
    visibility: 'private',
    source: 'llm_mcp_write',
    created_at: $now,
    updated_at: $now
})
WITH s
MATCH (u:User {id: $user_id})
MERGE (u)-[:OWNS_MEMORY]->(s)
WITH s
MATCH (ses:Session {id: $session_id, user_id: $user_id})
MERGE (s)-[:FROM_SESSION]->(ses)
RETURN s.id AS id
"""

# Link SessionSummary to resolved Project
LINK_PROJECT_QUERY = """
MATCH (s:SessionSummary {id: $summary_id, user_id: $user_id})
MATCH (p:Project {id: $project_id})
MERGE (s)-[:ABOUT_PROJECT]->(p)
RETURN p.id AS id
"""

# Link SessionSummary to resolved Entity
LINK_ENTITY_QUERY = """
MATCH (s:SessionSummary {id: $summary_id, user_id: $user_id})
MATCH (e {id: $entity_id})
MERGE (s)-[:MENTIONS_ENTITY]->(e)
RETURN e.id AS id
"""

# Create Task node and edge
CREATE_TASK_QUERY = """
MATCH (s:SessionSummary {id: $summary_id, user_id: $user_id})
CREATE (t:Task {
    id: $task_id,
    user_id: $user_id,
    text: $text,
    status: $status,
    created_at: $now,
    updated_at: $now
})
MERGE (s)-[:HAS_TASK]->(t)
RETURN t.id AS id
"""

# Read back summary by ID and User ID
READ_BACK_SUMMARY_QUERY = """
MATCH (s:SessionSummary {id: $id, user_id: $user_id})
OPTIONAL MATCH (s)-[:ABOUT_PROJECT]->(p:Project)
OPTIONAL MATCH (s)-[:MENTIONS_ENTITY]->(e)
OPTIONAL MATCH (s)-[:HAS_TASK]->(t:Task)
RETURN
    s.id AS id,
    s.user_id AS user_id,
    s.session_id AS session_id,
    s.title AS title,
    s.summary AS summary,
    s.keywords AS keywords,
    s.entity_keys AS entity_keys,
    s.decisions AS decisions,
    s.open_tasks_text AS open_tasks_text,
    s.importance AS importance,
    s.status AS status,
    s.summary_version AS summary_version,
    s.supersedes_id AS supersedes_id,
    s.content_hash AS content_hash,
    s.created_at AS created_at,
    s.updated_at AS updated_at,
    p.id AS project_id,
    p.name AS project_name,
    collect(DISTINCT {id: e.id, name: e.name, label: head(labels(e))}) AS linked_entities,
    collect(DISTINCT {id: t.id, text: t.text, status: t.status}) AS tasks
"""

# Fetch candidate summaries for user-scoped search
FETCH_USER_CANDIDATES_QUERY = """
MATCH (s:SessionSummary {user_id: $user_id})
WHERE s.status IN $statuses
OPTIONAL MATCH (s)-[:ABOUT_PROJECT]->(p:Project)
OPTIONAL MATCH (s)-[:MENTIONS_ENTITY]->(e)
OPTIONAL MATCH (s)-[:HAS_TASK]->(t:Task)
RETURN
    s.id AS id,
    s.title AS title,
    s.summary AS summary,
    s.keywords AS keywords,
    s.entity_keys AS entity_keys,
    s.decisions AS decisions,
    s.open_tasks_text AS open_tasks_text,
    s.importance AS importance,
    s.status AS status,
    s.summary_version AS summary_version,
    s.supersedes_id AS supersedes_id,
    s.created_at AS created_at,
    s.updated_at AS updated_at,
    p.id AS project_id,
    p.name AS project_name,
    collect(DISTINCT {id: e.id, name: e.name, label: head(labels(e))}) AS linked_entities,
    collect(DISTINCT {id: t.id, text: t.text, status: t.status}) AS tasks
LIMIT 200
"""

# Link SUPERSEDES relationship
LINK_SUPERSEDES_QUERY = """
MATCH (new_sum:SessionSummary {id: $new_id, user_id: $user_id})
MATCH (old_sum:SessionSummary {id: $old_id, user_id: $user_id})
SET old_sum.status = 'superseded', old_sum.updated_at = $now
MERGE (new_sum)-[:SUPERSEDES]->(old_sum)
RETURN new_sum.id AS id
"""

# Archive summary
ARCHIVE_SUMMARY_QUERY = """
MATCH (s:SessionSummary {id: $id, user_id: $user_id})
SET s.status = 'archived', s.updated_at = $now
RETURN s.id AS id
"""

# Get user timeline
def get_user_timeline_query(limit: int) -> str:
    return f"""
    MATCH (s:SessionSummary {{user_id: $user_id}})
    WHERE s.status IN $statuses
    OPTIONAL MATCH (s)-[:ABOUT_PROJECT]->(p:Project)
    RETURN
        s.id AS id,
        s.session_id AS session_id,
        s.title AS title,
        s.summary AS summary,
        s.status AS status,
        s.summary_version AS summary_version,
        s.supersedes_id AS supersedes_id,
        s.importance AS importance,
        s.created_at AS created_at,
        s.updated_at AS updated_at,
        p.name AS project_name
    ORDER BY s.created_at DESC
    LIMIT {int(limit)}
    """

# Memory status counts for configured user
MEMORY_STATUS_COUNTS_QUERY = """
MATCH (s:SessionSummary {user_id: $user_id})
RETURN
    count(CASE WHEN s.status = 'active' THEN 1 END) AS active_count,
    count(CASE WHEN s.status = 'superseded' THEN 1 END) AS superseded_count,
    count(CASE WHEN s.status = 'archived' THEN 1 END) AS archived_count
"""
