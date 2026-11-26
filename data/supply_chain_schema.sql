-- PostgreSQL with pgvector extension initialization schema
CREATE EXTENSION IF NOT EXISTS vector;

-- Inventory Catalog
CREATE TABLE IF NOT EXISTS inventory_items (
    sku VARCHAR(50) PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    category VARCHAR(50) NOT NULL,
    current_stock INTEGER NOT NULL,
    safety_stock INTEGER NOT NULL,
    reorder_point INTEGER NOT NULL,
    daily_burn_rate NUMERIC(10,2) NOT NULL,
    unit_cost NUMERIC(10,2) NOT NULL,
    warehouse_location VARCHAR(100) NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Supplier Profiles
CREATE TABLE IF NOT EXISTS supplier_profiles (
    supplier_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    country VARCHAR(50) NOT NULL,
    skus_provided JSONB DEFAULT '[]'::jsonb,
    lead_time_days INTEGER NOT NULL,
    min_order_quantity INTEGER NOT NULL,
    unit_price NUMERIC(10,2) NOT NULL,
    historical_on_time_delivery_rate NUMERIC(5,4) DEFAULT 0.95,
    historical_defect_rate NUMERIC(5,4) DEFAULT 0.01,
    geopolitical_risk_score NUMERIC(5,4) DEFAULT 0.1,
    is_single_source BOOLEAN DEFAULT FALSE
);

-- Logistics Routes
CREATE TABLE IF NOT EXISTS logistics_routes (
    route_id VARCHAR(50) PRIMARY KEY,
    origin VARCHAR(100) NOT NULL,
    destination VARCHAR(100) NOT NULL,
    carrier_name VARCHAR(100) NOT NULL,
    transport_mode VARCHAR(20) NOT NULL,
    standard_transit_days INTEGER NOT NULL,
    expedited_transit_days INTEGER NOT NULL,
    standard_cost_per_kg NUMERIC(10,2) NOT NULL,
    expedited_cost_per_kg NUMERIC(10,2) NOT NULL,
    current_delay_days INTEGER DEFAULT 0,
    port_congestion_index NUMERIC(5,4) DEFAULT 0.0,
    reliability_score NUMERIC(5,4) DEFAULT 0.95
);

-- Fused Audit and Debug Trace Tables (arXiv:2606.04990)
CREATE TABLE IF NOT EXISTS run_traces (
    run_id VARCHAR(50) PRIMARY KEY,
    task_prompt TEXT NOT NULL,
    orchestration_topology VARCHAR(50) NOT NULL,
    status VARCHAR(30) DEFAULT 'RUNNING',
    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP,
    total_duration_ms NUMERIC(10,2) DEFAULT 0.0,
    total_tokens INTEGER DEFAULT 0,
    estimated_cost_usd NUMERIC(10,6) DEFAULT 0.0,
    tokens_pruned INTEGER DEFAULT 0,
    agent_token_breakdown JSONB DEFAULT '{}'::jsonb,
    retry_count INTEGER DEFAULT 0,
    degraded_agents JSONB DEFAULT '[]'::jsonb,
    resumed_from_checkpoint BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS execution_units (
    unit_id VARCHAR(50) PRIMARY KEY,
    run_id VARCHAR(50) REFERENCES run_traces(run_id) ON DELETE CASCADE,
    step_number INTEGER NOT NULL,
    agent_id VARCHAR(50) NOT NULL,
    unit_type VARCHAR(50) NOT NULL,
    action_name VARCHAR(100) NOT NULL,
    input_payload JSONB DEFAULT '{}'::jsonb,
    output_payload JSONB,
    execution_time_ms NUMERIC(10,2) DEFAULT 0.0,
    status VARCHAR(30) DEFAULT 'SUCCESS',
    error_message TEXT,
    supporting_evidence_ids JSONB DEFAULT '[]'::jsonb,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS evidence_units (
    evidence_id VARCHAR(50) PRIMARY KEY,
    run_id VARCHAR(50) REFERENCES run_traces(run_id) ON DELETE CASCADE,
    evidence_type VARCHAR(50) NOT NULL,
    source_agent_or_tool VARCHAR(100) NOT NULL,
    semantic_content TEXT NOT NULL,
    raw_data JSONB DEFAULT '{}'::jsonb,
    confidence_score NUMERIC(5,4) DEFAULT 1.0,
    is_contradicted BOOLEAN DEFAULT FALSE,
    embedding_vector vector(1536), -- semantic pgvector index
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
