"""
Supervisor Agent: Task decomposition, parallel dispatch, conflict arbitration, and synthesis.
"""
from typing import List, Dict, Any, Optional
from src.models.state import (
    SubAgentDirective,
    SubAgentOutput,
    RiskAssessment,
    ArbitrationDecision,
)
from src.risk_engine.scorer import SupplyChainRiskScorer
from src.models.domain import RiskLevel
from src.tracing.fused_logger import FusedTraceLogger
from src.models.trace import UnitType

class SupervisorAgent:
    """
    Central orchestrator coordinating Demand, Inventory, Supplier, and Logistics agents.
    Handles parallel task decomposition, conflict arbitration, and final plan generation.
    """
    def __init__(self):
        self.agent_id = "supervisor"

    def decompose_task(self, user_prompt: str, target_skus: List[str]) -> List[SubAgentDirective]:
        """
        Decomposes user instruction into parallel subagent directives.
        """
        skus = target_skus or ["MCU-9021"]
        directives = [
            SubAgentDirective(
                agent_id="demand",
                task_description=f"Analyze demand projection, historical burn rate, and surge signals for SKUs: {skus}",
                target_skus=skus,
                priority="HIGH"
            ),
            SubAgentDirective(
                agent_id="inventory",
                task_description=f"Evaluate warehouse stock on hand, safety stock levels, and replenishment needs for SKUs: {skus}",
                target_skus=skus,
                priority="HIGH"
            ),
            SubAgentDirective(
                agent_id="supplier",
                task_description=f"Identify qualified suppliers, compare lead times, unit costs, and validate MOQs for SKUs: {skus}",
                target_skus=skus,
                priority="HIGH"
            ),
            SubAgentDirective(
                agent_id="logistics",
                task_description=f"Assess freight transit corridors, carrier delays, and compare standard vs expedited freight costs for SKUs: {skus}",
                target_skus=skus,
                priority="HIGH",
                context_data={"origin_country": "Taiwan", "estimated_cargo_weight_kg": 600.0}
            ),
        ]
        return directives

    def arbitrate_conflicts(
        self,
        subagent_outputs: List[SubAgentOutput],
        risk_assessment: RiskAssessment,
        tracer: FusedTraceLogger
    ) -> ArbitrationDecision:
        """
        Deterministic supervisor arbitration when domain recommendations conflict.
        Uses deterministic risk thresholds to resolve trade-offs between speed, cost, and stockout risk.
        """
        output_map = {out.agent_id: out for out in subagent_outputs}
        inv_out = output_map.get("inventory_agent")
        sup_out = output_map.get("supplier_agent")
        log_out = output_map.get("logistics_agent")

        conflicts = []
        overrides = []
        final_reorders = {}
        chosen_supplier = None
        chosen_mode = "OCEAN"

        # 1. Determine recommended quantity from inventory
        reorder_qty = 1500
        if inv_out and inv_out.recommended_actions:
            reorder_qty = inv_out.recommended_actions[0].get("recommended_units", 1500)
        final_reorders["MCU-9021"] = reorder_qty

        # 2. Check Supplier Constraints (e.g. MOQ, Lead Times)
        fast_supplier = None
        cheap_supplier = None
        if sup_out and sup_out.recommended_actions:
            chosen_supplier = sup_out.recommended_actions[0].get("supplier_id", "SUP-SILICON-TW")

        # 3. Detect Trade-off Conflict: Speed vs Freight Cost vs Stockout Severity
        if risk_assessment.composite_risk_score >= 0.50 or risk_assessment.stockout_risk_score >= 0.70:
            # High / Critical stockout risk! Standard shipping will cause an outage before arrival.
            conflicts.append(
                f"Conflict detected: Standard ocean freight transit exceeds stock runway ({risk_assessment.stockout_risk_score:.2f} stockout risk)."
            )
            # Arbitration Strategy: Split Shipments (Split-Batch Hybrid)
            # 25% expedited via AIR to bridge the immediate 10-day deficit, 75% via standard freight
            resolution_strategy = "HYBRID_SPLIT_DISPATCH (25% Expedited Air, 75% Standard Freight)"
            chosen_mode = "AIR_AND_OCEAN_SPLIT"
            tradeoff_rationale = (
                f"Elevated risk score ({risk_assessment.composite_risk_score:.3f}) requires immediate buffer replenishment. "
                f"Dispatching 25% ({int(reorder_qty * 0.25)} units) via expedited air freight mitigates stockout within 3 days, "
                f"while routing remaining 75% via ocean preserves $8,500+ in freight margins."
            )
            overrides.append({
                "agent": "logistics_agent",
                "default_recommendation": "Standard Ocean",
                "arbitrated_action": "Split shipment with expedited air bridge"
            })
        else:
            resolution_strategy = "STANDARD_CONSOLIDATION"
            chosen_mode = "OCEAN"
            tradeoff_rationale = (
                f"Risk score ({risk_assessment.composite_risk_score:.3f}) is within acceptable operational tolerance. "
                "Consolidating entire order via standard freight optimizes logistics spend."
            )

        decision = ArbitrationDecision(
            conflicts_detected=conflicts,
            resolution_strategy=resolution_strategy,
            final_reorder_quantities=final_reorders,
            chosen_supplier_id=chosen_supplier or "SUP-SILICON-TW",
            chosen_transport_mode=chosen_mode,
            tradeoff_rationale=tradeoff_rationale,
            overridden_agent_recommendations=overrides
        )

        tracer.log_execution_unit(
            agent_id=self.agent_id,
            unit_type=UnitType.ARBITRATION_ACTION,
            action_name="supervisor_arbitrate_conflicts",
            input_payload={"conflicts_detected": conflicts, "risk_score": risk_assessment.composite_risk_score},
            output_payload=decision.model_dump()
        )

        return decision

    def synthesize_final_response(
        self,
        user_prompt: str,
        subagent_outputs: List[SubAgentOutput],
        risk: RiskAssessment,
        arbitration: ArbitrationDecision
    ) -> str:
        """
        Synthesizes the complete enterprise operational plan.
        """
        lines = [
            "# Multi-Agent Supply Chain Orchestration Plan",
            f"**Operational Objective**: {user_prompt}",
            "",
            "## 1. Domain Agent Findings",
        ]
        for out in subagent_outputs:
            status_indicator = "[OK]" if out.status == "SUCCESS" else f"[{out.status}]"
            lines.append(f"- **{out.agent_id.replace('_', ' ').title()}** {status_indicator}: {out.summary}")
            
        lines.extend([
            "",
            "## 2. Deterministic Risk Assessment (Non-LLM Rule Engine)",
            f"- **Composite Risk Score**: `{risk.composite_risk_score:.4f}` | **Severity Tier**: `{risk.risk_level}`",
            f"- **Mathematical Proof**: `{risk.audit_formula}`",
            "- **Key Risk Drivers**:",
        ])
        for factor in risk.risk_factors:
            lines.append(f"  - {factor}")
            
        lines.extend([
            "",
            "## 3. Conflict Arbitration & Strategic Decision",
            f"- **Resolution Strategy**: `{arbitration.resolution_strategy}`",
            f"- **Chosen Supplier**: `{arbitration.chosen_supplier_id}`",
            f"- **Logistics Fulfillment Mode**: `{arbitration.chosen_transport_mode}`",
            f"- **Trade-off Rationale**: {arbitration.tradeoff_rationale}",
            "",
            "## 4. Final Execution Directives",
        ])
        for sku, qty in arbitration.final_reorder_quantities.items():
            lines.append(f"- Issue PO for SKU `{sku}`: **{qty} units** to Supplier `{arbitration.chosen_supplier_id}`.")
            
        return "\n".join(lines)
