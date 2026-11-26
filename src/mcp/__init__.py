from src.mcp.base import MCPServerRegistry, MCPPermissionError
from src.mcp.demand_mcp import demand_mcp
from src.mcp.inventory_mcp import inventory_mcp
from src.mcp.supplier_mcp import supplier_mcp
from src.mcp.logistics_mcp import logistics_mcp

ALL_MCP_REGISTRIES = {
    "demand": demand_mcp,
    "inventory": inventory_mcp,
    "supplier": supplier_mcp,
    "logistics": logistics_mcp
}

__all__ = [
    "MCPServerRegistry",
    "MCPPermissionError",
    "demand_mcp",
    "inventory_mcp",
    "supplier_mcp",
    "logistics_mcp",
    "ALL_MCP_REGISTRIES",
]
