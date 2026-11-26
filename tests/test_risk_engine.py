"""
Tests for the Deterministic Supply Chain Risk Engine.
Verifies zero-LLM reproducibility, exact mathematical bounds, and thresholding.
"""
import pytest
from src.risk_engine.metrics import (
    calculate_stockout_risk,
    calculate_supplier_risk,
    calculate_logistics_risk,
    evaluate_composite_risk
)
from src.risk_engine.scorer import SupplyChainRiskScorer
from src.models.domain import RiskLevel

def test_stockout_risk_exhausted_inventory():
    score, meta = calculate_stockout_risk(
        current_stock=0,
        daily_burn_rate=100.0,
        lead_time_days=10,
        safety_stock=500
    )
    assert score == 1.0
    assert meta["current_stock"] == 0

def test_stockout_risk_healthy_coverage():
    score, meta = calculate_stockout_risk(
        current_stock=10000,
        daily_burn_rate=50.0,
        lead_time_days=14,
        safety_stock=500
    )
    # Healthy buffer should be low risk
    assert score < 0.25
    assert meta["days_of_inventory"] == 200.0

def test_supplier_risk_single_source_and_subpar_delivery():
    score, meta = calculate_supplier_risk(
        historical_on_time_delivery_rate=0.80,
        historical_defect_rate=0.03,
        geopolitical_risk_score=0.40,
        is_single_source=True
    )
    # High risk vendor
    assert score > 0.30
    assert meta["is_single_source"] is True

def test_composite_risk_exact_reproducibility():
    s_stock = 0.85
    s_sup = 0.40
    s_log = 0.50
    score, level, proof = evaluate_composite_risk(
        stockout_score=s_stock,
        supplier_score=s_sup,
        logistics_score=s_log,
        weights=(0.35, 0.35, 0.30)
    )
    expected = round((0.35 * 0.85) + (0.35 * 0.40) + (0.30 * 0.50), 4)
    assert score == expected
    assert level in [RiskLevel.HIGH, RiskLevel.MODERATE]
    assert f"{expected:.4f}" in proof

def test_scorer_service_on_catalog_item():
    assessment = SupplyChainRiskScorer.evaluate_sku_context("MCU-9021")
    assert assessment.composite_risk_score >= 0.0
    assert assessment.composite_risk_score <= 1.0
    assert assessment.audit_formula.startswith("CompositeRisk =")
    assert len(assessment.risk_factors) == 3
