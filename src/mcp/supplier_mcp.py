"""
Supplier MCP Server: vendor catalogs, lead times, MOQs, unit pricing, and defect history.
Allowed Agent: 'supplier_agent' (and 'supervisor').
"""
from src.mcp.base import MCPServerRegistry
from src.db.session import SessionLocal
from src.db.models import DBSupplierProfile
from typing import Dict, Any, List

supplier_mcp = MCPServerRegistry(domain="supplier")

@supplier_mcp.register_tool(
    name="get_available_suppliers",
    description="Lists all qualified suppliers supplying a given SKU with prices, MOQs, and lead times.",
    allowed_agents=["supplier_agent"]
)
def get_available_suppliers(sku: str) -> Dict[str, Any]:
    db = SessionLocal()
    try:
        all_sups = db.query(DBSupplierProfile).all()
        matching = [s for s in all_sups if sku in s.skus_provided]
        
        results = []
        for s in matching:
            results.append({
                "supplier_id": s.supplier_id,
                "name": s.name,
                "country": s.country,
                "unit_price": s.unit_price,
                "lead_time_days": s.lead_time_days,
                "moq": s.min_order_quantity,
                "on_time_rate": s.historical_on_time_delivery_rate,
                "defect_rate": s.historical_defect_rate,
                "geopolitical_risk": s.geopolitical_risk_score,
                "is_single_source": s.is_single_source
            })
            
        return {
            "sku": sku,
            "qualified_suppliers_count": len(results),
            "suppliers": results,
            "summary": f"Found {len(results)} suppliers for {sku}. Fastest lead time: {min([r['lead_time_days'] for r in results]) if results else 'N/A'} days."
        }
    finally:
        db.close()

@supplier_mcp.register_tool(
    name="validate_purchase_order",
    description="Validates supplier minimum order quantities, lead time constraints, and total batch cost.",
    allowed_agents=["supplier_agent"]
)
def validate_purchase_order(supplier_id: str, quantity: int) -> Dict[str, Any]:
    db = SessionLocal()
    try:
        sup = db.query(DBSupplierProfile).filter(DBSupplierProfile.supplier_id == supplier_id).first()
        if not sup:
            return {"valid": False, "reason": f"Supplier {supplier_id} not found", "summary": "Invalid supplier"}
            
        meets_moq = quantity >= sup.min_order_quantity
        total_cost = round(quantity * sup.unit_price, 2)
        
        return {
            "supplier_id": supplier_id,
            "supplier_name": sup.name,
            "quantity_ordered": quantity,
            "min_order_quantity": sup.min_order_quantity,
            "meets_moq": meets_moq,
            "unit_price": sup.unit_price,
            "total_material_cost": total_cost,
            "production_lead_time_days": sup.lead_time_days,
            "summary": f"Order of {quantity} units at {sup.name} {'meets MOQ' if meets_moq else 'VIOLATES MOQ'}. Total: ${total_cost}."
        }
    finally:
        db.close()
