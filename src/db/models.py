"""
SQLAlchemy ORM models for Relational Storage and Fused Audit/Debug Tracing.
Compatible with PostgreSQL (with pgvector) and SQLite (with JSON storage fallback).
"""
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Boolean,
    DateTime,
    Text,
    JSON,
    ForeignKey,
    create_engine,
)
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime
import uuid

Base = declarative_base()

class DBInventoryItem(Base):
    __tablename__ = "inventory_items"
    
    sku = Column(String(50), primary_key=True)
    name = Column(String(150), nullable=False)
    category = Column(String(50), nullable=False)
    current_stock = Column(Integer, nullable=False)
    safety_stock = Column(Integer, nullable=False)
    reorder_point = Column(Integer, nullable=False)
    daily_burn_rate = Column(Float, nullable=False)
    unit_cost = Column(Float, nullable=False)
    warehouse_location = Column(String(100), nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class DBSupplierProfile(Base):
    __tablename__ = "supplier_profiles"
    
    supplier_id = Column(String(50), primary_key=True)
    name = Column(String(150), nullable=False)
    country = Column(String(50), nullable=False)
    skus_provided = Column(JSON, default=list)
    lead_time_days = Column(Integer, nullable=False)
    min_order_quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    historical_on_time_delivery_rate = Column(Float, default=0.95)
    historical_defect_rate = Column(Float, default=0.01)
    geopolitical_risk_score = Column(Float, default=0.1)
    is_single_source = Column(Boolean, default=False)

class DBLogisticsRoute(Base):
    __tablename__ = "logistics_routes"
    
    route_id = Column(String(50), primary_key=True)
    origin = Column(String(100), nullable=False)
    destination = Column(String(100), nullable=False)
    carrier_name = Column(String(100), nullable=False)
    transport_mode = Column(String(20), nullable=False)
    standard_transit_days = Column(Integer, nullable=False)
    expedited_transit_days = Column(Integer, nullable=False)
    standard_cost_per_kg = Column(Float, nullable=False)
    expedited_cost_per_kg = Column(Float, nullable=False)
    current_delay_days = Column(Integer, default=0)
    port_congestion_index = Column(Float, default=0.0)
    reliability_score = Column(Float, default=0.95)

# --- Fused Audit & Debug Trace Tables (arXiv:2606.04990) ---

class DBRunTrace(Base):
    __tablename__ = "run_traces"
    
    run_id = Column(String(50), primary_key=True, default=lambda: f"run_{uuid.uuid4().hex[:10]}")
    task_prompt = Column(Text, nullable=False)
    orchestration_topology = Column(String(50), nullable=False)
    status = Column(String(30), default="RUNNING")
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    total_duration_ms = Column(Float, default=0.0)
    
    # Financial & Resource Accounting (O3)
    total_tokens = Column(Integer, default=0)
    estimated_cost_usd = Column(Float, default=0.0)
    tokens_pruned = Column(Integer, default=0)
    agent_token_breakdown = Column(JSON, default=dict)
    
    # Resilience Metrics (O1)
    retry_count = Column(Integer, default=0)
    degraded_agents = Column(JSON, default=list)
    resumed_from_checkpoint = Column(Boolean, default=False)
    
    # Relationships
    execution_units = relationship("DBExecutionUnit", back_populates="run_trace", cascade="all, delete-orphan")
    evidence_units = relationship("DBEvidenceUnit", back_populates="run_trace", cascade="all, delete-orphan")

class DBExecutionUnit(Base):
    __tablename__ = "execution_units"
    
    unit_id = Column(String(50), primary_key=True)
    run_id = Column(String(50), ForeignKey("run_traces.run_id"), nullable=False)
    step_number = Column(Integer, nullable=False)
    agent_id = Column(String(50), nullable=False)
    unit_type = Column(String(50), nullable=False)
    action_name = Column(String(100), nullable=False)
    input_payload = Column(JSON, default=dict)
    output_payload = Column(JSON, nullable=True)
    execution_time_ms = Column(Float, default=0.0)
    status = Column(String(30), default="SUCCESS")
    error_message = Column(Text, nullable=True)
    supporting_evidence_ids = Column(JSON, default=list)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    run_trace = relationship("DBRunTrace", back_populates="execution_units")

class DBEvidenceUnit(Base):
    __tablename__ = "evidence_units"
    
    evidence_id = Column(String(50), primary_key=True)
    run_id = Column(String(50), ForeignKey("run_traces.run_id"), nullable=False)
    evidence_type = Column(String(50), nullable=False)
    source_agent_or_tool = Column(String(100), nullable=False)
    semantic_content = Column(Text, nullable=False)
    raw_data = Column(JSON, default=dict)
    confidence_score = Column(Float, default=1.0)
    is_contradicted = Column(Boolean, default=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    run_trace = relationship("DBRunTrace", back_populates="evidence_units")
