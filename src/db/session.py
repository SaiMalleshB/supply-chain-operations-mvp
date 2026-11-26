"""
Database connection, session management, and schema initialization.
"""
import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from src.config import settings
from src.db.models import Base, DBInventoryItem, DBSupplierProfile, DBLogisticsRoute

# Ensure data directory exists
sqlite_path = Path(settings.SQLITE_DB_PATH).expanduser()
if not sqlite_path.is_absolute():
    sqlite_path = Path(__file__).resolve().parents[2] / sqlite_path
sqlite_path.parent.mkdir(parents=True, exist_ok=True)

if settings.USE_SQLITE_FALLBACK:
    DATABASE_URL = f"sqlite:///{sqlite_path.as_posix()}"
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    DATABASE_URL = f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Session:
    """Yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initializes tables and seeds initial supply chain records if empty."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(DBInventoryItem).count() == 0:
            seed_data(db)
    finally:
        db.close()

def seed_data(db: Session):
    """Populates realistic baseline enterprise supply chain entities."""
    # 1. Inventory Items
    items = [
        DBInventoryItem(
            sku="MCU-9021",
            name="Automotive Grade Microcontroller 32-bit",
            category="Semiconductors",
            current_stock=1200,
            safety_stock=2500,
            reorder_point=3000,
            daily_burn_rate=140.0,
            unit_cost=18.50,
            warehouse_location="WH-East-NewJersey"
        ),
        DBInventoryItem(
            sku="ACT-440",
            name="Precision Heavy Industrial Actuator",
            category="Mechanical",
            current_stock=450,
            safety_stock=300,
            reorder_point=400,
            daily_burn_rate=15.0,
            unit_cost=320.00,
            warehouse_location="WH-Midwest-Chicago"
        ),
        DBInventoryItem(
            sku="BAT-880",
            name="High-Density LiFePO4 Cell Pack 48V",
            category="Energy",
            current_stock=80,
            safety_stock=200,
            reorder_point=250,
            daily_burn_rate=22.0,
            unit_cost=540.00,
            warehouse_location="WH-West-Reno"
        ),
        DBInventoryItem(
            sku="SENS-102",
            name="Industrial Multi-Spectrum LiDAR Sensor",
            category="Sensors",
            current_stock=850,
            safety_stock=400,
            reorder_point=500,
            daily_burn_rate=28.0,
            unit_cost=115.00,
            warehouse_location="WH-South-Dallas"
        )
    ]
    for item in items:
        db.add(item)
        
    # 2. Supplier Profiles
    suppliers = [
        DBSupplierProfile(
            supplier_id="SUP-SILICON-TW",
            name="Apex Semiconductor Foundry",
            country="Taiwan",
            skus_provided=["MCU-9021"],
            lead_time_days=21,
            min_order_quantity=1000,
            unit_price=17.20,
            historical_on_time_delivery_rate=0.92,
            historical_defect_rate=0.008,
            geopolitical_risk_score=0.45,
            is_single_source=False
        ),
        DBSupplierProfile(
            supplier_id="SUP-SILICON-US",
            name="Domestic Foundry Solutions",
            country="USA",
            skus_provided=["MCU-9021"],
            lead_time_days=7,
            min_order_quantity=500,
            unit_price=24.50,
            historical_on_time_delivery_rate=0.98,
            historical_defect_rate=0.002,
            geopolitical_risk_score=0.05,
            is_single_source=False
        ),
        DBSupplierProfile(
            supplier_id="SUP-BATT-KR",
            name="NexGen Energy Storage Ltd",
            country="South Korea",
            skus_provided=["BAT-880"],
            lead_time_days=18,
            min_order_quantity=100,
            unit_price=510.00,
            historical_on_time_delivery_rate=0.88,
            historical_defect_rate=0.012,
            geopolitical_risk_score=0.25,
            is_single_source=True
        ),
        DBSupplierProfile(
            supplier_id="SUP-MECH-DE",
            name="Vanguard Precision Machining GmbH",
            country="Germany",
            skus_provided=["ACT-440", "SENS-102"],
            lead_time_days=14,
            min_order_quantity=50,
            unit_price=305.00,
            historical_on_time_delivery_rate=0.96,
            historical_defect_rate=0.004,
            geopolitical_risk_score=0.12,
            is_single_source=False
        )
    ]
    for sup in suppliers:
        db.add(sup)
        
    # 3. Logistics Routes
    routes = [
        DBLogisticsRoute(
            route_id="ROUTE-TW-US-OCEAN",
            origin="Taipei, Taiwan",
            destination="Los Angeles, USA",
            carrier_name="Pacific Cargo Lines",
            transport_mode="OCEAN",
            standard_transit_days=18,
            expedited_transit_days=14,
            standard_cost_per_kg=2.80,
            expedited_cost_per_kg=5.20,
            current_delay_days=5,
            port_congestion_index=0.68,
            reliability_score=0.78
        ),
        DBLogisticsRoute(
            route_id="ROUTE-TW-US-AIR",
            origin="Taipei, Taiwan",
            destination="Los Angeles, USA",
            carrier_name="Air Express Logistics",
            transport_mode="AIR",
            standard_transit_days=3,
            expedited_transit_days=1,
            standard_cost_per_kg=14.50,
            expedited_cost_per_kg=28.00,
            current_delay_days=0,
            port_congestion_index=0.10,
            reliability_score=0.96
        ),
        DBLogisticsRoute(
            route_id="ROUTE-US-DOMESTIC-ROAD",
            origin="Austin, USA",
            destination="New Jersey, USA",
            carrier_name="Swift Interstate Freight",
            transport_mode="ROAD",
            standard_transit_days=4,
            expedited_transit_days=2,
            standard_cost_per_kg=1.85,
            expedited_cost_per_kg=3.60,
            current_delay_days=0,
            port_congestion_index=0.05,
            reliability_score=0.97
        ),
        DBLogisticsRoute(
            route_id="ROUTE-KR-US-OCEAN",
            origin="Busan, South Korea",
            destination="Long Beach, USA",
            carrier_name="HanSeo Shipping Co",
            transport_mode="OCEAN",
            standard_transit_days=16,
            expedited_transit_days=12,
            standard_cost_per_kg=3.10,
            expedited_cost_per_kg=6.00,
            current_delay_days=2,
            port_congestion_index=0.45,
            reliability_score=0.84
        )
    ]
    for route in routes:
        db.add(route)
        
    db.commit()

# Self-initialize on module load
init_db()
