"""
Supplier Specialist Agent.
Evaluates suppliers, MOQs, production lead times, and vendor risk profiles.
"""
from typing import List, Dict, Any
from src.agents.base import BaseSupplyChainAgent
from src.models.state import SubAgentDirective, SubAgentOutput
from src.mcp.supplier_mcp import supplier_mcp
from src.tracing.fused_logger import FusedTraceLogger

class SupplierAgent(BaseSupplyChainAgent):
    def __init__(self):
        super().__init__(
            agent_id="supplier_agent",
            role_description="Sourcing strategist, vendor risk evaluator, and purchase order validator."
        )

    def _run_agent_logic(self, directive: SubAgentDirective, tracer: FusedTraceLogger) -> SubAgentOutput:
        target_skus = directive.target_skus or ["MCU-9021"]
        evidence_ids = []
        selected_suppliers = []
        recommendations = []

        for sku in target_skus:
            # 1. MCP Tool Invocation: get_available_suppliers
            res_sups = supplier_mcp.invoke("get_available_suppliers", calling_agent_id=self.agent_id, sku=sku)
            sup_data = res_sups["result"]
            ev1 = res_sups["evidence_unit"]
            tracer.evidence_units.append(ev1)
            evidence_ids.append(ev1.evidence_id)

            suppliers = sup_data.get("suppliers", [])
            if not suppliers:
                continue

            # Sourcing logic: choose based on balance of lead time and reliability
            best_sup = min(suppliers, key=lambda s: (s["lead_time_days"] * 0.6) + ((1.0 - s["on_time_rate"]) * 50))
            
            # 2. MCP Tool Invocation: validate_purchase_order with suggested order
            test_qty = max(best_sup["moq"], 1000)
            res_val = supplier_mcp.invoke(
                "validate_purchase_order", 
                calling_agent_id=self.agent_id, 
                supplier_id=best_sup["supplier_id"], 
                quantity=test_qty
            )
            val_data = res_val["result"]
            ev2 = res_val["evidence_unit"]
            tracer.evidence_units.append(ev2)
            evidence_ids.append(ev2.evidence_id)

            selected_suppliers.append({
                "sku": sku,
                "chosen_supplier_id": best_sup["supplier_id"],
                "supplier_name": best_sup["name"],
                "lead_time_days": best_sup["lead_time_days"],
                "unit_price": best_sup["unit_price"],
                "moq": best_sup["moq"],
                "on_time_rate": best_sup["on_time_rate"]
            })

            recommendations.append({
                "action": "SOURCE_FROM_SUPPLIER",
                "sku": sku,
                "supplier_id": best_sup["supplier_id"],
                "suggested_quantity": test_qty,
                "lead_time_days": best_sup["lead_time_days"],
                "unit_price": best_sup["unit_price"]
            })

        prompt_tokens = 220 + (len(target_skus) * 90)
        comp_tokens = 120 + (len(target_skus) * 55)
        tracer.record_tokens(self.agent_id, prompt_tokens, comp_tokens)

        summary = (
            f"Supplier evaluation complete. "
            + "; ".join([f"{s['sku']}: Sourced from {s['supplier_name']} ({s['lead_time_days']}d lead time, ${s['unit_price']}/unit)" for s in selected_suppliers])
        )

        return SubAgentOutput(
            agent_id=self.agent_id,
            status="SUCCESS",
            summary=summary,
            recommended_actions=recommendations,
            data_payload={"selected_suppliers": selected_suppliers},
            confidence=0.92,
            evidence_ids=evidence_ids,
            token_usage={"prompt_tokens": prompt_tokens, "completion_tokens": comp_tokens}
        )
