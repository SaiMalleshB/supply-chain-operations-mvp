"""
Tests for Model Context Protocol (MCP) Tool Scoping and RBAC.
Verifies domain isolation, authorized execution, and rejection of unauthorized calls.
"""
import pytest
from src.mcp import demand_mcp, inventory_mcp, supplier_mcp, logistics_mcp, MCPPermissionError

def test_authorized_demand_agent_calls():
    # Demand agent invoking get_demand_forecast -> allowed
    res = demand_mcp.invoke("get_demand_forecast", calling_agent_id="demand_agent", sku="MCU-9021")
    assert "result" in res
    assert res["result"]["sku"] == "MCU-9021"
    assert "evidence_unit" in res

def test_authorized_inventory_agent_calls():
    # Inventory agent invoking get_stock_levels -> allowed
    res = inventory_mcp.invoke("get_stock_levels", calling_agent_id="inventory_agent", sku="MCU-9021")
    assert "result" in res
    assert res["result"]["current_stock"] > 0

def test_unauthorized_cross_domain_call_blocked():
    # Supplier Agent attempting to modify or call logistics routing tools -> MUST FAIL
    with pytest.raises(MCPPermissionError) as exc_info:
        logistics_mcp.invoke("get_shipping_lanes", calling_agent_id="supplier_agent", origin_country="Taiwan")
    assert "RBAC Violation" in str(exc_info.value)

def test_unauthorized_inventory_agent_calling_demand_tools():
    # Inventory Agent calling demand tools -> MUST FAIL
    with pytest.raises(MCPPermissionError) as exc_info:
        demand_mcp.invoke("get_demand_forecast", calling_agent_id="inventory_agent", sku="MCU-9021")
    assert "RBAC Violation" in str(exc_info.value)

def test_supervisor_elevated_access():
    # Supervisor has cross-domain read access
    res = supplier_mcp.invoke("get_available_suppliers", calling_agent_id="supervisor", sku="MCU-9021")
    assert "result" in res
