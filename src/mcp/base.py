"""
Model Context Protocol (MCP) Base Architecture with Role-Based Access Control (RBAC).
Enforces tool isolation per agent and produces structured Evidence Units for tracing.
"""
from typing import Callable, Dict, Any, List, Optional
import inspect
from src.models.trace import EvidenceUnit, EvidenceType

class MCPPermissionError(PermissionError):
    """Raised when an agent attempts to call a tool outside its permitted boundary."""
    pass

class ToolDefinition:
    def __init__(self, name: str, description: str, func: Callable, allowed_agents: List[str]):
        self.name = name
        self.description = description
        self.func = func
        self.allowed_agents = allowed_agents
        self.parameters = inspect.signature(func).parameters

class MCPServerRegistry:
    """
    Central MCP Server managing tool registry, agent access control boundaries,
    and automatic evidence unit generation.
    """
    def __init__(self, domain: str):
        self.domain = domain
        self._tools: Dict[str, ToolDefinition] = {}

    def register_tool(self, name: str, description: str, allowed_agents: List[str]):
        def decorator(func: Callable):
            self._tools[name] = ToolDefinition(
                name=name,
                description=description,
                func=func,
                allowed_agents=allowed_agents
            )
            return func
        return decorator

    def list_tools_for_agent(self, agent_id: str) -> List[Dict[str, Any]]:
        """Returns tool schemas only for tools the agent is authorized to call."""
        available = []
        for name, tool in self._tools.items():
            if agent_id in tool.allowed_agents or "supervisor" in tool.allowed_agents:
                available.append({
                    "name": tool.name,
                    "description": tool.description,
                    "domain": self.domain,
                    "parameters": [
                        {"name": p_name, "type": str(param.annotation), "required": param.default == inspect.Parameter.empty}
                        for p_name, param in tool.parameters.items()
                    ]
                })
        return available

    def invoke(self, tool_name: str, calling_agent_id: str, **kwargs) -> Dict[str, Any]:
        """
        Invokes an MCP tool with strict RBAC enforcement.
        Returns a dict containing `result` and a generated `evidence_unit`.
        """
        if tool_name not in self._tools:
            raise KeyError(f"Tool '{tool_name}' not found in MCP domain '{self.domain}'.")

        tool = self._tools[tool_name]
        
        # Enforce RBAC boundary
        if calling_agent_id not in tool.allowed_agents and calling_agent_id != "supervisor":
            raise MCPPermissionError(
                f"RBAC Violation: Agent '{calling_agent_id}' is unauthorized to invoke tool '{tool_name}' in domain '{self.domain}'. Allowed agents: {tool.allowed_agents}"
            )

        # Execute tool
        result_data = tool.func(**kwargs)

        # Generate semantic Evidence Unit (arXiv:2606.04990)
        evidence = EvidenceUnit(
            evidence_type=EvidenceType.MCP_TOOL_RESULT,
            source_agent_or_tool=f"mcp::{self.domain}::{tool_name}",
            semantic_content=f"Agent '{calling_agent_id}' executed '{tool_name}' with args {kwargs} -> {result_data.get('summary', str(result_data))}",
            raw_data={"tool": tool_name, "args": kwargs, "output": result_data},
            confidence_score=1.0
        )

        return {
            "result": result_data,
            "evidence_unit": evidence
        }
