"""
Tests for Fused Trace Artifacts (arXiv:2606.04990) and Post-Hoc Audit Queries.
"""
import pytest
from src.tracing.fused_logger import FusedTraceLogger
from src.tracing.query import TraceAuditor
from src.orchestration.topologies import TopologyRunner

def test_fused_trace_generation_and_audit():
    trace = TopologyRunner.run_parallel_supervisor("Trace test prompt", ["BAT-880"])
    
    # Query run summary
    summary = TraceAuditor.get_run_summary(trace.run_id)
    assert summary is not None
    assert summary["run_id"] == trace.run_id
    assert summary["total_tokens"] > 0
    
    # Query tool calls specifically for logistics_agent
    logistics_calls = TraceAuditor.query_tool_calls(trace.run_id, agent_id="logistics_agent")
    assert len(logistics_calls) >= 1
    
    # Query evidence units
    evid_units = TraceAuditor.query_evidence_for_run(trace.run_id)
    assert len(evid_units) >= 1
    assert any(e["source"].startswith("mcp::") for e in evid_units)

def test_comparative_topologies_token_overhead():
    prompt = "Benchmark topology cost"
    trace_parallel = TopologyRunner.run_parallel_supervisor(prompt, ["MCU-9021"])
    trace_seq = TopologyRunner.run_sequential_pipeline(prompt, ["MCU-9021"])
    
    # Sequential pipeline accumulates context history and has higher tokens
    assert trace_seq.total_token_accounting.total_tokens >= trace_parallel.total_token_accounting.total_tokens
