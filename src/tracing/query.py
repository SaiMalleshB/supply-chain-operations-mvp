"""
Trace Query & Post-Hoc Audit Service.
Enables compliance officers, operators, and developers to query:
- Tool calls by agent and run
- Evidence units and citations
- Arbitration decisions and deterministic risk formulas
"""
from typing import List, Dict, Any, Optional
from src.db.session import SessionLocal
from src.db.models import DBRunTrace, DBExecutionUnit, DBEvidenceUnit

class TraceAuditor:
    """Provides structured audit query capabilities over historical agent runs."""

    @staticmethod
    def get_run_summary(run_id: str) -> Optional[Dict[str, Any]]:
        db = SessionLocal()
        try:
            r = db.query(DBRunTrace).filter(DBRunTrace.run_id == run_id).first()
            if not r:
                return None
            return {
                "run_id": r.run_id,
                "task_prompt": r.task_prompt,
                "topology": r.orchestration_topology,
                "status": r.status,
                "duration_ms": r.total_duration_ms,
                "total_tokens": r.total_tokens,
                "cost_usd": r.estimated_cost_usd,
                "tokens_pruned": r.tokens_pruned,
                "retry_count": r.retry_count,
                "degraded_agents": r.degraded_agents,
                "start_time": str(r.start_time),
                "end_time": str(r.end_time)
            }
        finally:
            db.close()

    @staticmethod
    def query_tool_calls(run_id: str, agent_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Answers: 'Show me every tool call the [Supplier/Demand/Inventory/Logistics] Agent made in run X'.
        """
        db = SessionLocal()
        try:
            q = db.query(DBExecutionUnit).filter(DBExecutionUnit.run_id == run_id)
            if agent_id:
                q = q.filter(DBExecutionUnit.agent_id == agent_id)
            units = q.order_by(DBExecutionUnit.step_number.asc()).all()
            
            results = []
            for u in units:
                results.append({
                    "step": u.step_number,
                    "agent": u.agent_id,
                    "type": u.unit_type,
                    "action": u.action_name,
                    "input": u.input_payload,
                    "output": u.output_payload,
                    "execution_time_ms": u.execution_time_ms,
                    "status": u.status,
                    "timestamp": str(u.timestamp),
                    "evidence_refs": u.supporting_evidence_ids
                })
            return results
        finally:
            db.close()

    @staticmethod
    def query_evidence_for_run(run_id: str) -> List[Dict[str, Any]]:
        """
        Retrieves all semantic Evidence Units (observations, policies, tool outputs) for a run.
        """
        db = SessionLocal()
        try:
            units = db.query(DBEvidenceUnit).filter(DBEvidenceUnit.run_id == run_id).all()
            return [
                {
                    "evidence_id": e.evidence_id,
                    "type": e.evidence_type,
                    "source": e.source_agent_or_tool,
                    "semantic_content": e.semantic_content,
                    "raw_data": e.raw_data,
                    "confidence": e.confidence_score,
                    "timestamp": str(e.timestamp)
                }
                for e in units
            ]
        finally:
            db.close()

    @staticmethod
    def list_all_runs(limit: int = 50) -> List[Dict[str, Any]]:
        db = SessionLocal()
        try:
            runs = db.query(DBRunTrace).order_by(DBRunTrace.start_time.desc()).limit(limit).all()
            return [
                {
                    "run_id": r.run_id,
                    "prompt": r.task_prompt[:80] + ("..." if len(r.task_prompt) > 80 else ""),
                    "topology": r.orchestration_topology,
                    "status": r.status,
                    "tokens": r.total_tokens,
                    "retries": r.retry_count,
                    "degraded_agents": r.degraded_agents or [],
                    "cost": f"${r.estimated_cost_usd:.5f}",
                    "duration_ms": r.total_duration_ms,
                    "timestamp": str(r.start_time)
                }
                for r in runs
            ]
        finally:
            db.close()
