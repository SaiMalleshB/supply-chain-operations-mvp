"""
Enterprise Multi-Agent Orchestration Platform - Control Dashboard
Aesthetic: Strict Minimalist Monochrome (Black, Slate/Graphite Grey, Crisp White).
"""
import sys
import os
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
import pandas as pd
import json
import time

# Internal imports
from src.orchestration.topologies import TopologyRunner
from src.tracing.query import TraceAuditor
from src.eval.benchmark_harness import ThreeWayBenchmarkHarness
from src.eval.scenarios import EVALUATION_SCENARIOS
from src.db.session import SessionLocal
from src.db.models import DBInventoryItem, DBSupplierProfile, DBLogisticsRoute
from src.config import settings

# 1. Page Configuration
st.set_page_config(
    page_title="Supply Chain Multi-Agent Platform",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Strict Minimalist Monochrome Styling (Black / Greyish / White)
CUSTOM_CSS = """
<style>
    /* Global Base */
    .stApp {
        background-color: #09090b !important;
        color: #f4f4f5 !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    
    /* Headers & Text */
    h1, h2, h3, h4, h5, h6 {
        color: #ffffff !important;
        font-weight: 600 !important;
        letter-spacing: -0.02em;
    }
    p, span, label, div {
        color: #d4d4d8;
    }
    
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #121214 !important;
        border-right: 1px solid #27272a !important;
    }
    
    /* Cards and Containers */
    .mono-card {
        background-color: #18181b;
        border: 1px solid #27272a;
        border-radius: 6px;
        padding: 18px;
        margin-bottom: 16px;
    }
    .mono-card-header {
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #a1a1aa;
        border-bottom: 1px solid #27272a;
        padding-bottom: 8px;
        margin-bottom: 12px;
    }
    .mono-card-value {
        font-size: 1.6rem;
        font-weight: 700;
        color: #ffffff;
    }
    
    /* Metric pill */
    .mono-badge {
        display: inline-block;
        padding: 3px 8px;
        font-size: 0.75rem;
        font-weight: 600;
        border-radius: 4px;
        background-color: #27272a;
        color: #f4f4f5;
        border: 1px solid #3f3f46;
    }
    
    /* Code / Formulas */
    code, pre {
        background-color: #18181b !important;
        color: #f4f4f5 !important;
        border: 1px solid #27272a !important;
        border-radius: 4px !important;
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace !important;
    }
    
    /* Buttons */
    .stButton > button {
        background-color: #f4f4f5 !important;
        color: #09090b !important;
        font-weight: 600 !important;
        border-radius: 4px !important;
        border: 1px solid #ffffff !important;
        transition: all 0.2s ease;
    }
    /* Streamlit renders button labels in nested paragraph/span elements. */
    .stButton > button *, .stButton > button p, .stButton > button span {
        color: #09090b !important;
        opacity: 1 !important;
    }
    .stButton > button:hover {
        background-color: #d4d4d8 !important;
        border-color: #e4e4e7 !important;
        color: #000000 !important;
    }

    /* Tabs */
    button[data-baseweb="tab"] {
        color: #a1a1aa !important;
        font-weight: 500 !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: #ffffff !important;
        border-bottom: 2px solid #ffffff !important;
    }
    
    /* Tables */
    div[data-testid="stDataFrame"] {
        border: 1px solid #27272a !important;
        border-radius: 6px;
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# 3. Sidebar Navigation
st.sidebar.markdown("### **ORCHESTRATOR**")
st.sidebar.markdown(
    "<span class='mono-badge'>LangGraph</span> "
    "<span class='mono-badge'>Local Tool RBAC</span> "
    "<span class='mono-badge'>SQLite</span>",
    unsafe_allow_html=True
)
st.sidebar.markdown("---")
view = st.sidebar.radio(
    "Navigation",
    ["Mission Control", "Data Sources", "Reliability", "Traceability"],
    index=0
)
st.sidebar.markdown("---")
st.sidebar.markdown(
    "<div style='font-size:0.75rem; color:#71717a;'>"
    "Operations • Data Sources • Reliability • Traceability"
    "</div>",
    unsafe_allow_html=True
)

# --- VIEW 1: MISSION CONTROL & LIVE ORCHESTRATION ---
if view == "Mission Control":
    st.title("Enterprise Multi-Agent Operations")
    st.markdown(
        "<div style='color:#a1a1aa; margin-bottom: 20px; font-size: 0.95rem;'>"
        "Analyze a supply chain scenario with local catalog data, resilient specialist agents, deterministic risk scoring, and an auditable run trace."
        "</div>",
        unsafe_allow_html=True
    )

    col_input, col_meta = st.columns([2, 1])

    with col_input:
        selected_scenario_idx = st.selectbox(
            "Select Operational Scenario Template",
            options=range(len(EVALUATION_SCENARIOS)),
            format_func=lambda i: EVALUATION_SCENARIOS[i].title
        )
        template = EVALUATION_SCENARIOS[selected_scenario_idx]
        
        prompt_input = st.text_area(
            "Executive Objective / Task Prompt",
            value=template.description,
            height=100
        )
        sku_selection = st.multiselect(
            "Target SKUs",
            options=["MCU-9021", "ACT-440", "BAT-880", "SENS-102"],
            default=template.target_skus
        )

    with col_meta:
        st.markdown(
            f"""
            <div class='mono-card'>
                <div class='mono-card-header'>Architecture Specifications</div>
                <div style='font-size: 0.85rem; line-height: 1.6; color:#a1a1aa;'>
                    • <b>Supervisor</b>: Centralized Fan-Out / Fan-In<br>
                    • <b>Subagents</b>: 4 Domain Specialists (Concurrent)<br>
                    • <b>Boundaries</b>: In-process tool permissions<br>
                    • <b>Risk Engine</b>: 100% Deterministic (Non-LLM)<br>
                    • <b>Persistence</b>: SQLite traces, in-memory checkpoints
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    if st.button("Execute Multi-Agent Orchestration", use_container_width=True):
        if not prompt_input.strip():
            st.warning("Enter an operational objective to run an analysis.")
            st.stop()
        if not sku_selection:
            st.warning("Select at least one target SKU to run an analysis.")
            st.stop()
        try:
            with st.spinner("Dispatching parallel subagents and checkpointing state..."):
                t_start = time.time()
                trace = TopologyRunner.run_parallel_supervisor(prompt_input, sku_selection)
                dur = (time.time() - t_start) * 1000.0
        except Exception as exc:
            st.error("The analysis could not be completed. Check the database and application logs, then retry.")
            st.exception(exc)
            st.stop()

        st.success(f"Execution complete in {dur:.1f}ms • Run ID: `{trace.run_id}`")

        # Top Metric KPI Row
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.markdown(
                f"""
                <div class='mono-card'>
                    <div class='mono-card-header'>Execution Units</div>
                    <div class='mono-card-value'>{len(trace.execution_units)}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
        with m2:
            st.markdown(
                f"""
                <div class='mono-card'>
                    <div class='mono-card-header'>Evidence Units</div>
                    <div class='mono-card-value'>{len(trace.evidence_units)}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
        with m3:
            st.markdown(
                f"""
                <div class='mono-card'>
                    <div class='mono-card-header'>Total Tokens</div>
                    <div class='mono-card-value'>{trace.total_token_accounting.total_tokens:,}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
        with m4:
            st.markdown(
                f"""
                <div class='mono-card'>
                    <div class='mono-card-header'>Estimated Cost</div>
                    <div class='mono-card-value'>${trace.total_token_accounting.estimated_cost_usd:.5f}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

        # Subagent Detailed Execution Cards
        st.subheader("Subagent Concurrent Execution (Parallel MCP Fan-Out)")
        sub_cols = st.columns(4)
        agent_names = ["demand_agent", "inventory_agent", "supplier_agent", "logistics_agent"]
        display_names = ["Demand Agent", "Inventory Agent", "Supplier Agent", "Logistics Agent"]

        for idx, agent_id in enumerate(agent_names):
            matching_units = [u for u in trace.execution_units if u.agent_id == agent_id and u.action_name.endswith("_completed_task")]
            with sub_cols[idx]:
                if matching_units:
                    unit = matching_units[0]
                    summary_text = unit.output_payload.get("summary", "Complete") if unit.output_payload else "Complete"
                    st.markdown(
                        f"""
                        <div class='mono-card' style='min-height: 220px;'>
                            <div class='mono-card-header'>{display_names[idx]}</div>
                            <div style='font-size:0.75rem; color:#a1a1aa; margin-bottom:8px;'>
                                Latency: <b>{unit.execution_time_ms}ms</b> • Status: <span class='mono-badge'>{unit.status}</span>
                            </div>
                            <div style='font-size:0.85rem; line-height: 1.4; color:#f4f4f5;'>
                                {summary_text}
                            </div>
                            <div style='margin-top:12px; font-size:0.75rem; color:#71717a;'>
                                Evidence refs: {len(unit.evidence_ids)} units
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown(
                        f"""
                        <div class='mono-card'>
                            <div class='mono-card-header'>{display_names[idx]}</div>
                            <div style='font-size:0.85rem; color:#71717a;'>No output record.</div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

        # Risk Engine & Arbitration Section
        st.subheader("Deterministic Risk Scoring & Arbitration")
        col_risk, col_arb = st.columns(2)

        risk_unit = next((u for u in trace.execution_units if u.agent_id == "deterministic_risk_engine"), None)
        arb_unit = next((u for u in trace.execution_units if u.action_name == "supervisor_arbitrate_conflicts"), None)

        with col_risk:
            if risk_unit and risk_unit.output_payload:
                rp = risk_unit.output_payload
                st.markdown(
                    f"""
                    <div class='mono-card'>
                        <div class='mono-card-header'>Mathematical Risk Proof (Non-LLM)</div>
                        <div style='font-size: 1.4rem; font-weight: 700; color: #ffffff; margin-bottom: 6px;'>
                            Composite Score: {rp.get('composite_risk_score', 0):.4f} [{rp.get('risk_level', 'LOW')}]
                        </div>
                        <pre style='padding: 10px; font-size: 0.8rem;'>{rp.get('audit_formula', '')}</pre>
                        <div style='font-size: 0.85rem; color:#d4d4d8; margin-top: 8px;'>
                            <b>Risk Drivers:</b><br>
                            {"<br>".join(["• " + str(f) for f in rp.get('risk_factors', [])])}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

        with col_arb:
            if arb_unit and arb_unit.output_payload:
                ap = arb_unit.output_payload
                st.markdown(
                    f"""
                    <div class='mono-card'>
                        <div class='mono-card-header'>Supervisor Conflict Arbitration</div>
                        <div style='font-size: 1.1rem; font-weight: 700; color: #ffffff; margin-bottom: 6px;'>
                            Strategy: {ap.get('resolution_strategy', 'Standard')}
                        </div>
                        <div style='font-size: 0.85rem; line-height: 1.5; color:#d4d4d8;'>
                            <b>Trade-off Rationale:</b><br>
                            {ap.get('tradeoff_rationale', '')}
                        </div>
                        <div style='margin-top: 10px; font-size: 0.8rem; color:#a1a1aa;'>
                            Supplier: <b>{ap.get('chosen_supplier_id')}</b> • Transit Mode: <b>{ap.get('chosen_transport_mode')}</b>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

        # Final Directives
        synth_unit = next((u for u in trace.execution_units if u.unit_type == "FINAL_SYNTHESIS"), None)
        if synth_unit and synth_unit.output_payload:
            st.subheader("Synthesized Plan Directives")
            st.markdown(synth_unit.output_payload.get("plan", ""))


# --- VIEW 2: TRACEABILITY ---
elif view == "Traceability":
    st.title("Traceability")
    st.markdown(
        "<div style='color:#a1a1aa; margin-bottom: 20px; font-size: 0.95rem;'>"
        "Inspect each run's recorded actions, outputs, evidence, and agent-level history."
        "</div>",
        unsafe_allow_html=True
    )

    runs = TraceAuditor.list_all_runs(limit=30)
    if not runs:
        st.info("No execution runs recorded yet. Execute an analysis in Mission Control.")
    else:
        run_options = {f"{r['run_id']} | {r['topology']} | {r['timestamp'][:19]}": r['run_id'] for r in runs}
        selected_label = st.selectbox("Select Run Artifact", list(run_options.keys()))
        selected_run_id = run_options[selected_label]

        summary = TraceAuditor.get_run_summary(selected_run_id)
        if summary:
            # Summary Metrics
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Run ID", summary["run_id"])
            c2.metric("Topology", summary["topology"])
            c3.metric("Tokens Consumed", f"{summary['total_tokens']:,}")
            c4.metric("Cost ($ USD)", f"${summary['cost_usd']:.5f}")

            tab_exec, tab_evid, tab_filter = st.tabs(["Execution Units (Procedural)", "Evidence Units (Semantic)", "Post-Hoc Agent Filter"])

            with tab_exec:
                exec_units = TraceAuditor.query_tool_calls(selected_run_id)
                if exec_units:
                    df_exec = pd.DataFrame(exec_units)
                    st.dataframe(df_exec[["step", "agent", "type", "action", "status", "execution_time_ms"]], use_container_width=True)
                    st.caption("Expand below to view raw payloads:")
                    st.json(exec_units)
                else:
                    st.write("No execution units found.")

            with tab_evid:
                evid_units = TraceAuditor.query_evidence_for_run(selected_run_id)
                if evid_units:
                    df_evid = pd.DataFrame(evid_units)
                    st.dataframe(df_evid[["evidence_id", "type", "source", "semantic_content", "confidence"]], use_container_width=True)
                    st.caption("Full semantic evidence records:")
                    st.json(evid_units)
                else:
                    st.write("No evidence units found.")

            with tab_filter:
                st.markdown("#### Auditable Query: 'Show me every action taken by Agent X in Run Y'")
                agent_filter = st.selectbox("Filter by Agent", ["supplier_agent", "demand_agent", "inventory_agent", "logistics_agent", "supervisor", "deterministic_risk_engine"])
                filtered_calls = TraceAuditor.query_tool_calls(selected_run_id, agent_id=agent_filter)
                if filtered_calls:
                    st.write(f"Found **{len(filtered_calls)}** procedural actions for `{agent_filter}`:")
                    st.json(filtered_calls)
                else:
                    st.write(f"No actions recorded for `{agent_filter}` in this run.")


# --- VIEW 3: RELIABILITY ---
elif view == "Reliability":
    st.title("Reliability")
    st.markdown(
        "<div style='color:#a1a1aa; margin-bottom: 20px; font-size: 0.95rem;'>"
        "Review run outcomes and the safeguards used when an agent or data operation fails."
        "</div>",
        unsafe_allow_html=True
    )

    recent_runs = TraceAuditor.list_all_runs(limit=100)
    completed_runs = sum(1 for run in recent_runs if run["status"] == "COMPLETED")
    degraded_runs = sum(1 for run in recent_runs if run["status"] in {"DEGRADED", "FAILED"})
    r1, r2, r3 = st.columns(3)
    r1.metric("Recorded runs", len(recent_runs))
    r2.metric("Completed", completed_runs)
    r3.metric("Degraded or failed", degraded_runs)

    st.subheader("Reliability safeguards")
    st.markdown(
        f"- Agents retry failed operations up to **{settings.MAX_SUBAGENT_RETRIES} times** with backoff.\n"
        f"- Partial degradation is **{'enabled' if settings.ALLOW_PARTIAL_DEGRADATION else 'disabled'}**; affected agents are marked in the run trace.\n"
        "- Risk scoring is deterministic and runs against the selected SKU and local catalog records.\n"
        "- Graph checkpoints are in memory; run traces are stored in SQLite."
    )

    if recent_runs:
        st.caption("Most recent runs")
        st.dataframe(pd.DataFrame(recent_runs)[["run_id", "status", "retries", "degraded_agents", "tokens", "timestamp"]], use_container_width=True)
    else:
        st.info("No runs recorded yet. Execute an analysis in Mission Control to start collecting reliability history.")

    with st.expander("Optional: compare orchestration topologies"):
        st.caption("This demo benchmark runs 12 local scenarios and can take a few moments.")

        if st.button("Run topology comparison", use_container_width=True):
            try:
                with st.spinner("Running local scenarios across three topologies..."):
                    harness = ThreeWayBenchmarkHarness()
                    df_results = harness.run_full_suite()
                    st.session_state["benchmark_df"] = df_results
                st.success("Topology comparison completed.")
            except Exception as exc:
                st.error("The comparison stopped before completion. Existing results remain available if present.")
                st.exception(exc)

        if "benchmark_df" in st.session_state:
            df = st.session_state["benchmark_df"]
            st.subheader("Topology comparison results")
            st.dataframe(df, use_container_width=True)

# --- VIEW 4: DATA SOURCES ---
elif view == "Data Sources":
    st.title("Data Sources")
    st.markdown(
        "<div style='color:#a1a1aa; margin-bottom: 20px; font-size: 0.95rem;'>"
        "See what feeds each analysis, where it is stored, and which values are simulated."
        "</div>",
        unsafe_allow_html=True
    )

    st.subheader("Source map")
    source_rows = [
        {"Analysis data": "Inventory stock, burn rates, costs", "Source": "SQLite catalog: inventory_items", "How it is produced": "Seeded local records in data/supply_chain.db; editable through the database."},
        {"Analysis data": "Supplier qualification, prices, lead times", "Source": "SQLite catalog: supplier_profiles", "How it is produced": "Seeded local supplier records; matched to the selected SKU."},
        {"Analysis data": "Routes, delays, freight rates", "Source": "SQLite catalog: logistics_routes", "How it is produced": "Seeded local route records; quotes are calculated from rate × estimated weight."},
        {"Analysis data": "Demand forecast", "Source": "Calculated from inventory daily burn rate", "How it is produced": "30-day baseline multiplied by a fixed SKU-specific scenario factor."},
        {"Analysis data": "Market signals", "Source": "Hard-coded demo signals", "How it is produced": "Synthetic examples in the demand tool; not a live market feed."},
        {"Analysis data": "Risk score", "Source": "Deterministic risk engine", "How it is produced": "Formula applied to local stock, supplier, and route fields."},
    ]
    st.dataframe(pd.DataFrame(source_rows), use_container_width=True, hide_index=True)
    st.info("This MVP uses seeded local data and simulated demand signals. It does not connect to live ERP, supplier, carrier, or market systems.")

    try:
        db = SessionLocal()
        items = db.query(DBInventoryItem).all()
        suppliers = db.query(DBSupplierProfile).all()
        routes = db.query(DBLogisticsRoute).all()

        st.subheader("Inventory Stock Catalog")
        df_inv = pd.DataFrame([{
            "SKU": i.sku,
            "Product": i.name,
            "Category": i.category,
            "Stock": i.current_stock,
            "Safety Stock": i.safety_stock,
            "Burn Rate/d": i.daily_burn_rate,
            "Unit Cost": f"${i.unit_cost}",
            "Warehouse": i.warehouse_location
        } for i in items])
        st.dataframe(df_inv, use_container_width=True)

        st.subheader("Qualified Sourcing Suppliers")
        df_sup = pd.DataFrame([{
            "Supplier ID": s.supplier_id,
            "Name": s.name,
            "Country": s.country,
            "SKUs": ", ".join(s.skus_provided),
            "Lead Time (d)": s.lead_time_days,
            "MOQ": s.min_order_quantity,
            "On-Time Rate": f"{s.historical_on_time_delivery_rate*100:.1f}%",
            "Defect Rate": f"{s.historical_defect_rate*100:.2f}%",
            "Geo Risk": s.geopolitical_risk_score,
            "Single Source": s.is_single_source
        } for s in suppliers])
        st.dataframe(df_sup, use_container_width=True)

        st.subheader("Logistics Corridors & Transport Modes")
        df_routes = pd.DataFrame([{
            "Route ID": r.route_id,
            "Origin": r.origin,
            "Destination": r.destination,
            "Carrier": r.carrier_name,
            "Mode": r.transport_mode,
            "Std Days": r.standard_transit_days,
            "Air/Exp Days": r.expedited_transit_days,
            "Std $/kg": f"${r.standard_cost_per_kg}",
            "Active Delay (d)": r.current_delay_days,
            "Congestion": r.port_congestion_index
        } for r in routes])
        st.dataframe(df_routes, use_container_width=True)
    except Exception as exc:
        st.error("The catalog could not be loaded. Check the database connection and retry.")
        st.exception(exc)
    finally:
        if "db" in locals():
            db.close()
