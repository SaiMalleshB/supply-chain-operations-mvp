"""
Configuration settings for the Enterprise Multi-Agent Orchestration Platform.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

class Settings(BaseSettings):
    # App Settings
    PROJECT_NAME: str = "Enterprise Multi-Agent Supply Chain Platform"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # LLM & API Configuration
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY", "mock-key")
    DEFAULT_MODEL: str = "gpt-4o-mini"
    SUPERVISOR_MODEL: str = "gpt-4o"
    USE_MOCK_LLM_IF_NO_KEY: bool = True  # Allows full testing and evaluation out of the box
    
    # Database Settings
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "postgres")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "supply_chain_db")
    USE_SQLITE_FALLBACK: bool = True
    SQLITE_DB_PATH: str = str(PROJECT_ROOT / "data" / "supply_chain.db")
    
    # Reliability Settings (O1)
    MAX_SUBAGENT_RETRIES: int = 3
    RETRY_BACKOFF_BASE_SECONDS: float = 0.5
    SUBAGENT_TIMEOUT_SECONDS: float = 10.0
    ALLOW_PARTIAL_DEGRADATION: bool = True
    
    # Cost Control Settings (O3 - AgentDiet inspired)
    TOKEN_PRUNING_THRESHOLD: int = 400  # Skip compression if context under this threshold
    SLIDING_WINDOW_SIZE: int = 4        # Number of recent steps retained in active context
    MAX_RUN_TOKEN_BUDGET: int = 15000   # Hard budget cap per run to prevent runaway loops
    COST_PER_1K_INPUT_TOKENS: float = 0.00015   # gpt-4o-mini baseline
    COST_PER_1K_OUTPUT_TOKENS: float = 0.00060
    
    # Traceability Settings (O2 - arXiv:2606.04990)
    FUSED_TRACE_ENABLED: bool = True
    PERSIST_EVIDENCE_VECTORS: bool = True
    
    # Deterministic Risk Scoring Weights
    RISK_WEIGHT_STOCKOUT: float = 0.35
    RISK_WEIGHT_SUPPLIER: float = 0.35
    RISK_WEIGHT_LOGISTICS: float = 0.30

    model_config = SettingsConfigDict(env_file=".env", extra="allow")

settings = Settings()
