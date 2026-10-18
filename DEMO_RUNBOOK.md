# Demo Runbook & Video Storyboard (4–6 Minutes)

This document provides the exact sequence, script, and commands for recording or demonstrating the **FalkorDB Graph Intelligence Platform**.

---

## 1. Pre-Flight Checklist

Before starting the demo or recording:
- [ ] Ensure `.env` is populated with active FalkorDB Cloud credentials.
- [ ] Run the reset-and-seed command to start with a pristine state:
  ```bash
  python scripts/reset_demo.py --yes && python scripts/seed_demo.py && python scripts/verify_seed.py
  ```
- [ ] Confirm in Antigravity that all 3 MCP servers (`atlaspay-reasoning`, `atlaspay-memory`, `atlaspay-brain`) show **Connected**.
- [ ] Ensure `.agent/rules/memory-policy.md` is active as a workspace rule.
- [ ] Ensure `.env` or credentials are NOT visible on screen.

---

## 2. Demo Storyboard Timeline

| Minute | Stage | Action / Prompt | Focus |
|---|---|---|---|
| **0:00 - 1:00** | Introduction & Architecture | Show architecture diagram from README | Explain 3 MCP servers, 1 graph, shared core. Clarify that company data is seeded, but session memory is written live. |
| **1:00 - 2:00** | Track 3: Company Brain | Ask QA question regarding PaymentService ownership, ADR-014, and document source | Show MCP tool invocation, facts returned, and source citation (`doc-adr-014`). |
| **2:00 - 3:00** | Track 1: Graph Reasoning | Ask change impact question regarding PaymentService retry behavior | Show blast radius traversal: incoming dependents (Gateway), outgoing dependencies (Ledger, Risk, Notification), ADRs, and incidents. |
| **3:00 - 4:15** | Track 2: Session A (Write) | Prompt the agent to save architecture decision & next steps | Show `remember_session_summary` call, server persistence verification, and returned `summary_id`. |
| **4:15 - 5:15** | Track 2: Session B (New Conversation Retrieval) | **Open a brand-new conversation** in Antigravity; ask to continue implementation | Show autonomous `search_user_memory` call without context pasting; agent answers from FalkorDB. |
| **5:15 - 6:00** | Track 2: Session C (Update) | Prompt agent to update memory with progress and next steps | Show `update_user_memory`, version bump to v2, and `SUPERSEDES` relationship preservation. |

---

## 3. Exact Prompts to Copy/Paste

### Prompt 1: Company Brain (Track 3)
```text
Who owns PaymentService, which team are they on, why did AtlasPay choose idempotency keys, and which document supports that decision?
```

### Prompt 2: Graph Reasoning (Track 1)
```text
If PaymentService changes its retry behavior, which services or features could be affected? Show the paths.
```

### Prompt 3: Session A - Memory Write (Track 2)
```text
We decided to use three Python MCP services over a shared FalkorDB graph. The memory service saves summaries per user and retrieves them in later sessions by topic. Save a concise summary of this session — the architecture decision, the reason, keywords, and next steps — so I can continue later.
```

### Prompt 4: Session B - Cross-Session Retrieval (Track 2)
*(Open a brand-new Antigravity conversation)*
```text
I'm ready to implement the FalkorDB MCP memory feature. What architecture did we choose, and what were the next steps?
```

### Prompt 5: Session C - Memory Update (Track 2)
```text
Update that memory: the shared core is implemented, and the next task is to test retrieval ranking. Keep the original decision history.
```

---

## 4. Reset Command for Retrying
To wipe private session memory and restore the company graph back to factory seed:
```bash
python scripts/reset_demo.py --yes && python scripts/seed_demo.py && python scripts/verify_seed.py
```
