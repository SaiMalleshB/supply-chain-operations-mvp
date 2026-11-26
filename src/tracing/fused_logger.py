"""
Fused Audit and Debug Trace Collector.
Implements the unified trace artifact architecture inspired by arXiv:2606.04990.
Combines procedural execution units and semantic evidence units into a single queryable artifact.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from src.models.trace import (
    RunTrace,
    ExecutionUnit,
    EvidenceUnit,
    TokenAccounting,
    UnitType,
    EvidenceType,
)
from src.db.session import SessionLocal
from src.db.models import DBRunTrace, DBExecutionUnit, DBEvidenceUnit
from src.config import settings
import uuid

class FusedTraceLogger:
    """
    Singleton-style tracer for tracking a multi-agent orchestration session.
    """
    def __init__(self, run_id: Optional[str] = None, task_prompt: str = "", topology: str = "PARALLEL_SUPERVISOR"):
        self.run_id = run_id or f"run_{uuid.uuid4().hex[:10]}"
        self.task_prompt = task_prompt
        self.topology = topology
        self.start_time = datetime.utcnow()
        self.step_counter = 0
        
        self.execution_units: List[ExecutionUnit] = []
        self.evidence_units: List[EvidenceUnit] = []
        self.agent_token_accounting: Dict[str, TokenAccounting] = {}
        self.total_tokens = TokenAccounting()
        self.retry_count = 0
        self.degraded_agents: List[str] = []
        self.resumed = False

    def log_execution_unit(
        self,
        agent_id: str,
        unit_type: UnitType,
        action_name: str,
        input_payload: Dict[str, Any],
        output_payload: Optional[Dict[str, Any]] = None,
        execution_time_ms: float = 0.0,
        status: str = "SUCCESS",
        error_message: Optional[str] = None,
        evidence_ids: Optional[List[str]] = None
    ) -> ExecutionUnit:
        self.step_counter += 1
        unit = ExecutionUnit(
            unit_id=f"exec_{uuid.uuid4().hex[:8]}",
            step_number=self.step_counter,
            agent_id=agent_id,
            unit_type=unit_type,
            action_name=action_name,
            input_payload=input_payload,
            output_payload=output_payload,
            execution_time_ms=execution_time_ms,
            status=status,
            error_message=error_message,
            evidence_ids=evidence_ids or []
        )
        self.execution_units.append(unit)
        return unit

    def log_evidence_unit(
        self,
        evidence_type: EvidenceType,
        source: str,
        semantic_content: str,
        raw_data: Optional[Dict[str, Any]] = None,
        confidence: float = 1.0
    ) -> EvidenceUnit:
        unit = EvidenceUnit(
            evidence_id=f"evid_{uuid.uuid4().hex[:8]}",
            evidence_type=evidence_type,
            source_agent_or_tool=source,
            semantic_content=semantic_content,
            raw_data=raw_data or {},
            confidence_score=confidence
        )
        self.evidence_units.append(unit)
        return unit

    def record_tokens(self, agent_id: str, prompt_tokens: int, completion_tokens: int, pruned_tokens: int = 0):
        if agent_id not in self.agent_token_accounting:
            self.agent_token_accounting[agent_id] = TokenAccounting()
            
        acc = self.agent_token_accounting[agent_id]
        acc.prompt_tokens += prompt_tokens
        acc.completion_tokens += completion_tokens
        acc.total_tokens += (prompt_tokens + completion_tokens)
        acc.tokens_pruned_by_agent_diet += pruned_tokens
        
        cost = (
            (acc.prompt_tokens / 1000.0 * settings.COST_PER_1K_INPUT_TOKENS) +
            (acc.completion_tokens / 1000.0 * settings.COST_PER_1K_OUTPUT_TOKENS)
        )
        acc.estimated_cost_usd = round(cost, 6)

        # Update global totals
        self.total_tokens.prompt_tokens += prompt_tokens
        self.total_tokens.completion_tokens += completion_tokens
        self.total_tokens.total_tokens += (prompt_tokens + completion_tokens)
        self.total_tokens.tokens_pruned_by_agent_diet += pruned_tokens
        self.total_tokens.estimated_cost_usd = round(
            (self.total_tokens.prompt_tokens / 1000.0 * settings.COST_PER_1K_INPUT_TOKENS) +
            (self.total_tokens.completion_tokens / 1000.0 * settings.COST_PER_1K_OUTPUT_TOKENS),
            6
        )

    def persist_to_database(self, final_status: str = "COMPLETED") -> RunTrace:
        end_time = datetime.utcnow()
        duration_ms = (end_time - self.start_time).total_seconds() * 1000.0

        run_trace = RunTrace(
            run_id=self.run_id,
            task_prompt=self.task_prompt,
            orchestration_topology=self.topology,
            status=final_status,
            start_time=self.start_time,
            end_time=end_time,
            total_duration_ms=round(duration_ms, 2),
            execution_units=self.execution_units,
            evidence_units=self.evidence_units,
            agent_token_accounting=self.agent_token_accounting,
            total_token_accounting=self.total_tokens,
            retry_count=self.retry_count,
            degraded_agents=self.degraded_agents,
            resumed_from_checkpoint=self.resumed
        )

        db = SessionLocal()
        try:
            db_run = DBRunTrace(
                run_id=run_trace.run_id,
                task_prompt=run_trace.task_prompt,
                orchestration_topology=run_trace.orchestration_topology,
                status=run_trace.status,
                start_time=run_trace.start_time,
                end_time=run_trace.end_time,
                total_duration_ms=run_trace.total_duration_ms,
                total_tokens=run_trace.total_token_accounting.total_tokens,
                estimated_cost_usd=run_trace.total_token_accounting.estimated_cost_usd,
                tokens_pruned=run_trace.total_token_accounting.tokens_pruned_by_agent_diet,
                agent_token_breakdown={k: v.model_dump() for k, v in run_trace.agent_token_accounting.items()},
                retry_count=run_trace.retry_count,
                degraded_agents=run_trace.degraded_agents,
                resumed_from_checkpoint=run_trace.resumed_from_checkpoint
            )
            db.merge(db_run)
            
            # Persist execution units
            for eu in run_trace.execution_units:
                db_eu = DBExecutionUnit(
                    unit_id=eu.unit_id,
                    run_id=run_trace.run_id,
                    step_number=eu.step_number,
                    agent_id=eu.agent_id,
                    unit_type=eu.unit_type.value,
                    action_name=eu.action_name,
                    input_payload=eu.input_payload,
                    output_payload=eu.output_payload,
                    execution_time_ms=eu.execution_time_ms,
                    status=eu.status,
                    error_message=eu.error_message,
                    supporting_evidence_ids=eu.evidence_ids,
                    timestamp=eu.timestamp
                )
                db.merge(db_eu)
                
            # Persist evidence units
            for ev in run_trace.evidence_units:
                db_ev = DBEvidenceUnit(
                    evidence_id=ev.evidence_id,
                    run_id=run_trace.run_id,
                    evidence_type=ev.evidence_type.value,
                    source_agent_or_tool=ev.source_agent_or_tool,
                    semantic_content=ev.semantic_content,
                    raw_data=ev.raw_data,
                    confidence_score=ev.confidence_score,
                    is_contradicted=ev.is_contradicted,
                    timestamp=ev.timestamp
                )
                db.merge(db_ev)
                
            db.commit()
        finally:
            db.close()
            
        return run_trace
