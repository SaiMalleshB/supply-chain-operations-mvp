"""
Demand MCP Server: forecasting, sales trends, and market signal analysis.
Allowed Agent: 'demand_agent' (and 'supervisor').
"""
from src.mcp.base import MCPServerRegistry
from src.db.session import SessionLocal
from src.db.models import DBInventoryItem
from typing import Dict, Any

demand_mcp = MCPServerRegistry(domain="demand")

@demand_mcp.register_tool(
    name="get_demand_forecast",
    description="Fetches 30-day forecast, confidence intervals, and current market trend for a SKU.",
    allowed_agents=["demand_agent"]
)
def get_demand_forecast(sku: str) -> Dict[str, Any]:
    db = SessionLocal()
    try:
        item = db.query(DBInventoryItem).filter(DBInventoryItem.sku == sku).first()
        if not item:
            return {"error": f"SKU {sku} not found", "summary": f"SKU {sku} missing"}
        
        # Simulated demand modeling based on baseline burn rate
        base_30d = int(item.daily_burn_rate * 30)
        # Check if there is an active demand surge scenario
        surge_factor = 1.35 if sku in ["MCU-9021", "BAT-880"] else 1.05
        projected_30d = int(base_30d * surge_factor)
        
        return {
            "sku": sku,
            "product_name": item.name,
            "baseline_30d_demand": base_30d,
            "projected_30d_demand": projected_30d,
            "surge_percentage": round((surge_factor - 1.0) * 100, 1),
            "confidence_lower": int(projected_30d * 0.90),
            "confidence_upper": int(projected_30d * 1.15),
            "summary": f"Forecast for {sku} projected at {projected_30d} units (+{round((surge_factor - 1.0)*100, 1)}% trend)."
        }
    finally:
        db.close()

@demand_mcp.register_tool(
    name="get_market_signals",
    description="Retrieves leading market indicators and seasonal promotions.",
    allowed_agents=["demand_agent"]
)
def get_market_signals(sku: str) -> Dict[str, Any]:
    signals = [
        {"source": "Automotive Tier-1 OEM Orders", "indicator": "SURGE", "confidence": 0.92},
        {"source": "Consumer Tech Market Survey", "indicator": "ELEVATED", "confidence": 0.85}
    ]
    return {
        "sku": sku,
        "market_signals": signals,
        "demand_volatility": "HIGH" if sku.startswith("MCU") else "NORMAL",
        "summary": f"High demand volatility detected for {sku} driven by OEM orders."
    }
