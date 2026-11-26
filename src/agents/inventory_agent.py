"""
Inventory Specialist Agent.
Analyzes warehouse stock runway, safety buffers, and replenishment points.
"""
from typing import List
from src.agents.base import BaseSupplyChainAgent
from src.models.state import SubAgentDirective, SubAgentOutput
from src.mcp.inventory_mcp import inventory_mcp
from src.tracing.fused_logger import FusedTraceLogger

class InventoryAgent(BaseSupplyChainAgent):
    def __init__(self):
        super().__init__(
            agent_id="inventory_agent",
            role_description="Inventory optimization specialist and stock safety monitor."
        )

    def _run_agent_logic(self, directive: SubAgentDirective, tracer: FusedTraceLogger) -> SubAgentOutput:
        target_skus = directive.target_skus or ["MCU-9021"]
        evidence_ids = []
        stock_profiles = []
        recommendations = []

        for sku in target_skus:
            # 1. MCP Tool Invocation: get_stock_levels
            res_stock = inventory_mcp.invoke("get_stock_levels", calling_agent_id=self.agent_id, sku=sku)
            stock_data = res_stock["result"]
            ev1 = res_stock["evidence_unit"]
            tracer.evidence_units.append(ev1)
            evidence_ids.append(ev1.evidence_id)

            # 2. MCP Tool Invocation: calculate_reorder_need
            res_reorder = inventory_mcp.invoke("calculate_reorder_need", calling_agent_id=self.agent_id, sku=sku, target_coverage_days=45)
            reorder_data = res_reorder["result"]
            ev2 = res_reorder["evidence_unit"]
            tracer.evidence_units.append(ev2)
            evidence_ids.append(ev2.evidence_id)

            stock_profiles.append({
                "sku": sku,
                "current_stock": stock_data.get("current_stock"),
                "runway_days": stock_data.get("runway_days"),
                "stockout_status": stock_data.get("stockout_status"),
                "recommended_order_quantity": reorder_data.get("recommended_order_quantity")
            })

            recommendations.append({
                "action": "TRIGGER_REORDER",
                "sku": sku,
                "recommended_units": reorder_data.get("recommended_order_quantity"),
                "urgency": "HIGH" if stock_data.get("stockout_status") == "CRITICAL" else "MEDIUM"
            })

        prompt_tokens = 200 + (len(target_skus) * 80)
        comp_tokens = 110 + (len(target_skus) * 50)
        tracer.record_tokens(self.agent_id, prompt_tokens, comp_tokens)

        summary = (
            f"Inventory review completed. "
            + "; ".join([f"{p['sku']}: {p['runway_days']}d runway ({p['stockout_status']}), needs {p['recommended_order_quantity']} units" for p in stock_profiles])
        )

        return SubAgentOutput(
            agent_id=self.agent_id,
            status="SUCCESS",
            summary=summary,
            recommended_actions=recommendations,
            data_payload={"stock_profiles": stock_profiles},
            confidence=0.96,
            evidence_ids=evidence_ids,
            token_usage={"prompt_tokens": prompt_tokens, "completion_tokens": comp_tokens}
        )
