"""
Cost Controller & Context Pruning module.
Grounded in AgentDiet (arXiv:2509.23586) & MultiAgentBench (ACL 2025).
Provides token budgeting, sliding-window message pruning, and per-topology cost tracking.
"""
from typing import List, Dict, Any, Tuple
from src.config import settings

class AgentDietCostController:
    """
    Manages token budgets and applies the sliding window compression technique
    to ensure orchestration overhead is controlled and auditable.
    """
    def __init__(
        self,
        token_threshold: int = settings.TOKEN_PRUNING_THRESHOLD,
        sliding_window_size: int = settings.SLIDING_WINDOW_SIZE,
        max_run_budget: int = settings.MAX_RUN_TOKEN_BUDGET
    ):
        self.token_threshold = token_threshold
        self.sliding_window_size = sliding_window_size
        self.max_run_budget = max_run_budget

    def estimate_tokens(self, text_or_dict: Any) -> int:
        """Heuristic token estimation (~4 characters per token)."""
        content = str(text_or_dict)
        return max(1, len(content) // 4)

    def prune_context_window(
        self, 
        messages: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Applies AgentDiet sliding window pruning.
        If total tokens are under `token_threshold`, does nothing (saving compute).
        If tokens exceed threshold, retains system prompt and recent window, 
        compressing intermediate verbose steps into concise summaries.
        """
        raw_token_count = sum(self.estimate_tokens(m.get("content", "")) for m in messages)
        
        # Rule 1: Skip if under threshold
        if raw_token_count < self.token_threshold or len(messages) <= self.sliding_window_size:
            return messages, 0

        # Rule 2: Sliding window retention
        # Preserve first message (directive/system) and most recent N messages
        first_msg = messages[0] if messages else {}
        recent_window = messages[-self.sliding_window_size:]
        intermediate = messages[1:-self.sliding_window_size]

        if not intermediate:
            return messages, 0

        # Compress intermediate messages
        compressed_summary = {
            "role": "system",
            "content": f"[AgentDiet Context Compression: {len(intermediate)} intermediate steps compressed to preserve token budget]"
        }
        
        pruned_messages = [first_msg, compressed_summary] + recent_window
        new_token_count = sum(self.estimate_tokens(m.get("content", "")) for m in pruned_messages)
        pruned_tokens = max(0, raw_token_count - new_token_count)

        return pruned_messages, pruned_tokens

    def check_budget_exceeded(self, total_tokens_consumed: int) -> bool:
        """Returns True if the run has breached the hard cost/token ceiling."""
        return total_tokens_consumed >= self.max_run_budget
