"""
Unified Trace Schemas (Execution Units + Evidence Units).
Grounded in arXiv:2606.04990 (Provenance-grounded tracing for LLM multi-agent systems).
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
import uuid

class UnitType(str, Enum):
    # Execution Unit Subtypes (Procedural)
    REASONING_STEP = "REASONING_STEP"
    TOOL_INVOCATION = "TOOL_INVOCATION"
    TOOL_OUTPUT = "TOOL_OUTPUT"
    INTER_AGENT_MESSAGE = "INTER_AGENT_MESSAGE"
    SUPERVISOR_DISPATCH = "SUPERVISOR_DISPATCH"
    ARBITRATION_ACTION = "ARBITRATION_ACTION"
    CHECKPOINT_PERSISTENCE = "CHECKPOINT_PERSISTENCE"
    FINAL_SYNTHESIS = "FINAL_SYNTHESIS"

class EvidenceType(str, Enum):
    # Evidence Unit Subtypes (Semantic)
    DATABASE_RECORD = "DATABASE_RECORD"
    MCP_TOOL_RESULT = "MCP_TOOL_RESULT"
    POLICY_RULE = "POLICY_RULE"
    INTERMEDIATE_CLAIM = "INTERMEDIATE_CLAIM"
    RISK_COMPUTATION_PROOF = "RISK_COMPUTATION_PROOF"
    HISTORICAL_SIMILAR_CASE = "HISTORICAL_SIMILAR_CASE"

class ExecutionUnit(BaseModel):
    unit_id: str = Field(default_factory=lambda: f"exec_{uuid.uuid4().hex[:8]}")
    step_number: int
    agent_id: str
    unit_type: UnitType
    action_name: str
    input_payload: Dict[str, Any] = Field(default_factory=dict)
    output_payload: Optional[Dict[str, Any]] = None
    execution_time_ms: float = 0.0
    status: str = "SUCCESS"  # SUCCESS, FAILED, TIMED_OUT, RETRIED
    error_message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    evidence_ids: List[str] = Field(default_factory=list)  # Links to supporting evidence units

class EvidenceUnit(BaseModel):
    evidence_id: str = Field(default_factory=lambda: f"evid_{uuid.uuid4().hex[:8]}")
    evidence_type: EvidenceType
    source_agent_or_tool: str
    semantic_content: str
    raw_data: Dict[str, Any] = Field(default_factory=dict)
    confidence_score: float = 1.0
    is_contradicted: bool = False
    embedding_vector: Optional[List[float]] = None  # for pgvector indexing
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class TokenAccounting(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    tokens_pruned_by_agent_diet: int = 0

class RunTrace(BaseModel):
    run_id: str = Field(default_factory=lambda: f"run_{uuid.uuid4().hex[:10]}")
    task_prompt: str
    orchestration_topology: str  # "PARALLEL_SUPERVISOR", "SEQUENTIAL_PIPELINE", "SINGLE_AGENT"
    status: str = "RUNNING"      # RUNNING, COMPLETED, FAILED, DEGRADED
    start_time: datetime = Field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    total_duration_ms: float = 0.0
    
    # Fused Audit & Debug Units
    execution_units: List[ExecutionUnit] = Field(default_factory=list)
    evidence_units: List[EvidenceUnit] = Field(default_factory=list)
    
    # Financial & Resource Accounting (O3)
    agent_token_accounting: Dict[str, TokenAccounting] = Field(default_factory=dict)
    total_token_accounting: TokenAccounting = Field(default_factory=TokenAccounting)
    
    # Resilience Tracking (O1)
    retry_count: int = 0
    degraded_agents: List[str] = Field(default_factory=list)
    resumed_from_checkpoint: bool = False
