"""
Deterministic Risk Scoring Service.
Non-LLM, reproducible, audited risk engine.
"""
from typing import List, Dict, Any, Optional
from src.risk_engine.metrics import (
    calculate_stockout_risk,
    calculate_supplier_risk,
    calculate_logistics_risk,
    evaluate_composite_risk
)
from src.models.state import RiskAssessment
from src.models.domain import RiskLevel
from src.db.session import SessionLocal
from src.db.models import DBInventoryItem, DBSupplierProfile, DBLogisticsRoute

class SupplyChainRiskScorer:
    """
    Evaluates end-to-end supply chain risk using exact mathematical rules.
    Guaranteed zero hallucination, 100% reproducible.
    """
    
    @classmethod
    def evaluate_sku_context(
        cls,
        sku: str,
        demanded_quantity: int = 0,
        proposed_supplier_id: Optional[str] = None,
        proposed_transport_mode: Optional[str] = None,
        custom_delay_days: int = 0
    ) -> RiskAssessment:
        db = SessionLocal()
        try:
            item = db.query(DBInventoryItem).filter(DBInventoryItem.sku == sku).first()
            if not item:
                return RiskAssessment(
                    composite_risk_score=1.0,
                    risk_level=RiskLevel.CRITICAL.value,
                    stockout_risk_score=1.0,
                    supplier_risk_score=0.5,
                    logistics_risk_score=0.5,
                    risk_factors=[f"SKU {sku} not found in inventory catalog"],
                    audit_formula="SKU_NOT_FOUND_DEFAULT_CRITICAL"
                )
                
            # Find preferred or specified supplier
            supplier = None
            if proposed_supplier_id:
                supplier = db.query(DBSupplierProfile).filter(DBSupplierProfile.supplier_id == proposed_supplier_id).first()
            if not supplier:
                # Find any supplier providing this SKU
                all_sups = db.query(DBSupplierProfile).all()
                for s in all_sups:
                    if sku in s.skus_provided:
                        supplier = s
                        break
                        
            # Find matching route
            route = None
            if supplier:
                if supplier.country == "Taiwan":
                    route = db.query(DBLogisticsRoute).filter(
                        DBLogisticsRoute.transport_mode == (proposed_transport_mode or "OCEAN"),
                        DBLogisticsRoute.origin.like("%Taiwan%")
                    ).first()
                elif supplier.country == "USA":
                    route = db.query(DBLogisticsRoute).filter(DBLogisticsRoute.transport_mode == "ROAD").first()
                elif supplier.country == "South Korea":
                    route = db.query(DBLogisticsRoute).filter(DBLogisticsRoute.origin.like("%Korea%")).first()
                    
            if not route:
                route = db.query(DBLogisticsRoute).first()
                
            # Lead time calculation
            supplier_lead_time = supplier.lead_time_days if supplier else 14
            transit_days = (
                (route.expedited_transit_days if proposed_transport_mode == "AIR" else route.standard_transit_days)
                + (route.current_delay_days + custom_delay_days)
            ) if route else 10
            total_replenish_lead_time = supplier_lead_time + transit_days
            
            # 1. Stockout Risk
            effective_stock = max(0, item.current_stock - demanded_quantity)
            stockout_score, stock_meta = calculate_stockout_risk(
                current_stock=effective_stock,
                daily_burn_rate=item.daily_burn_rate,
                lead_time_days=total_replenish_lead_time,
                safety_stock=item.safety_stock
            )
            
            # 2. Supplier Risk
            if supplier:
                supplier_score, sup_meta = calculate_supplier_risk(
                    historical_on_time_delivery_rate=supplier.historical_on_time_delivery_rate,
                    historical_defect_rate=supplier.historical_defect_rate,
                    geopolitical_risk_score=supplier.geopolitical_risk_score,
                    is_single_source=supplier.is_single_source
                )
            else:
                supplier_score, sup_meta = 0.5, {"rationale": "No verified supplier assigned"}
                
            # 3. Logistics Risk
            if route:
                logistics_score, log_meta = calculate_logistics_risk(
                    current_delay_days=route.current_delay_days + custom_delay_days,
                    standard_transit_days=route.standard_transit_days,
                    port_congestion_index=route.port_congestion_index,
                    reliability_score=route.reliability_score
                )
            else:
                logistics_score, log_meta = 0.5, {"rationale": "No designated route found"}
                
            # 4. Composite Risk & Audit Formula
            composite_score, level, formula_proof = evaluate_composite_risk(
                stockout_score=stockout_score,
                supplier_score=supplier_score,
                logistics_score=logistics_score
            )
            
            factors = []
            factors.append(f"Stockout [{stockout_score}]: {stock_meta['rationale']}")
            factors.append(f"Supplier [{supplier_score}]: {sup_meta['rationale']}")
            factors.append(f"Logistics [{logistics_score}]: {log_meta['rationale']}")
            
            return RiskAssessment(
                composite_risk_score=composite_score,
                risk_level=level.value,
                stockout_risk_score=stockout_score,
                supplier_risk_score=supplier_score,
                logistics_risk_score=logistics_score,
                risk_factors=factors,
                audit_formula=formula_proof
            )
        finally:
            db.close()
