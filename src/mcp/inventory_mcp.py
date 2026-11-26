"""
Inventory MCP Server: stock on hand, safety stock levels, and replenishment points.
Allowed Agent: 'inventory_agent' (and 'supervisor').
"""
from src.mcp.base import MCPServerRegistry
from src.db.session import SessionLocal
from src.db.models import DBInventoryItem
from typing import Dict, Any

inventory_mcp = MCPServerRegistry(domain="inventory")

@inventory_mcp.register_tool(
    name="get_stock_levels",
    description="Retrieves current warehouse stock, safety stock, and reorder threshold for a SKU.",
    allowed_agents=["inventory_agent"]
)
def get_stock_levels(sku: str) -> Dict[str, Any]:
    db = SessionLocal()
    try:
        item = db.query(DBInventoryItem).filter(DBInventoryItem.sku == sku).first()
        if not item:
            return {"error": f"SKU {sku} not found", "summary": f"SKU {sku} missing"}
            
        stockout_status = "CRITICAL" if item.current_stock < item.safety_stock else (
            "WARNING" if item.current_stock < item.reorder_point else "HEALTHY"
        )
        runway_days = round(item.current_stock / max(0.1, item.daily_burn_rate), 1)

        return {
            "sku": sku,
            "product_name": item.name,
            "current_stock": item.current_stock,
            "safety_stock": item.safety_stock,
            "reorder_point": item.reorder_point,
            "daily_burn_rate": item.daily_burn_rate,
            "runway_days": runway_days,
            "stockout_status": stockout_status,
            "warehouse_location": item.warehouse_location,
            "summary": f"{sku} stock is {item.current_stock} units ({runway_days} days runway). Status: {stockout_status}."
        }
    finally:
        db.close()

@inventory_mcp.register_tool(
    name="calculate_reorder_need",
    description="Computes recommended reorder quantity to reach safety stock + target buffer.",
    allowed_agents=["inventory_agent"]
)
def calculate_reorder_need(sku: str, target_coverage_days: int = 45) -> Dict[str, Any]:
    db = SessionLocal()
    try:
        item = db.query(DBInventoryItem).filter(DBInventoryItem.sku == sku).first()
        if not item:
            return {"error": f"SKU {sku} not found", "summary": f"SKU {sku} missing"}
            
        target_units = int(item.daily_burn_rate * target_coverage_days) + item.safety_stock
        deficit = max(0, target_units - item.current_stock)
        
        return {
            "sku": sku,
            "target_coverage_days": target_coverage_days,
            "target_stock_units": target_units,
            "recommended_order_quantity": deficit,
            "estimated_inventory_cost": round(deficit * item.unit_cost, 2),
            "summary": f"Recommended reorder for {sku} is {deficit} units (${round(deficit * item.unit_cost, 2)})."
        }
    finally:
        db.close()
