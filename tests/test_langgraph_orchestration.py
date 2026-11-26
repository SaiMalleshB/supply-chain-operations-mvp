"""
Tests for LangGraph Multi-Agent Orchestration & Checkpointing.
Verifies concurrent subagent fan-out, fan-in state aggregation, and arbitration.
"""
import pytest
from src.orchestration.topologies import TopologyRunner
from src.tracing.fused_logger import FusedTraceLogger
from src.orchestration.graph import create_supply_chain_graph

def test_parallel_langgraph_execution_and_fan_in():
    prompt = "Test emergency demand surge of 35% for MCU-9021."
    trace = TopologyRunner.run_parallel_supervisor(prompt, ["MCU-9021"])
    
    assert trace.status == "COMPLETED"
    assert trace.orchestration_topology == "PARALLEL_SUPERVISOR"
    assert len(trace.execution_units) >= 8
    assert len(trace.evidence_units) >= 6
    assert trace.total_token_accounting.total_tokens > 0

    # Verify all 4 agents participated
    agent_ids = set(u.agent_id for u in trace.execution_units)
    assert "demand_agent" in agent_ids
    assert "inventory_agent" in agent_ids
    assert "supplier_agent" in agent_ids
    assert "logistics_agent" in agent_ids
    assert "supervisor" in agent_ids
    assert "deterministic_risk_engine" in agent_ids

def test_checkpointing_state_preservation():
    tracer = FusedTraceLogger(task_prompt="Checkpoint test", topology="PARALLEL_SUPERVISOR")
    graph = create_supply_chain_graph(tracer=tracer)
    
    initial_state = {
        "run_id": tracer.run_id,
        "user_prompt": "Test checkpoint resume",
        "target_skus": ["MCU-9021"],
        "current_step": "INITIALIZED",
        "orchestration_topology": "PARALLEL_SUPERVISOR",
        "directives": [],
        "subagent_outputs": [],
        "risk_assessment": None,
        "arbitration": None,
        "final_recommendation": None,
        "active_errors": [],
        "execution_history": [],
        "total_tokens_consumed": 0,
        "is_completed": False
    }
    
    config = {"configurable": {"thread_id": tracer.run_id}}
    final_state = graph.invoke(initial_state, config=config)
    
    assert final_state["is_completed"] is True
    assert final_state["risk_assessment"] is not None
    assert final_state["arbitration"] is not None
