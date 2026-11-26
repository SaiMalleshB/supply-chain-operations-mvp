"""
Logistics Specialist Agent.
Evaluates freight lanes, transit times, shipping modes (AIR vs OCEAN vs ROAD), and port delays.
"""
from typing import List, Dict, Any
from src.agents.base import BaseSupplyChainAgent
from src.models.state import SubAgentDirective, SubAgentOutput
from src.mcp.logistics_mcp import logistics_mcp
from src.tracing.fused_logger import FusedTraceLogger

class LogisticsAgent(BaseSupplyChainAgent):
    def __init__(self):
        super().__init__(
            agent_id="logistics_agent",
            role_description="Freight routing coordinator, carrier evaluator, and transit time estimator."
        )

    def _run_agent_logic(self, directive: SubAgentDirective, tracer: FusedTraceLogger) -> SubAgentOutput:
        origin_country = directive.context_data.get("origin_country", "Taiwan")
        weight_kg = directive.context_data.get("estimated_cargo_weight_kg", 500.0)
        evidence_ids = []
        route_options = []
        recommendations = []

        # 1. MCP Tool Invocation: get_shipping_lanes
        res_lanes = logistics_mcp.invoke("get_shipping_lanes", calling_agent_id=self.agent_id, origin_country=origin_country)
        lane_data = res_lanes["result"]
        ev1 = res_lanes["evidence_unit"]
        tracer.evidence_units.append(ev1)
        evidence_ids.append(ev1.evidence_id)

        lanes = lane_data.get("lanes", [])
        if lanes:
            # 2. MCP Tool Invocation: calculate_freight_quote for primary candidate routes
            for l in lanes[:2]:
                is_expedited = (l["mode"] == "AIR")
                res_quote = logistics_mcp.invoke(
                    "calculate_freight_quote",
                    calling_agent_id=self.agent_id,
                    route_id=l["route_id"],
                    cargo_weight_kg=weight_kg,
                    expedite=is_expedited
                )
                quote_data = res_quote["result"]
                ev_q = res_quote["evidence_unit"]
                tracer.evidence_units.append(ev_q)
                evidence_ids.append(ev_q.evidence_id)
                
                route_options.append(quote_data)

            # Recommend fastest vs lowest cost
            air_option = next((r for r in route_options if r.get("transport_mode") == "AIR"), None)
            ocean_option = next((r for r in route_options if r.get("transport_mode") == "OCEAN"), route_options[0])

            recommendations.append({
                "action": "STANDARD_ROUTING",
                "route_id": ocean_option.get("route_id"),
                "mode": ocean_option.get("transport_mode"),
                "transit_days": ocean_option.get("effective_transit_days"),
                "cost_usd": ocean_option.get("freight_cost_usd")
            })

            if air_option:
                recommendations.append({
                    "action": "EXPEDITED_FALLBACK",
                    "route_id": air_option.get("route_id"),
                    "mode": "AIR",
                    "transit_days": air_option.get("effective_transit_days"),
                    "cost_usd": air_option.get("freight_cost_usd")
                })

        prompt_tokens = 210
        comp_tokens = 115
        tracer.record_tokens(self.agent_id, prompt_tokens, comp_tokens)

        summary = (
            f"Logistics options analyzed for {origin_country}. "
            + "; ".join([f"{r['transport_mode']}: {r['effective_transit_days']}d (${r['freight_cost_usd']})" for r in route_options])
        )

        return SubAgentOutput(
            agent_id=self.agent_id,
            status="SUCCESS",
            summary=summary,
            recommended_actions=recommendations,
            data_payload={"routes": route_options},
            confidence=0.95,
            evidence_ids=evidence_ids,
            token_usage={"prompt_tokens": prompt_tokens, "completion_tokens": comp_tokens}
        )
