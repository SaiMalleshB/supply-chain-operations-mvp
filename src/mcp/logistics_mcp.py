"""
Logistics MCP Server: shipping lanes, freight rates, transit times, and port congestion.
Allowed Agent: 'logistics_agent' (and 'supervisor').
"""
from src.mcp.base import MCPServerRegistry
from src.db.session import SessionLocal
from src.db.models import DBLogisticsRoute
from typing import Dict, Any, List

logistics_mcp = MCPServerRegistry(domain="logistics")

@logistics_mcp.register_tool(
    name="get_shipping_lanes",
    description="Lists all transport corridors between origin and destination with rates and delays.",
    allowed_agents=["logistics_agent"]
)
def get_shipping_lanes(origin_country: str) -> Dict[str, Any]:
    db = SessionLocal()
    try:
        routes = db.query(DBLogisticsRoute).all()
        matching = [r for r in routes if origin_country.lower() in r.origin.lower()]
        if not matching:
            matching = routes # fallback
            
        lane_options = []
        for r in matching:
            lane_options.append({
                "route_id": r.route_id,
                "origin": r.origin,
                "destination": r.destination,
                "carrier": r.carrier_name,
                "mode": r.transport_mode,
                "standard_days": r.standard_transit_days,
                "expedited_days": r.expedited_transit_days,
                "standard_cost_per_kg": r.standard_cost_per_kg,
                "expedited_cost_per_kg": r.expedited_cost_per_kg,
                "delay_days": r.current_delay_days,
                "port_congestion": r.port_congestion_index
            })
            
        return {
            "origin_filter": origin_country,
            "routes_count": len(lane_options),
            "lanes": lane_options,
            "summary": f"Found {len(lane_options)} transport routes. Available modes: {list(set([l['mode'] for l in lane_options]))}."
        }
    finally:
        db.close()

@logistics_mcp.register_tool(
    name="calculate_freight_quote",
    description="Calculates freight cost and estimated delivery date based on mode (AIR vs OCEAN vs ROAD).",
    allowed_agents=["logistics_agent"]
)
def calculate_freight_quote(route_id: str, cargo_weight_kg: float, expedite: bool = False) -> Dict[str, Any]:
    db = SessionLocal()
    try:
        route = db.query(DBLogisticsRoute).filter(DBLogisticsRoute.route_id == route_id).first()
        if not route:
            return {"error": f"Route {route_id} not found", "summary": "Invalid route"}
            
        rate_per_kg = route.expedited_cost_per_kg if expedite else route.standard_cost_per_kg
        total_freight_cost = round(cargo_weight_kg * rate_per_kg, 2)
        base_transit = route.expedited_transit_days if expedite else route.standard_transit_days
        total_transit_days = base_transit + route.current_delay_days
        
        return {
            "route_id": route_id,
            "carrier": route.carrier_name,
            "transport_mode": route.transport_mode,
            "expedited": expedite,
            "cargo_weight_kg": cargo_weight_kg,
            "freight_cost_usd": total_freight_cost,
            "base_transit_days": base_transit,
            "active_delay_days": route.current_delay_days,
            "effective_transit_days": total_transit_days,
            "summary": f"{route.transport_mode} transit via {route.carrier_name}: {total_transit_days} days, cost: ${total_freight_cost}."
        }
    finally:
        db.close()
