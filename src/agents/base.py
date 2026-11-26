"""
Base Agent wrapper providing retry logic with backoff, fault isolation (O1),
and automatic registration with the Fused Trace Collector (O2).
"""
import time
from typing import Dict, Any, Optional, List
from src.models.state import SubAgentDirective, SubAgentOutput
from src.models.trace import UnitType
from src.tracing.fused_logger import FusedTraceLogger
from src.config import settings

class BaseSupplyChainAgent:
    def __init__(self, agent_id: str, role_description: str):
        self.agent_id = agent_id
        self.role_description = role_description

    def execute_with_resilience(
        self,
        directive: SubAgentDirective,
        tracer: FusedTraceLogger
    ) -> SubAgentOutput:
        """
        Executes domain logic with retry policy, exponential backoff, and graceful fallback.
        """
        retries = 0
        backoff = settings.RETRY_BACKOFF_BASE_SECONDS
        start_time = time.time()
        
        # Log dispatch
        tracer.log_execution_unit(
            agent_id=self.agent_id,
            unit_type=UnitType.REASONING_STEP,
            action_name=f"{self.agent_id}_received_directive",
            input_payload=directive.model_dump()
        )

        while retries <= settings.MAX_SUBAGENT_RETRIES:
            try:
                # Subclass implementation
                output = self._run_agent_logic(directive, tracer)
                elapsed_ms = (time.time() - start_time) * 1000.0
                output.execution_time_ms = round(elapsed_ms, 2)
                
                tracer.log_execution_unit(
                    agent_id=self.agent_id,
                    unit_type=UnitType.TOOL_OUTPUT,
                    action_name=f"{self.agent_id}_completed_task",
                    input_payload={"directive": directive.task_description},
                    output_payload=output.model_dump(),
                    execution_time_ms=output.execution_time_ms,
                    status="SUCCESS",
                    evidence_ids=output.evidence_ids
                )
                return output

            except Exception as e:
                retries += 1
                tracer.retry_count += 1
                tracer.log_execution_unit(
                    agent_id=self.agent_id,
                    unit_type=UnitType.REASONING_STEP,
                    action_name=f"{self.agent_id}_retry_attempt_{retries}",
                    input_payload={"error": str(e)},
                    status="RETRIED",
                    error_message=str(e)
                )
                if retries > settings.MAX_SUBAGENT_RETRIES:
                    if settings.ALLOW_PARTIAL_DEGRADATION:
                        # Graceful partial degradation (O1)
                        tracer.degraded_agents.append(self.agent_id)
                        elapsed_ms = (time.time() - start_time) * 1000.0
                        return SubAgentOutput(
                            agent_id=self.agent_id,
                            status="DEGRADED",
                            summary=f"Degraded fallback: Agent {self.agent_id} encountered repeated errors: {str(e)}",
                            confidence=0.20,
                            execution_time_ms=round(elapsed_ms, 2)
                        )
                    else:
                        raise e
                time.sleep(backoff)
                backoff *= 1.5

        return SubAgentOutput(agent_id=self.agent_id, status="FAILED", summary="Max retries reached")

    def _run_agent_logic(self, directive: SubAgentDirective, tracer: FusedTraceLogger) -> SubAgentOutput:
        raise NotImplementedError("Subclasses must implement _run_agent_logic.")
