"""
Demand Specialist Agent.
Analyzes demand forecasting, sales projections, and market signal volatility.
"""
from typing import List
from src.agents.base import BaseSupplyChainAgent
from src.models.state import SubAgentDirective, SubAgentOutput
from src.mcp.demand_mcp import demand_mcp
from src.tracing.fused_logger import FusedTraceLogger

class DemandAgent(BaseSupplyChainAgent):
    def __init__(self):
        super().__init__(
            agent_id="demand_agent",
            role_description="Demand forecasting specialist and market trend evaluator."
        )

    def _run_agent_logic(self, directive: SubAgentDirective, tracer: FusedTraceLogger) -> SubAgentOutput:
        target_skus = directive.target_skus or ["MCU-9021"]
        evidence_ids = []
        forecasts = []
        recommendations = []

        for sku in target_skus:
            # 1. MCP Tool Invocation: get_demand_forecast
            res_fc = demand_mcp.invoke("get_demand_forecast", calling_agent_id=self.agent_id, sku=sku)
            fc_data = res_fc["result"]
            ev1 = res_fc["evidence_unit"]
            tracer.evidence_units.append(ev1)
            evidence_ids.append(ev1.evidence_id)

            # 2. MCP Tool Invocation: get_market_signals
            res_sig = demand_mcp.invoke("get_market_signals", calling_agent_id=self.agent_id, sku=sku)
            sig_data = res_sig["result"]
            ev2 = res_sig["evidence_unit"]
            tracer.evidence_units.append(ev2)
            evidence_ids.append(ev2.evidence_id)

            forecasts.append({
                "sku": sku,
                "projected_30d": fc_data.get("projected_30d_demand"),
                "surge_percentage": fc_data.get("surge_percentage"),
                "volatility": sig_data.get("demand_volatility")
            })

            recommendations.append({
                "action": "ADJUST_PLANNED_BUFFER",
                "sku": sku,
                "target_demand_30d": fc_data.get("projected_30d_demand"),
                "surge_multiplier": 1.0 + (fc_data.get("surge_percentage", 0) / 100.0)
            })

        # Token accounting (estimated)
        prompt_tokens = 180 + (len(target_skus) * 75)
        comp_tokens = 95 + (len(target_skus) * 45)
        tracer.record_tokens(self.agent_id, prompt_tokens, comp_tokens)

        summary = (
            f"Demand analysis for {len(target_skus)} SKU(s). "
            + "; ".join([f"{f['sku']}: {f['projected_30d']} units projected (+{f['surge_percentage']}%)" for f in forecasts])
        )

        return SubAgentOutput(
            agent_id=self.agent_id,
            status="SUCCESS",
            summary=summary,
            recommended_actions=recommendations,
            data_payload={"forecasts": forecasts},
            confidence=0.94,
            evidence_ids=evidence_ids,
            token_usage={"prompt_tokens": prompt_tokens, "completion_tokens": comp_tokens}
        )
