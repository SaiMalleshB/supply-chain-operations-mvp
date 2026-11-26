"""
Domain models for the Supply Chain Multi-Agent System.
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime

class RiskLevel(str, Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class PriorityLevel(str, Enum):
    P1_URGENT = "P1_URGENT"
    P2_HIGH = "P2_HIGH"
    P3_MEDIUM = "P3_MEDIUM"
    P4_LOW = "P4_LOW"

class InventoryItem(BaseModel):
    sku: str
    name: str
    category: str
    current_stock: int
    safety_stock: int
    reorder_point: int
    daily_burn_rate: float
    unit_cost: float
    holding_cost_annual_rate: float = 0.20
    warehouse_location: str
    last_updated: datetime = Field(default_factory=datetime.utcnow)

class DemandSignal(BaseModel):
    sku: str
    forecasted_units_next_30d: int
    confidence_interval_low: int
    confidence_interval_high: int
    historical_avg_daily_demand: float
    demand_trend_pct: float  # e.g., +25.5% sudden surge
    signal_sources: List[str] = Field(default_factory=list)
    recorded_at: datetime = Field(default_factory=datetime.utcnow)

class SupplierProfile(BaseModel):
    supplier_id: str
    name: str
    country: str
    skus_provided: List[str]
    lead_time_days: int
    min_order_quantity: int
    unit_price: float
    historical_on_time_delivery_rate: float  # e.g., 0.94 (94%)
    historical_defect_rate: float            # e.g., 0.015 (1.5%)
    geopolitical_risk_score: float           # 0.0 to 1.0 (deterministic)
    is_single_source: bool = False

class LogisticsRoute(BaseModel):
    route_id: str
    origin: str
    destination: str
    carrier_name: str
    transport_mode: str  # "AIR", "OCEAN", "ROAD", "RAIL"
    standard_transit_days: int
    expedited_transit_days: int
    standard_cost_per_kg: float
    expedited_cost_per_kg: float
    current_delay_days: int = 0
    port_congestion_index: float = 0.0  # 0.0 to 1.0
    reliability_score: float = 0.95

class SupplyChainIncident(BaseModel):
    incident_id: str
    title: str
    description: str
    affected_skus: List[str]
    affected_regions: List[str]
    severity: RiskLevel
    reported_at: datetime = Field(default_factory=datetime.utcnow)
