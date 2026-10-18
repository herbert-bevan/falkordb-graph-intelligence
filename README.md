# FalkorDB Graph Intelligence Platform & Autonomous Memory Engine

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FalkorDB](https://img.shields.io/badge/FalkorDB-Cloud-orange.svg)](https://www.falkordb.com/)
[![MCP](https://img.shields.io/badge/MCP-1.30-purple.svg)](https://modelcontextprotocol.io/)
[![Tests](https://img.shields.io/badge/tests-33%20passed-brightgreen.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An enterprise-grade Python platform delivering **three specialized Model Context Protocol (MCP) servers** over a single **FalkorDB knowledge graph** and a unified, secure domain core.

Built specifically for advanced agentic AI environments (such as **Google Antigravity**, Claude Desktop, and VS Code), this platform bridges the gap between static codebases, corporate knowledge bases, and long-term agent memory without relying on vector embeddings or opaque embeddings-based semantic search.

---

## Table of Contents

1. [Executive Summary & Problem Statement](#1-executive-summary--problem-statement)
2. [System Architecture](#2-system-architecture)
3. [Graph Data Model & Schema](#3-graph-data-model--schema)
4. [Deep Dive: The Three MCP Servers](#4-deep-dive-the-three-mcp-servers)
   - [Track 1: atlaspay-reasoning](#track-1-atlaspay-reasoning)
   - [Track 2: atlaspay-memory (The Critical Track)](#track-2-atlaspay-memory-the-critical-track)
   - [Track 3: atlaspay-brain](#track-3-atlaspay-brain)
5. [Shared Domain Core & Security Boundaries](#5-shared-domain-core--security-boundaries)
6. [FalkorDB Field Learnings & Opportunities for Improvement](#6-falkordb-field-learnings--opportunities-for-improvement)
7. [Verification & Test Suite (33/33 Passing)](#7-verification--test-suite-3333-passing)
8. [Live Demo Runbook & Prompt Storyboard](#8-live-demo-runbook--prompt-storyboard)
9. [Deployment & Quickstart](#9-deployment--quickstart)

---

## 1. Executive Summary & Problem Statement

Large Language Models (LLMs) running inside agentic coding environments suffer from three critical deficiencies:
1. **Context Amnesia Across Conversations**: When a developer opens a new conversation or task, all prior decisions, agreed architectures, open tasks, and historical context are lost unless pasted manually.
2. **Hallucinated Blast Radius Analysis**: When asked about the downstream consequences of modifying an API or changing a retry policy, LLMs generate plausible-sounding guesses rather than tracing authoritative architectural dependencies.
3. **Unverifiable Corporate Knowledge Retrieval**: Traditional Retrieval-Augmented Generation (RAG) using vector search chunks documents arbitrarily, losing structural relationships between teams, services, Architecture Decision Records (ADRs), and incident postmortems.

### The Solution: FalkorDB Graph Intelligence Platform
This platform replaces unstructured vector search with **structured graph reasoning and deterministic scoring**:
- **Zero Vector DBs / Zero Embeddings**: Fast, deterministic keyword, token, entity squash matching, and graph-hop expansion.
- **The Definition of Done**: The user tells the LLM to remember an architectural decision in **Session A** → The LLM calls MCP `remember_session_summary` → FalkorDB persists the user-scoped record → In a **brand-new conversation (Session B)** with an empty context window, the user asks about the topic → The LLM autonomously calls `search_user_memory` → The summary is retrieved with scoring breakdown → The LLM answers accurately.
- **Strict Security & Scoping**: No raw Cypher execution tools (`no run_cypher`), no `user_id` leakage in tool schemas, backend-enforced tenant isolation, and payload secret scanning.

---

## 2. System Architecture

```mermaid
flowchart TD
  subgraph Agentic_Client["Agentic Client (e.g. Antigravity IDE)"]
    U[Developer / User] --> Agent[AI Coding Assistant]
    Rule[Memory Policy Rule: .agent/rules/memory-policy.md] -.-> Agent
  end

  subgraph MCP_Layer["Model Context Protocol (stdio transport)"]
    Agent -->|JSON-RPC stdio| M1["atlaspay-reasoning<br/>(4 Tools)"]
    Agent -->|JSON-RPC stdio| M2["atlaspay-memory<br/>(5 Tools)"]
    Agent -->|JSON-RPC stdio| M3["atlaspay-brain<br/>(5 Tools)"]
  end

  subgraph Core_Layer["Shared Python Domain Core (src/graph_intelligence/common/)"]
    M1 --> Core[Domain Core]
    M2 --> Core
    M3 --> Core
    Core --> Ident[identity.py: TrustedIdentity]
    Core --> Valid[validation.py: Secret Scanner & Bounds]
    Core --> Schema[schema.py: Allowlist Validator]
    Core --> Text[text.py: Normalization & Stemming]
    Core --> Adapter[falkordb_client.py: GraphStore Adapter]
  end

  subgraph Database_Layer["Graph Storage"]
    Adapter -->|Redis Protocol :63251| F[(FalkorDB Cloud<br/>Standalone Graph)]
    Seed[Idempotent Seeder: demo_data.json] --> F
  end
```

### Component Breakdown
1. **stdio Transport Layer**: MCP servers communicate over standard input/output using JSON-RPC 2.0. To prevent protocol corruption, **zero logging is emitted to stdout**; all telemetry, audit trails, and debug messages stream to `stderr` as structured JSON.
2. **Domain Core**: Business logic, query builders, validation, and parameter sanitization live strictly within Python domain classes. MCP tool handlers are ultra-thin wrappers that delegate to domain services.
3. **FalkorDB Client Adapter (`falkordb_client.py`)**: The single isolated gateway importing `falkordb`. Wraps driver exceptions into standard domain errors (`DatabaseUnavailable`), parses result headers into clean Python dictionaries, ensures schema indexes, and handles transient socket retries.

---

## 3. Graph Data Model & Schema

The graph maintains strict separation between **Company Knowledge Nodes** (seeded/ingested once, readable by all) and **Private User Memory Nodes** (scoped by `user_id`, readable and writable only by the owning identity).

```mermaid
erDiagram
  Company ||--o{ Team : "BELONGS_TO"
  Person ||--o{ Team : "MEMBER_OF"
  Person ||--o{ Service : "OWNS"
  Service ||--o{ Project : "PART_OF"
  Service ||--o{ Service : "DEPENDS_ON"
  Service ||--o{ Feature : "IMPLEMENTS"
  Incident ||--o{ Service : "AFFECTS"
  Decision ||--o{ Service : "AFFECTS"
  Decision ||--o{ Project : "MADE_FOR"
  Decision ||--o{ Document : "SUPPORTED_BY"
  Decision ||--o{ Incident : "RESPONDS_TO"
  Document ||--o{ Service : "DESCRIBES"
  Document ||--o{ Feature : "DESCRIBES"
  Document ||--o{ Incident : "DESCRIBES"
  Document ||--o{ Decision : "DESCRIBES"

  User ||--o{ SessionSummary : "OWNS_MEMORY"
  SessionSummary ||--o{ Session : "FROM_SESSION"
  SessionSummary ||--o{ Project : "ABOUT_PROJECT"
  SessionSummary ||--o{ Service : "MENTIONS_ENTITY"
  SessionSummary ||--o{ Decision : "MENTIONS_ENTITY"
  SessionSummary ||--o{ SessionSummary : "SUPERSEDES"
  SessionSummary ||--o{ Task : "HAS_TASK"
```

### Allowlisted Labels & Relationships
| Label Category | Labels |
|---|---|
| **Company Knowledge** | `Company`, `Team`, `Person`, `Project`, `Service`, `Feature`, `Incident`, `Decision`, `Document` |
| **User Memory** | `User`, `Session`, `SessionSummary`, `Task` |

Every node carries: `id`, `name`/`title`, `created_at`, `updated_at`, `source` (`seed` | `structured_ingestion` | `llm_mcp_write`), and optional `source_ref`.

---

## 4. Deep Dive: The Three MCP Servers

### Track 1: `atlaspay-reasoning`
Focuses on blast radius calculation, transitive dependencies, and graph connectivity.

#### Tools
1. **`find_service_dependencies(service, direction="both", max_depth=2, limit=25)`**:
   - `direction="dependencies"`: outgoing `[:DEPENDS_ON*1..depth]` (services this service needs).
   - `direction="dependents"`: incoming `[:DEPENDS_ON*1..depth]` (services that rely on this service).
   - `direction="both"`: bidirectional inspection with depth and path evidence.
2. **`analyze_change_impact(target, target_type="Service", change_description=None)`**:
   - Computes full architectural blast radius:
     - `dependents` (depth ≤3) — *"would be affected by interface/behavior change"*
     - `dependencies` (depth ≤2) — *"would see changed traffic/load"*
     - `features` (`[:IMPLEMENTS]`), `decisions` (`[:AFFECTS]`), `incidents` (`[:AFFECTS]`), `owners` (`[:OWNS]`), and `documents` (`[:DESCRIBES]`).
   - If target is a `Feature` or `Decision`, resolves the implementing/affected services and recurses.
3. **`find_graph_path(source, target, max_hops=4)`**:
   - Computes the shortest path between any two arbitrary nodes in the company graph using bounded Breadth-First Search (BFS) in Python over 1-hop neighbor queries.
4. **`search_connected_entities(query, entity_types=None, limit=10)`**:
   - Discovers entities matching squashed tokens or aliases and returns immediate 1-hop connections.

---

### Track 2: `atlaspay-memory` (The Critical Track)
Implements user-scoped persistent session memory written and retrieved by the LLM.

#### Data Model (`SessionSummary`)
```python
{
    "id": "sum_a8f3b29c10de",
    "user_id": "demo-user-herbert",
    "session_id": "ses_49e17b8c2d5a",
    "title": "Three MCP Services Architecture with FalkorDB",
    "summary": "We decided to use three Python MCP services over a shared FalkorDB graph...",
    "keywords": ["falkordb", "mcp", "memory", "architecture"],
    "entity_keys": ["PaymentService"],
    "decisions": ["Use three separate MCP servers"],
    "open_tasks_text": ["Implement shared core package", "Implement retrieval ranking"],
    "project_id": "proj-payment-reliability",
    "importance": "normal",
    "status": "active",  # 'active' | 'superseded' | 'archived'
    "summary_version": 1,
    "supersedes_id": None,
    "content_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "created_at": "2026-10-18T22:00:00+00:00",
}
```

#### Deterministic Retrieval Scoring Formula
When `search_user_memory` is invoked, candidates for the trusted `user_id` are scored deterministically in Python:

$$\text{Total Score} = S_{\text{entity}} + S_{\text{project}} + S_{\text{kw\_phrase}} + S_{\text{kw\_token}} + S_{\text{content}} + S_{\text{graph\_hop}} + S_{\text{recency}} - P_{\text{superseded}}$$

| Signal | Logic | Weight | Cap |
|---|---|---|---|
| **$S_{\text{entity}}$ (Entity Match)** | Resolved entity in query matches summary's linked entity or `entity_keys` | **+5.0** each | Max 15.0 |
| **$S_{\text{project}}$ (Project Match)** | Query project equals summary's `project_id` or `project_name` | **+4.0** | Max 4.0 |
| **$S_{\text{kw\_phrase}}$ (Keyword Phrase)** | Provided search keyword phrase matches a stored keyword | **+3.0** each | Max 12.0 |
| **$S_{\text{kw\_token}}$ (Keyword Tokens)** | Query/keyword token overlap with stored keyword tokens | **+2.0** each | Max 12.0 |
| **$S_{\text{content}}$ (Content Tokens)** | Token overlap with `title` or `summary` body | **+0.5** each | Max 3.0 |
| **$S_{\text{graph\_hop}}$ (Graph Adjacency)**| Summary links an entity directly adjacent (1 hop) to a query entity | **+2.0** | Max 4.0 |
| **$S_{\text{recency}}$ (Linear Decay)** | Linear decay over 30 days: $0.5 \times (1 - \frac{\text{days}}{30})$ | **0.0 to +0.5** | Max 0.5 |
| **$P_{\text{superseded}}$ (Penalty)** | Summary has `status == 'superseded'` | **-3.0** | - |

> **Threshold**: Summaries scoring below **3.0** are dropped. Results are sorted descending by score.

#### Lifecycle & Tools
- **`remember_session_summary(...)`**:
  - Computes SHA-256 hash of normalized title + summary. If identical active summary exists, returns with `deduplicated: true`.
  - Links resolved `Project` (`[:ABOUT_PROJECT]`) and `Service/Incident/Decision` (`[:MENTIONS_ENTITY]`).
  - Creates individual `Task` nodes (`[:HAS_TASK]`).
  - **Read-Back Verification**: Queries the database by ID and user ID before returning `ok: true`.
- **`update_user_memory(summary_id, update_type, ...)`**:
  - `archive`: Sets `status = 'archived'`.
  - `append_context`, `correct`, `supersede`: Creates new `SessionSummary` (`version = old + 1`), sets old summary status to `'superseded'`, creates `(new)-[:SUPERSEDES]->(old)` edge, marks completed tasks as `'done'`, and copies forward active tasks.
  - Enforces `expected_version` concurrency check (returns `CONFLICT` on mismatch).
- **`get_user_memory_timeline(...)`**: Returns chronological chain of memory records.
- **`get_memory_status()`**: Returns scoped memory counts (`active`, `superseded`, `archived`) for the configured user.

---

### Track 3: `atlaspay-brain`
Deterministic company knowledge search and Q&A over the synthetic **AtlasPay** fintech architecture.

#### Tools
- **`answer_company_question(question, project=None)`**:
  - **100% Deterministic & Hallucination-Free**: Does NOT invoke another LLM.
  - Resolves entities using a 60-second cached squash resolver.
  - Matches intent keywords (`owner`, `team`, `why/rationale`, `document`, `incident`, `dependency`, `feature`).
  - Runs allowlisted Cypher traversal templates.
  - Returns structured `facts` with graph `evidence_path` and cited `sources` (`id`, `title`, `uri`, `excerpt`).
  - Explicitly returns knowledge `gaps` if facts are not in the graph (e.g. unknown owners).
- **`get_service_brief(service)`**: Comprehensive ownership, dependency, incident, and runbook catalog.
- **`get_decision_context(decision)`**: Full Architecture Decision Record (ADR) history, motivation, and incident reviews.
- **`search_company_knowledge(query, entity_types=None, limit=10)`**: Entity discovery linked to source documentation.
- **`ingest_company_records(source, records, relationships)`**: Safe structured batch ingestion strictly restricted to company labels.

---

## 5. Shared Domain Core & Security Boundaries

### Security Invariants
1. **No `run_cypher` Tool**: Clients cannot run raw Cypher queries. All traversals are locked behind domain methods.
2. **Identity Isolation (No `user_id` in Tools)**:
   - Tool schemas **never accept `user_id`**.
   - `TrustedIdentity.current()` resolves identity server-side from configuration (`DEMO_USER_ID`).
   - Every Cypher memory query includes `user_id = $uid`.
   - Verified by unit tests introspecting all tool parameters via `test_mcp_tool_schemas.py`.
3. **Parameterization Only**: All user-supplied values are bound via `$params`. Label names, relationship types, and depth numbers cannot be parameterized in Cypher; they are strictly validated against token allowlists and integer bounds before interpolation.
4. **Secret Scanner**:
   - Scans all text payloads for sensitive patterns: `password=`, `api_key=`, `Bearer `, `sk-...`, `-----BEGIN RSA PRIVATE KEY-----`.
   - Calculates Shannon entropy on tokens ($> 4.2$ entropy over 32+ characters is rejected with `INVALID_INPUT`).
5. **No stdout Writes**: Standard output is reserved exclusively for JSON-RPC MCP framing. All application logs use a custom JSON formatter streaming to `stderr`.

---

## 6. FalkorDB Field Learnings & Opportunities for Improvement

During the development, integration, and live testing against **FalkorDB Cloud** (v4.22.0 / falkordb-py 1.8.0), several important nuances were discovered and adapted inside our adapter layer (`falkordb_client.py` and `service.py`). These represent high-value opportunities for FalkorDB engine and SDK enhancements:

### 1. Undirected `shortestPath()` Traversal Support
- **Current Behavior**: FalkorDB raises:
  `redis.exceptions.ResponseError: FalkorDB does not currently support undirected shortestPath traversals`
  when evaluating patterns such as `MATCH p = shortestPath((a)-[*..4]-(b))`.
- **Engine Adaptation**: Our platform implemented a bounded Breadth-First Search (BFS) in Python utilizing 1-hop neighbor queries (`MATCH (a {id: $id})-[r]-(b)`).
- **Recommendation for FalkorDB**: Native engine support for undirected shortest path traversals (standard openCypher compliance) would significantly improve performance and developer ergonomics for blast-radius and knowledge graph discovery queries.

### 2. Clause Flexibility for Path Functions
- **Current Behavior**: FalkorDB requires `shortestPath` to be used in `WITH` or `RETURN` clauses (`FalkorDB currently only supports shortestPaths in WITH or RETURN clauses`), disallowing `MATCH p = shortestPath(...)`.
- **Recommendation for FalkorDB**: Align `MATCH p = shortestPath(...)` with the openCypher specification to allow direct path assignment in `MATCH` statements.

### 3. Idempotent Index Creation (`IF NOT EXISTS`)
- **Current Behavior**: Executing `CREATE INDEX FOR (n:Service) ON (n.id)` when the index already exists raises:
  `Query attempt failed: Attribute 'id' is already indexed`
- **Adapter Adaptation**: `GraphStore.ensure_indexes()` queries `CALL db.indexes()` first to inspect existing indexes, and catches the `"already indexed"` string without resetting the connection.
- **Recommendation for FalkorDB**: Support `CREATE INDEX IF NOT EXISTS FOR (n:Label) ON (n.property)` so index creation can be fully declarative and idempotent.

### 4. Python SDK QueryResult Header Consistency
- **Current Behavior**: `QueryResult.header` in `falkordb-py` returns raw nested pairs `[[1, 'col_name']]` where index 0 is an internal type integer and index 1 is the column name (sometimes as raw bytes).
- **Adapter Adaptation**: Built an unpacker in `falkordb_client.py`:
  ```python
  col = h[1] if isinstance(h, (list, tuple)) and len(h) > 1 else h
  if isinstance(col, bytes):
      col = col.decode("utf-8")
  ```
- **Recommendation for FalkorDB SDK**: Provide a clean property `QueryResult.column_names: list[str]` or return rows directly as dictionaries via `QueryResult.to_dicts()`.

---

## 7. Verification & Test Suite (33/33 Passing)

The repository includes a comprehensive, multi-tiered test suite that runs against unit mocks, live FalkorDB Cloud instances, and live JSON-RPC stdio subprocesses:

```bash
.\.venv\Scripts\pytest.exe tests -v
```

### Test Results
```text
============================= test session starts =============================
platform win32 -- Python 3.14.0, pytest-9.1.1, pluggy-1.7.0
rootdir: C:\Users\HerbertThomas\Documents\HB\Projects\GraphHacks
configfile: pyproject.toml
plugins: anyio-4.15.1
collected 33 items

tests/integration/test_company_brain.py::test_answer_company_question_acceptance PASSED [  3%]
tests/integration/test_company_brain.py::test_get_service_brief PASSED   [  6%]
tests/integration/test_company_brain.py::test_get_decision_context PASSED [  9%]
tests/integration/test_company_brain.py::test_unknown_question_reports_gaps PASSED [ 12%]
tests/integration/test_memory.py::test_track2_full_memory_lifecycle PASSED [ 15%]
tests/integration/test_reasoning.py::test_find_service_dependencies PASSED [ 18%]
tests/integration/test_reasoning.py::test_analyze_change_impact_paymentservice PASSED [ 21%]
tests/integration/test_reasoning.py::test_find_graph_path PASSED         [ 24%]
tests/integration/test_seed.py::test_seed_idempotency_and_verification PASSED [ 27%]
tests/mcp_smoke/test_stdio_servers.py::test_reasoning_server_stdio[asyncio] PASSED [ 30%]
tests/mcp_smoke/test_stdio_servers.py::test_memory_server_stdio[asyncio] PASSED [ 33%]
tests/mcp_smoke/test_stdio_servers.py::test_brain_server_stdio[asyncio] PASSED [ 36%]
tests/unit/test_demo_data_integrity.py::test_demo_data_counts PASSED     [ 39%]
tests/unit/test_demo_data_integrity.py::test_demo_data_schema_labels_and_edges PASSED [ 42%]
tests/unit/test_identity.py::test_trusted_identity_resolution PASSED     [ 45%]
tests/unit/test_mcp_tool_schemas.py::test_tool_counts PASSED             [ 48%]
tests/unit/test_mcp_tool_schemas.py::test_no_user_id_in_any_tool_schema PASSED [ 51%]
tests/unit/test_retrieval_scoring.py::test_scoring_weights PASSED        [ 54%]
tests/unit/test_retrieval_scoring.py::test_superseded_penalty PASSED     [ 57%]
tests/unit/test_retrieval_scoring.py::test_unrelated_query_scores_low PASSED [ 60%]
tests/unit/test_schema.py::test_allowed_labels PASSED                    [ 63%]
tests/unit/test_schema.py::test_company_vs_memory_isolation PASSED       [ 66%]
tests/unit/test_schema.py::test_allowed_relationships PASSED             [ 69%]
tests/unit/test_schema.py::test_validate_relationship_type PASSED        [ 72%]
tests/unit/test_text.py::test_normalize_term PASSED                      [ 75%]
tests/unit/test_text.py::test_squash PASSED                              [ 78%]
tests/unit/test_text.py::test_tokenize PASSED                            [ 81%]
tests/unit/test_text.py::test_extract_keywords PASSED                    [ 84%]
tests/unit/test_validation.py::test_scan_for_secrets_detects_patterns PASSED [ 87%]
tests/unit/test_validation.py::test_scan_for_secrets_clean_input PASSED  [ 90%]
tests/unit/test_validation.py::test_validate_text_length PASSED          [ 93%]
tests/unit/test_validation.py::test_validate_list_size PASSED            [ 96%]
tests/unit/test_validation.py::test_validate_int_range PASSED            [100%]

============================= 33 passed in 50.13s =============================
```

---

## 8. Live Demo Runbook & Prompt Storyboard

To provide a 100% leak-free, authentic demo where the AI assistant cannot read code files from the local directory:
1. Open the clean demo workspace created at **`c:\Users\HerbertThomas\Documents\HB\Projects\AtlasPay-Demo`**.
2. It contains **only** [`.agent/rules/memory-policy.md`](file:///c:/Users/HerbertThomas/Documents/HB/Projects/AtlasPay-Demo/.agent/rules/memory-policy.md) and zero source files.
3. The MCP servers communicate over stdio to FalkorDB Cloud.

### Step 1: Company Brain (Track 3)
```text
Who owns PaymentService, which team are they on, why did AtlasPay choose idempotency keys, and which document supports that decision?
```
- **Observed Behavior**: Agent calls `answer_company_question`.
- **Returned Facts**: Maya Chen owns PaymentService (Payments team); ADR-014 was accepted to prevent duplicate charges during timeouts (`INC-PAY-019`); cites document `doc-adr-014` ("ADR-014 Idempotency Keys").

---

### Step 2: Blast Radius Reasoning (Track 1)
```text
If PaymentService changes its retry behavior, which services or features could be affected? Show the paths.
```
- **Observed Behavior**: Agent calls `analyze_change_impact`.
- **Returned Graph Facts**: Dependents (`API Gateway`), dependencies (`LedgerService`, `RiskEngine`, `NotificationService`), implemented features (`Bounded Retry Policy`, `Idempotent Payment Processing`), and governing decisions (`ADR-021`).

---

### Step 3: Session A — Memory Write (Track 2)
```text
We decided to use three Python MCP services over a shared FalkorDB graph. The memory service saves summaries per user and retrieves them in later sessions by topic. Save a concise summary of this session — the architecture decision, the reason, keywords, and next steps — so I can continue later.
```
- **Observed Behavior**: Agent calls `remember_session_summary`.
- **Result**: Summary persisted to FalkorDB; returns real `summary_id` (e.g. `sum_...`) with status `active` (version 1).

---

### Step 4: Session B — Cross-Session Retrieval in a Brand-New Conversation
> **Start a new conversation tab in Antigravity. Do NOT paste prior context.**

```text
I'm ready to implement the FalkorDB MCP memory feature. What architecture did we choose, and what were the next steps?
```
- **Observed Behavior**: Agent recognizes reference to prior decisions and invokes `search_user_memory`.
- **Result**: FalkorDB returns Session A's summary; agent answers with exact architecture decisions and next steps grounded in graph memory.

---

### Step 5: Session C — Versioned Memory Update
```text
Update that memory: the shared core is implemented, and the next task is to test retrieval ranking. Keep the original decision history.
```
- **Observed Behavior**: Agent calls `update_user_memory` (`update_type: "append_context"`).
- **Result**: Version 2 created; Version 1 marked `superseded` and linked via `(v2)-[:SUPERSEDES]->(v1)`.

---

## 9. Deployment & Quickstart

### 1. Installation
```bash
git clone https://github.com/herbert-bevan/falkordb-graph-intelligence.git
cd falkordb-graph-intelligence
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

### 2. Environment Configuration
Create `.env` in the repository root:
```dotenv
FALKORDB_HOST=your-instance.cloud.falkordb.com
FALKORDB_PORT=6379
FALKORDB_USERNAME=falkordb
FALKORDB_PASSWORD=your-password
FALKORDB_SSL=false
FALKORDB_GRAPH=atlaspay_demo
FALKORDB_GRAPH_TEST=atlaspay_test
DEMO_USER_ID=demo-user-herbert
DEFAULT_PROJECT_ID=proj-payment-reliability
LOG_LEVEL=INFO
```

### 3. Database Initialization & Verification
```powershell
# Check cloud connection
.\.venv\Scripts\python.exe scripts/check_connection.py

# Seed the 31 company nodes & 53 relationships
.\.venv\Scripts\python.exe scripts/seed_demo.py

# Verify counts & integrity
.\.venv\Scripts\python.exe scripts/verify_seed.py
```

### 4. Docker / VPS Deployment
For production or self-hosted deployment:
```bash
docker compose up -d
docker build -t falkordb-graph-intelligence .
```
