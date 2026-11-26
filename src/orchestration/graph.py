"""
LangGraph Multi-Agent Orchestration Graph.
Implements the Centralized Parallel Supervisor topology with durable checkpointing,
deterministic non-LLM risk scoring, and conflict arbitration.
"""
from typing import Dict, Any, List
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from src.models.state import SupplyChainGraphState, SubAgentDirective
from src.agents.supervisor import SupervisorAgent
from src.agents.demand_agent import DemandAgent
from src.agents.inventory_agent import InventoryAgent
from src.agents.supplier_agent import SupplierAgent
from src.agents.logistics_agent import LogisticsAgent
from src.risk_engine.scorer import SupplyChainRiskScorer
from src.tracing.fused_logger import FusedTraceLogger
from src.models.trace import UnitType

# Shared in-memory checkpointer; checkpoints are cleared when the process exits.
default_checkpointer = InMemorySaver()

def create_supply_chain_graph(
    tracer: FusedTraceLogger,
    checkpointer: Any = default_checkpointer
):
    """
    Constructs the LangGraph state machine with parallel subagent execution branches.
    """
    supervisor = SupervisorAgent()
    demand_agent = DemandAgent()
    inventory_agent = InventoryAgent()
    supplier_agent = SupplierAgent()
    logistics_agent = LogisticsAgent()

    # --- Node Definitions ---

    def supervisor_plan(state: SupplyChainGraphState) -> Dict[str, Any]:
        tracer.log_execution_unit(
            agent_id="supervisor",
            unit_type=UnitType.SUPERVISOR_DISPATCH,
            action_name="decompose_task",
            input_payload={"prompt": state["user_prompt"], "skus": state["target_skus"]}
        )
        directives = supervisor.decompose_task(state["user_prompt"], state["target_skus"])
        return {
            "directives": directives,
            "current_step": "SUPERVISOR_DECOMPOSED",
            "execution_history": [{"role": "supervisor", "content": f"Dispatched {len(directives)} parallel subagent directives."}]
        }

    def run_demand(state: SupplyChainGraphState) -> Dict[str, Any]:
        directive = next((d for d in state["directives"] if d.agent_id == "demand"), None)
        if not directive:
            directive = SubAgentDirective(agent_id="demand", task_description="Default demand analysis", target_skus=state["target_skus"])
        output = demand_agent.execute_with_resilience(directive, tracer)
        return {
            "subagent_outputs": [output],
            "execution_history": [{"role": "demand_agent", "content": output.summary}]
        }

    def run_inventory(state: SupplyChainGraphState) -> Dict[str, Any]:
        directive = next((d for d in state["directives"] if d.agent_id == "inventory"), None)
        if not directive:
            directive = SubAgentDirective(agent_id="inventory", task_description="Default inventory analysis", target_skus=state["target_skus"])
        output = inventory_agent.execute_with_resilience(directive, tracer)
        return {
            "subagent_outputs": [output],
            "execution_history": [{"role": "inventory_agent", "content": output.summary}]
        }

    def run_supplier(state: SupplyChainGraphState) -> Dict[str, Any]:
        directive = next((d for d in state["directives"] if d.agent_id == "supplier"), None)
        if not directive:
            directive = SubAgentDirective(agent_id="supplier", task_description="Default supplier analysis", target_skus=state["target_skus"])
        output = supplier_agent.execute_with_resilience(directive, tracer)
        return {
            "subagent_outputs": [output],
            "execution_history": [{"role": "supplier_agent", "content": output.summary}]
        }

    def run_logistics(state: SupplyChainGraphState) -> Dict[str, Any]:
        directive = next((d for d in state["directives"] if d.agent_id == "logistics"), None)
        if not directive:
            directive = SubAgentDirective(agent_id="logistics", task_description="Default logistics analysis", target_skus=state["target_skus"])
        output = logistics_agent.execute_with_resilience(directive, tracer)
        return {
            "subagent_outputs": [output],
            "execution_history": [{"role": "logistics_agent", "content": output.summary}]
        }

    def run_risk_engine(state: SupplyChainGraphState) -> Dict[str, Any]:
        """Runs the deterministic non-LLM risk scoring service on aggregated subagent outputs."""
        sku = state["target_skus"][0] if state["target_skus"] else "MCU-9021"
        assessment = SupplyChainRiskScorer.evaluate_sku_context(sku)
        
        tracer.log_execution_unit(
            agent_id="deterministic_risk_engine",
            unit_type=UnitType.REASONING_STEP,
            action_name="evaluate_composite_risk",
            input_payload={"sku": sku},
            output_payload=assessment.model_dump()
        )
        return {
            "risk_assessment": assessment,
            "current_step": "RISK_EVALUATED",
            "execution_history": [{"role": "risk_engine", "content": f"Deterministic Composite Risk: {assessment.composite_risk_score} [{assessment.risk_level}]"}]
        }

    def supervisor_arbitrate(state: SupplyChainGraphState) -> Dict[str, Any]:
        """Resolves trade-offs between conflicting domain recommendations."""
        decision = supervisor.arbitrate_conflicts(
            subagent_outputs=state["subagent_outputs"],
            risk_assessment=state["risk_assessment"],
            tracer=tracer
        )
        return {
            "arbitration": decision,
            "current_step": "ARBITRATED",
            "execution_history": [{"role": "supervisor", "content": f"Arbitration strategy chosen: {decision.resolution_strategy}"}]
        }

    def supervisor_synthesize(state: SupplyChainGraphState) -> Dict[str, Any]:
        """Generates the unified final operational plan."""
        final_text = supervisor.synthesize_final_response(
            user_prompt=state["user_prompt"],
            subagent_outputs=state["subagent_outputs"],
            risk=state["risk_assessment"],
            arbitration=state["arbitration"]
        )
        tracer.log_execution_unit(
            agent_id="supervisor",
            unit_type=UnitType.FINAL_SYNTHESIS,
            action_name="synthesize_response",
            input_payload={"prompt": state["user_prompt"]},
            output_payload={"plan": final_text}
        )
        return {
            "final_recommendation": final_text,
            "current_step": "COMPLETED",
            "is_completed": True,
            "execution_history": [{"role": "supervisor", "content": "Final execution directives generated."}]
        }

    # --- Build StateGraph ---
    workflow = StateGraph(SupplyChainGraphState)

    workflow.add_node("supervisor_plan", supervisor_plan)
    workflow.add_node("demand_node", run_demand)
    workflow.add_node("inventory_node", run_inventory)
    workflow.add_node("supplier_node", run_supplier)
    workflow.add_node("logistics_node", run_logistics)
    workflow.add_node("risk_node", run_risk_engine)
    workflow.add_node("arbitrate_node", supervisor_arbitrate)
    workflow.add_node("synthesize_node", supervisor_synthesize)

    # Topology: Parallel Fan-Out
    workflow.add_edge(START, "supervisor_plan")
    workflow.add_edge("supervisor_plan", "demand_node")
    workflow.add_edge("supervisor_plan", "inventory_node")
    workflow.add_edge("supervisor_plan", "supplier_node")
    workflow.add_edge("supervisor_plan", "logistics_node")

    # Topology: Fan-In Aggregation to Risk Node
    workflow.add_edge("demand_node", "risk_node")
    workflow.add_edge("inventory_node", "risk_node")
    workflow.add_edge("supplier_node", "risk_node")
    workflow.add_edge("logistics_node", "risk_node")

    # Sequential Post-Processing
    workflow.add_edge("risk_node", "arbitrate_node")
    workflow.add_edge("arbitrate_node", "synthesize_node")
    workflow.add_edge("synthesize_node", END)

    app = workflow.compile(checkpointer=checkpointer)
    return app
