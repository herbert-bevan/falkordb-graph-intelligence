# Antigravity Setup & Demo Instructions

Follow these exact steps to connect the three FalkorDB MCP servers to Antigravity and run the cross-session memory and graph reasoning demo.

---

## Step 1: Configure MCP Servers in Antigravity

1. Open this repository (`c:\Users\HerbertThomas\Documents\HB\Projects\GraphHacks`) as your Antigravity workspace.
2. In the Antigravity chat panel, open the settings menu (or click the MCP Server status pill) and navigate to:
   **MCP Servers → Manage MCP Servers → View raw config**
3. Add the three AtlasPay MCP servers to your configuration. Replace `<ABS_REPO_PATH>` with your repository path (`C:\\Users\\HerbertThomas\\Documents\\HB\\Projects\\GraphHacks` on Windows):

```json
{
  "mcpServers": {
    "atlaspay-reasoning": {
      "command": "C:\\Users\\HerbertThomas\\Documents\\HB\\Projects\\GraphHacks\\.venv\\Scripts\\python.exe",
      "args": ["-m", "graph_intelligence.reasoning.mcp_server"]
    },
    "atlaspay-memory": {
      "command": "C:\\Users\\HerbertThomas\\Documents\\HB\\Projects\\GraphHacks\\.venv\\Scripts\\python.exe",
      "args": ["-m", "graph_intelligence.memory.mcp_server"],
      "env": {
        "DEMO_USER_ID": "demo-user-herbert"
      }
    },
    "atlaspay-brain": {
      "command": "C:\\Users\\HerbertThomas\\Documents\\HB\\Projects\\GraphHacks\\.venv\\Scripts\\python.exe",
      "args": ["-m", "graph_intelligence.company_brain.mcp_server"]
    }
  }
}
```

4. Save the configuration and click **Refresh / Reconnect**.
5. Confirm that all three servers show **Connected** and report their tools:
   - `atlaspay-reasoning`: 4 tools (`find_service_dependencies`, `analyze_change_impact`, `find_graph_path`, `search_connected_entities`)
   - `atlaspay-memory`: 5 tools (`remember_session_summary`, `search_user_memory`, `update_user_memory`, `get_user_memory_timeline`, `get_memory_status`)
   - `atlaspay-brain`: 5 tools (`search_company_knowledge`, `get_service_brief`, `get_decision_context`, `answer_company_question`, `ingest_company_records`)

---

## Step 2: Install the Memory Policy Rule

To ensure the agent autonomously invokes memory tools without being prompted for Cypher or IDs:

1. The rule is already installed in your workspace at `.agent/rules/memory-policy.md`.
2. Antigravity automatically detects workspace rules located in `.agent/rules/`.
3. Verify that the rule appears under your workspace customizations/rules list in Antigravity.

---

## Step 3: Run the Live Demo Storyboard

### 1. Company Brain (Track 3)
In your conversation, ask:
> "Who owns PaymentService, which team are they on, why did AtlasPay choose idempotency keys, and which document supports that decision?"

**Expected Behavior**:
The agent invokes `answer_company_question` on `atlaspay-brain`. It answers that **Maya Chen** owns PaymentService on the **Payments** team, cites the motivation for **ADR-014** (duplicate charges during `INC-PAY-019`), and cites document **`doc-adr-014`** ("ADR-014 Idempotency Keys").

---

### 2. Graph Reasoning (Track 1)
Ask:
> "If PaymentService changes its retry behavior, which services or features could be affected? Show the paths."

**Expected Behavior**:
The agent invokes `analyze_change_impact` on `atlaspay-reasoning`. It identifies incoming dependents (e.g. `API Gateway`), outgoing dependencies (`LedgerService`, `RiskEngine`, `NotificationService`), implemented features (`Bounded Retry Policy`, `Idempotent Payment Processing`), and governing decisions (`ADR-021`).

---

### 3. Track 2 Cross-Session Memory Loop (Definition of Done)

#### Session A (Write):
In the current conversation, say:
> "We decided to use three Python MCP services over a shared FalkorDB graph. The memory service saves summaries per user and retrieves them in later sessions by topic. Save a concise summary of this session — the architecture decision, the reason, keywords, and next steps — so I can continue later."

**Expected Behavior**:
- The agent calls `remember_session_summary` on `atlaspay-memory`.
- It confirms persistence only after receiving `ok: true`, citing the newly generated `summary_id` (e.g. `sum_...`).

---

#### Session B (Retrieve across a brand-new conversation):
> **IMPORTANT**: Start a **brand-new conversation** in Antigravity. Do **NOT** paste any context or mention the previous session.

In the new conversation, ask:
> "I'm ready to implement the FalkorDB MCP memory feature. What architecture did we choose, and what were the next steps?"

**Expected Behavior**:
- The agent detects the reference to past work and autonomously calls `search_user_memory` on `atlaspay-memory`.
- The tool returns the Session A summary.
- The agent answers accurately using the retrieved context from FalkorDB.

---

#### Session C (Update):
In that conversation, say:
> "Update that memory: the shared core is implemented, and the next task is to test retrieval ranking. Keep the original decision history."

**Expected Behavior**:
- The agent calls `update_user_memory` with `update_type: "append_context"`.
- It confirms the summary was updated to version 2 with a new `summary_id`.
