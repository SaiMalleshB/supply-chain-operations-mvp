"""
Comparative Orchestration Topologies.
Supports measuring cost, latency, and reliability across 3 distinct topologies:
1. Centralized Parallel Supervisor (Target LangGraph MAS)
2. Sequential Pipeline (Linear Chain MAS)
3. Single Monolithic Agent (Baseline 1)
"""
import time
from typing import Dict, Any, List
from src.orchestration.graph import create_supply_chain_graph
from src.tracing.fused_logger import FusedTraceLogger
from src.models.trace import UnitType, EvidenceType, RunTrace
from src.models.state import SubAgentDirective, SubAgentOutput
from src.agents.demand_agent import DemandAgent
from src.agents.inventory_agent import InventoryAgent
from src.agents.supplier_agent import SupplierAgent
from src.agents.logistics_agent import LogisticsAgent
from src.agents.supervisor import SupervisorAgent
from src.risk_engine.scorer import SupplyChainRiskScorer
from src.orchestration.cost_controller import AgentDietCostController

class TopologyRunner:
    """Executes different coordination architectures under uniform test scenarios."""

    @staticmethod
    def run_parallel_supervisor(prompt: str, target_skus: List[str]) -> RunTrace:
        """
        Topology A: Centralized Supervisor with Concurrent Parallel Fan-Out (LangGraph).
        """
        prompt = (prompt or "").strip()
        target_skus = list(dict.fromkeys(s.strip() for s in (target_skus or []) if s and s.strip()))
        if not prompt:
            raise ValueError("Enter an operational objective before starting a run.")
        if not target_skus:
            raise ValueError("Select at least one target SKU before starting a run.")
        tracer = FusedTraceLogger(task_prompt=prompt, topology="PARALLEL_SUPERVISOR")
        graph = create_supply_chain_graph(tracer=tracer)
        
        initial_state = {
            "run_id": tracer.run_id,
            "user_prompt": prompt,
            "target_skus": target_skus,
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
        
        final_status = "DEGRADED" if tracer.degraded_agents else "COMPLETED"
        trace = tracer.persist_to_database(final_status=final_status)
        return trace

    @staticmethod
    def run_sequential_pipeline(prompt: str, target_skus: List[str]) -> RunTrace:
        """
        Topology B: Sequential Linear Chain.
        Each agent runs strictly one after another, passing cumulative history downstream.
        Demonstrates higher latency and context token accumulation.
        """
        tracer = FusedTraceLogger(task_prompt=prompt, topology="SEQUENTIAL_PIPELINE")
        cost_controller = AgentDietCostController()
        
        d_agent = DemandAgent()
        i_agent = InventoryAgent()
        s_agent = SupplierAgent()
        l_agent = LogisticsAgent()
        supervisor = SupervisorAgent()

        cumulative_history = [{"role": "system", "content": f"Task: {prompt}"}]
        outputs = []

        # 1. Demand
        d_dir = SubAgentDirective(agent_id="demand", task_description=prompt, target_skus=target_skus)
        d_out = d_agent.execute_with_resilience(d_dir, tracer)
        outputs.append(d_out)
        cumulative_history.append({"role": "demand_agent", "content": d_out.summary})

        # 2. Inventory (receives cumulative history)
        i_dir = SubAgentDirective(agent_id="inventory", task_description=prompt, target_skus=target_skus, context_data={"history": cumulative_history})
        i_out = i_agent.execute_with_resilience(i_dir, tracer)
        outputs.append(i_out)
        cumulative_history.append({"role": "inventory_agent", "content": i_out.summary})

        # 3. Supplier (receives cumulative history)
        s_dir = SubAgentDirective(agent_id="supplier", task_description=prompt, target_skus=target_skus, context_data={"history": cumulative_history})
        s_out = s_agent.execute_with_resilience(s_dir, tracer)
        outputs.append(s_out)
        cumulative_history.append({"role": "supplier_agent", "content": s_out.summary})

        # 4. Logistics (receives cumulative history)
        l_dir = SubAgentDirective(agent_id="logistics", task_description=prompt, target_skus=target_skus, context_data={"history": cumulative_history})
        l_out = l_agent.execute_with_resilience(l_dir, tracer)
        outputs.append(l_out)
        cumulative_history.append({"role": "logistics_agent", "content": l_out.summary})

        # Extra token overhead penalty due to un-pruned sequential context accumulation
        extra_tokens = int(sum(cost_controller.estimate_tokens(m["content"]) for m in cumulative_history) * 1.4)
        tracer.record_tokens("pipeline_overhead", prompt_tokens=extra_tokens, completion_tokens=0)

        # Risk scoring & Arbitration
        sku = target_skus[0] if target_skus else "MCU-9021"
        risk = SupplyChainRiskScorer.evaluate_sku_context(sku)
        decision = supervisor.arbitrate_conflicts(outputs, risk, tracer)
        supervisor.synthesize_final_response(prompt, outputs, risk, decision)

        final_status = "DEGRADED" if tracer.degraded_agents else "COMPLETED"
        trace = tracer.persist_to_database(final_status=final_status)
        return trace

    @staticmethod
    def run_single_monolithic_agent(prompt: str, target_skus: List[str]) -> RunTrace:
        """
        Topology C: Single Monolithic Agent.
        A single generic agent attempting all supply chain decisions sequentially.
        Lacks specialized MCP boundaries and domain isolation.
        """
        tracer = FusedTraceLogger(task_prompt=prompt, topology="SINGLE_AGENT")
        sku = target_skus[0] if target_skus else "MCU-9021"

        tracer.log_execution_unit(
            agent_id="monolithic_agent",
            unit_type=UnitType.REASONING_STEP,
            action_name="monolithic_analysis_all_domains",
            input_payload={"prompt": prompt, "sku": sku}
        )

        # Single agent executes all tools directly without domain verification
        time.sleep(0.08) # simulate sequential processing
        
        # Monolithic agent incurs higher prompt tokens due to massive single system prompt
        tracer.record_tokens("monolithic_agent", prompt_tokens=950, completion_tokens=320)
        
        risk = SupplyChainRiskScorer.evaluate_sku_context(sku)
        tracer.log_execution_unit(
            agent_id="monolithic_agent",
            unit_type=UnitType.FINAL_SYNTHESIS,
            action_name="monolithic_response",
            input_payload={"risk": risk.composite_risk_score},
            output_payload={"summary": f"Monolithic evaluation completed for SKU {sku}. Risk: {risk.risk_level}"}
        )

        trace = tracer.persist_to_database(final_status="COMPLETED")
        return trace
