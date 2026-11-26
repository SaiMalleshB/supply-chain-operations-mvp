"""
Mathematical formulas and rule definitions for Deterministic Supply Chain Risk Scoring.
100% Non-LLM, reproducible, and verifiable.
"""
from typing import Tuple, Dict, Any, List
from src.models.domain import RiskLevel
from src.config import settings

def calculate_stockout_risk(
    current_stock: int,
    daily_burn_rate: float,
    lead_time_days: int,
    safety_stock: int
) -> Tuple[float, Dict[str, Any]]:
    """
    Computes stockout risk based on inventory coverage vs. replenishment lead time.
    Returns: (risk_score [0.0-1.0], breakdown_dict)
    """
    burn_rate = max(0.1, daily_burn_rate)
    days_of_inventory = current_stock / burn_rate
    safety_stock_days = safety_stock / burn_rate
    
    # Coverage shortfall: how many days without stock before shipment arrives
    shortfall_days = lead_time_days - days_of_inventory
    
    if current_stock <= 0:
        score = 1.0
        rationale = "Inventory is currently exhausted (0 units available)."
    elif shortfall_days > 0:
        # Imminent stockout before shipment arrives
        normalized_shortfall = min(1.0, shortfall_days / max(1.0, float(lead_time_days)))
        score = min(1.0, 0.60 + (0.40 * normalized_shortfall))
        rationale = f"Replenishment lead time ({lead_time_days}d) exceeds stock runway ({days_of_inventory:.1f}d) by {shortfall_days:.1f} days."
    elif days_of_inventory <= (lead_time_days + safety_stock_days):
        # Penetrating safety stock buffer
        buffer_ratio = (days_of_inventory - lead_time_days) / max(1.0, safety_stock_days)
        score = 0.20 + (0.40 * (1.0 - buffer_ratio))
        rationale = f"Stock runway ({days_of_inventory:.1f}d) encroaches safety stock buffer ({safety_stock_days:.1f}d)."
    else:
        # Healthy buffer
        excess_ratio = min(2.0, days_of_inventory / max(1.0, lead_time_days + safety_stock_days))
        score = max(0.02, 0.20 / excess_ratio)
        rationale = f"Comfortable inventory coverage ({days_of_inventory:.1f}d) above lead time + safety buffer."

    breakdown = {
        "current_stock": current_stock,
        "days_of_inventory": round(days_of_inventory, 2),
        "lead_time_days": lead_time_days,
        "safety_stock_days": round(safety_stock_days, 2),
        "shortfall_days": round(shortfall_days, 2),
        "risk_score": round(score, 4),
        "rationale": rationale
    }
    return round(score, 4), breakdown

def calculate_supplier_risk(
    historical_on_time_delivery_rate: float,
    historical_defect_rate: float,
    geopolitical_risk_score: float,
    is_single_source: bool
) -> Tuple[float, Dict[str, Any]]:
    """
    Computes vendor reliability risk based on delivery history, defect rates, 
    geopolitical stability, and sole-source concentration.
    """
    ot_penalty = max(0.0, 1.0 - historical_on_time_delivery_rate) # e.g. 1.0 - 0.90 = 0.10
    defect_penalty = min(1.0, historical_defect_rate * 10.0)      # e.g. 0.02 defect * 10 = 0.20
    geo_penalty = min(1.0, max(0.0, geopolitical_risk_score))
    single_source_penalty = 0.25 if is_single_source else 0.0
    
    # Weighted sum
    score = (0.35 * ot_penalty) + (0.25 * defect_penalty) + (0.25 * geo_penalty) + (0.15 * (1.0 if is_single_source else 0.0))
    score = min(1.0, max(0.01, score))
    
    rationale_parts = []
    if historical_on_time_delivery_rate < 0.90:
        rationale_parts.append(f"Subpar on-time delivery ({historical_on_time_delivery_rate*100:.1f}%)")
    if is_single_source:
        rationale_parts.append("Single-source vulnerability")
    if geopolitical_risk_score > 0.35:
        rationale_parts.append(f"Elevated geopolitical risk ({geopolitical_risk_score:.2f})")
    if not rationale_parts:
        rationale_parts.append("Supplier exhibits strong track record and low risk indicators")

    breakdown = {
        "on_time_rate": historical_on_time_delivery_rate,
        "defect_rate": historical_defect_rate,
        "geopolitical_risk": geopolitical_risk_score,
        "is_single_source": is_single_source,
        "risk_score": round(score, 4),
        "rationale": "; ".join(rationale_parts)
    }
    return round(score, 4), breakdown

def calculate_logistics_risk(
    current_delay_days: int,
    standard_transit_days: int,
    port_congestion_index: float,
    reliability_score: float
) -> Tuple[float, Dict[str, Any]]:
    """
    Computes freight and fulfillment delay risk.
    """
    delay_ratio = min(1.0, current_delay_days / max(1.0, float(standard_transit_days)))
    congestion = min(1.0, max(0.0, port_congestion_index))
    unreliability = max(0.0, 1.0 - reliability_score)
    
    score = (0.45 * delay_ratio) + (0.35 * congestion) + (0.20 * unreliability)
    score = min(1.0, max(0.01, score))
    
    rationale_parts = []
    if current_delay_days > 0:
        rationale_parts.append(f"Active transit delay of {current_delay_days} days")
    if port_congestion_index > 0.40:
        rationale_parts.append(f"Port congestion index high ({port_congestion_index:.2f})")
    if not rationale_parts:
        rationale_parts.append("Logistics corridor running within standard transit windows")

    breakdown = {
        "delay_days": current_delay_days,
        "standard_transit_days": standard_transit_days,
        "port_congestion": port_congestion_index,
        "carrier_reliability": reliability_score,
        "risk_score": round(score, 4),
        "rationale": "; ".join(rationale_parts)
    }
    return round(score, 4), breakdown

def evaluate_composite_risk(
    stockout_score: float,
    supplier_score: float,
    logistics_score: float,
    weights: Tuple[float, float, float] = (
        settings.RISK_WEIGHT_STOCKOUT, 
        settings.RISK_WEIGHT_SUPPLIER, 
        settings.RISK_WEIGHT_LOGISTICS
    )
) -> Tuple[float, RiskLevel, str]:
    """
    Calculates weighted composite risk and produces an audit-reproducible formula.
    """
    w_stock, w_sup, w_log = weights
    composite = (w_stock * stockout_score) + (w_sup * supplier_score) + (w_log * logistics_score)
    composite = round(min(1.0, max(0.0, composite)), 4)
    
    if composite >= 0.75:
        level = RiskLevel.CRITICAL
    elif composite >= 0.50:
        level = RiskLevel.HIGH
    elif composite >= 0.25:
        level = RiskLevel.MODERATE
    else:
        level = RiskLevel.LOW
        
    formula_proof = (
        f"CompositeRisk = ({w_stock} * {stockout_score}) + ({w_sup} * {supplier_score}) + "
        f"({w_log} * {logistics_score}) = {composite:.4f} -> [{level.value}]"
    )
    return composite, level, formula_proof
