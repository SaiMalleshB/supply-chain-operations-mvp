# Supply Chain Operations MVP

A local-first prototype for supply chain incident analysis. It runs a Streamlit dashboard with seeded SQLite catalog data, deterministic specialist agents, risk scoring, and run traces.

## MVP scope

- No API key, Docker service, or network connection is needed for the default local run.
- SQLite stores the catalog and run traces. LangGraph uses an in-memory checkpointer, so graph checkpoints do not survive a process restart.
- Agent outputs are rule-based and use local catalog data; they are not live LLM responses, supplier quotes, or logistics feeds.
- The MCP-style registry enforces in-process tool permissions. This project does not start separate MCP server processes.
- PostgreSQL schema and configuration are included for experimentation, but SQLite is the supported default path.

---

## 1. System Architecture & Literature Foundation

```
                           ┌────────────────────────────────────────┐
                           │          User / Mission Control        │
                           └──────────────────┬─────────────────────┘
                                              │
                           ┌──────────────────▼─────────────────────┐
                           │    LangGraph Supervisor Orchestrator   │
                           │ (Decomposition, in-memory checkpoint) │
                           └──────┬───────────┬───────────┬─────────┘
              ┌───────────────────┼───────────┴───────────┼───────────────────┐
              ▼                   ▼                       ▼                   ▼
      ┌───────────────┐   ┌───────────────┐       ┌───────────────┐   ┌───────────────┐
      │ Demand Agent  │   │Inventory Agent│       │Supplier Agent │   │Logistics Agent│
      └───────┬───────┘   └───────┬───────┘       └───────┬───────┘   └───────┬───────┘
              │ (MCP RBAC)        │ (MCP RBAC)            │ (MCP RBAC)        │ (MCP RBAC)
              ▼                   ▼                       ▼                   ▼
      ┌───────────────┐   ┌───────────────┐       ┌───────────────┐   ┌───────────────┐
      │  Demand MCP   │   │ Inventory MCP │       │  Supplier MCP │   │ Logistics MCP │
      └───────┬───────┘   └───────┬───────┘       └───────┬───────┘   └───────┬───────┘
              └───────────────────┼───────────────────────┼───────────────────┘
                                  ▼                       ▼
                  ┌───────────────────────────────┐ ┌─────────────────────────┐
                  │ Deterministic Risk Engine     │ │ Fused Audit & Debug     │
                  │ (Rule-Based, Non-LLM Math)   │ │ Trace Store (SQLite)   │
                  └───────────────────────────────┘ └─────────────────────────┘
```

### Research Grounding & Key Contributions Preserved

1. **Cost as a Function of Orchestration Topology** (*arXiv:2501.06322, MDPI 18/6/326, MultiAgentBench*):
   - Compares **Centralized Parallel Supervisor** vs **Sequential Chain Pipeline** vs **Single Monolithic Agent**.
   - Demonstrates that sequential pipelines incur a 25%–45% token cost penalty due to downstream context accumulation without pruning.
2. **Fused Audit and Debug Tracing into a Single Artifact** (*arXiv:2606.04990*):
   - Rather than disjoint systems for compliance vs debugging, every run produces a unified trace containing **Procedural Execution Units** (actions, inputs, outputs, timestamps) linked to **Semantic Evidence Units** (tool data, observations, policies, confidence scores).
3. **AgentDiet Token Control & Sliding Window Pruning** (*arXiv:2509.23586*):
   - Applies token thresholding (skips compression on short contexts to save compute) and sliding window context retention to protect against runaway loop costs.
4. **Deterministic Risk Scoring Engine (Zero LLM)**:
   - 100% auditable, reproducible mathematical formulas for stockout shortfall, vendor reliability, and freight delay risks, producing an exact verifiable arithmetic proof for compliance.
5. **Strict MCP RBAC Boundaries**:
   - Model Context Protocol servers isolate tool access per agent (e.g., supplier agent cannot access freight routing tools), throwing `MCPPermissionError` on unauthorized invocations.

---

## 2. Minimalist Monochrome Design

All UI views follow a strict minimalist, enterprise-grade grayscale palette:
- **Backgrounds**: Slate/Graphite Black (`#09090b` / `#121214`)
- **Card Panels**: `#18181b` with subtle `#27272a` borders
- **Typography**: Clean high-contrast white (`#ffffff`) and zinc grey (`#a1a1aa`)
- **Accent Elements**: Monochrome badges and crisp borders, zero distracting neon colors.

---

## 3. Quick Start & Execution

### Prerequisites
- Python 3.11+
- Virtual environment with dependencies installed (via `uv` or `pip`)

### Running the Local Dashboard
Run from the project root:
```bash
.venv\Scripts\python.exe -m streamlit run src/ui/app.py
```
The dashboard includes:
- **Mission Control**: Scenario execution with agent cards, deterministic risk calculations, and plan directives.
- **Data Sources**: Review local catalog inputs, simulated demand signals, and risk calculations.
- **Reliability**: Review run outcomes, retries, degraded agents, and optional topology comparisons.
- **Traceability**: Inspect execution actions, outputs, evidence, and agent history on a dedicated page.

The database path is resolved relative to the project, so launching Streamlit from another working directory does not create a second empty database.

### Running Automated Test Suite
Run the unit and integration tests covering risk engine math, MCP boundaries, LangGraph state machine, and fused tracing:
```bash
.venv\Scripts\pytest tests/ -v
```

---

## 4. Project Structure

```
capstone/
├── README.md                      # Project architecture & setup documentation
├── requirements.txt               # Pinned Python package dependencies
├── docker-compose.yml             # PostgreSQL 16 + pgvector container definition
├── data/
│   ├── supply_chain.db            # Out-of-the-box local SQLite database
│   └── supply_chain_schema.sql    # PostgreSQL + pgvector relational schema
├── src/
│   ├── config.py                  # Pydantic environment settings and budgets
│   ├── models/
│   │   ├── domain.py              # Inventory, Supplier, Route, and Incident schemas
│   │   ├── state.py               # LangGraph StateGraph schema & reducers
│   │   └── trace.py               # ExecutionUnit & EvidenceUnit schemas (arXiv:2606.04990)
│   ├── db/
│   │   ├── session.py             # SQLAlchemy connection & automatic seed loader
│   │   └── models.py              # Database ORM models (relational + traces)
│   ├── risk_engine/
│   │   ├── metrics.py             # Deterministic mathematical formulas & proofs
│   │   └── scorer.py              # Non-LLM Risk Scoring Service
│   ├── mcp/
│   │   ├── base.py                # MCP registry with RBAC permission boundaries
│   │   ├── demand_mcp.py          # Forecasting & market signal tools
│   │   ├── inventory_mcp.py       # Stock level & safety buffer tools
│   │   ├── supplier_mcp.py        # Vendor catalog, MOQ & lead time tools
│   │   └── logistics_mcp.py       # Shipping routes & freight quote tools
│   ├── agents/
│   │   ├── base.py                # Resilience wrapper (retry, backoff, degradation)
│   │   ├── supervisor.py          # Central orchestrator & arbitration engine
│   │   ├── demand_agent.py        # Demand forecasting specialist
│   │   ├── inventory_agent.py     # Stock replenishment specialist
│   │   ├── supplier_agent.py      # Vendor sourcing specialist
│   │   └── logistics_agent.py     # Freight routing specialist
│   ├── orchestration/
│   │   ├── graph.py               # LangGraph parallel supervisor state machine
│   │   ├── topologies.py          # 3 Topologies: Parallel, Sequential, Monolithic
│   │   └── cost_controller.py     # AgentDiet sliding-window pruner & token tracker
│   ├── tracing/
│   │   ├── fused_logger.py        # Unified audit + debug trace collector
│   │   └── query.py               # Post-hoc trace query & audit service
│   ├── eval/
│   │   ├── scenarios.py           # 4 supply chain benchmark incident scenarios
│   │   └── benchmark_harness.py   # Three-way baseline evaluation harness
│   └── ui/
│       └── app.py                 # Minimalist monochrome Streamlit dashboard
└── tests/
    ├── test_risk_engine.py        # Mathematical bounds & reproducibility tests
    ├── test_mcp_rbac.py           # Tool boundary isolation & RBAC violation tests
    ├── test_langgraph_orchestration.py  # Checkpointing & parallel execution tests
    └── test_fused_traces.py       # Fused audit queries & topology cost tests
```
