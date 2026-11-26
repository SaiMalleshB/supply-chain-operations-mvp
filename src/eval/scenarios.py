"""
Supply Chain Benchmark Scenarios.
Realistic test cases designed to evaluate reliability, cost, and constraint satisfaction.
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Any

class EvaluationScenario(BaseModel):
    scenario_id: str
    title: str
    description: str
    target_skus: List[str]
    expected_constraints: Dict[str, Any]
    failure_injection: Dict[str, Any] = Field(default_factory=dict)

EVALUATION_SCENARIOS = [
    EvaluationScenario(
        scenario_id="SCENARIO_01_DEMAND_SURGE",
        title="Automotive Microcontroller 40% Demand Surge",
        description="A major Tier-1 automotive customer increases 30-day order demand by 40%. The system must calculate stockout risk, select qualified suppliers with adequate MOQ, and balance freight speed against budget.",
        target_skus=["MCU-9021"],
        expected_constraints={
            "min_units_ordered": 1000,
            "max_lead_time_days": 25,
            "requires_split_air_freight": True
        }
    ),
    EvaluationScenario(
        scenario_id="SCENARIO_02_PORT_CONGESTION",
        title="Pacific Port Congestion & Ocean Lane Bottleneck",
        description="Ocean freight from Taiwan is experiencing 5-day port congestion delays. Standard shipment will breach factory safety thresholds. The system must arbitrate between ocean and air options.",
        target_skus=["MCU-9021"],
        expected_constraints={
            "requires_expedited_contingency": True,
            "max_tolerated_risk": 0.65
        }
    ),
    EvaluationScenario(
        scenario_id="SCENARIO_03_SINGLE_SOURCE_BATTERY",
        title="Single-Source Battery Pack Buffer Depletion",
        description="Energy storage cells (BAT-880) are sole-sourced from South Korea. Stock runway is only 3.6 days. System must trigger urgent reorder while flagging single-source supply chain vulnerability.",
        target_skus=["BAT-880"],
        expected_constraints={
            "min_units_ordered": 100,
            "requires_sole_source_warning": True
        }
    ),
    EvaluationScenario(
        scenario_id="SCENARIO_04_MULTI_SKU_COORDINATION",
        title="Multi-SKU Factory Replenishment Coordination",
        description="Concurrent replenishment across both mechanical actuators (ACT-440) and optical sensors (SENS-102) from European precision suppliers.",
        target_skus=["ACT-440", "SENS-102"],
        expected_constraints={
            "multi_agent_parallel_dispatch": True,
            "min_units_ordered": 150
        }
    )
]
