"""
LangGraph State Schemas for Supervisor and Specialized Subagents.
Supports parallel fan-out, fan-in aggregation, checkpointing, and conflict arbitration.
"""
from typing import TypedDict, List, Dict, Any, Optional, Annotated
from pydantic import BaseModel, Field
import operator

class SubAgentDirective(BaseModel):
    agent_id: str               # "demand", "inventory", "supplier", "logistics"
    task_description: str
    target_skus: List[str] = Field(default_factory=list)
    priority: str = "HIGH"
    context_data: Dict[str, Any] = Field(default_factory=dict)

class SubAgentOutput(BaseModel):
    agent_id: str
    status: str = "SUCCESS"     # "SUCCESS", "FAILED", "TIMEOUT", "DEGRADED"
    summary: str
    recommended_actions: List[Dict[str, Any]] = Field(default_factory=list)
    data_payload: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = 1.0
    evidence_ids: List[str] = Field(default_factory=list)
    token_usage: Dict[str, int] = Field(default_factory=dict)
    execution_time_ms: float = 0.0

class RiskAssessment(BaseModel):
    composite_risk_score: float  # 0.0 - 1.0
    risk_level: str              # LOW, MODERATE, HIGH, CRITICAL
    stockout_risk_score: float
    supplier_risk_score: float
    logistics_risk_score: float
    risk_factors: List[str] = Field(default_factory=list)
    audit_formula: str           # Reproducible deterministic mathematical formula proof

class ArbitrationDecision(BaseModel):
    conflicts_detected: List[str] = Field(default_factory=list)
    resolution_strategy: str
    final_reorder_quantities: Dict[str, int] = Field(default_factory=dict)
    chosen_supplier_id: Optional[str] = None
    chosen_transport_mode: Optional[str] = None
    tradeoff_rationale: str
    overridden_agent_recommendations: List[Dict[str, Any]] = Field(default_factory=list)

# Reducer functions for LangGraph parallel fan-in
def merge_subagent_outputs(
    existing: List[SubAgentOutput], 
    new_outputs: List[SubAgentOutput]
) -> List[SubAgentOutput]:
    """Combines subagent outputs from parallel branches without overwriting."""
    combined = list(existing or [])
    combined.extend(new_outputs)
    return combined

def merge_messages(existing: List[Dict[str, str]], new_msgs: List[Dict[str, str]]) -> List[Dict[str, str]]:
    combined = list(existing or [])
    combined.extend(new_msgs)
    return combined

class SupplyChainGraphState(TypedDict):
    # Execution Context
    run_id: str
    user_prompt: str
    target_skus: List[str]
    current_step: str
    orchestration_topology: str
    
    # Supervisor Decomposition
    directives: List[SubAgentDirective]
    
    # Subagent Concurrent Results (merged via reducer)
    subagent_outputs: Annotated[List[SubAgentOutput], merge_subagent_outputs]
    
    # Deterministic Risk Computation (non-LLM)
    risk_assessment: Optional[RiskAssessment]
    
    # Arbitration & Final Synthesis
    arbitration: Optional[ArbitrationDecision]
    final_recommendation: Optional[str]
    
    # Diagnostics & Tracing
    active_errors: List[str]
    execution_history: Annotated[List[Dict[str, str]], merge_messages]
    total_tokens_consumed: int
    is_completed: bool
