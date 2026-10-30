-- =============================================================================
-- GOLD LAYER: Oncology Pricing & Commercial Markup Analytical Mart
-- =============================================================================
-- Architecture: Modular Common Table Expressions (CTEs)
-- Engine: In-Process Columnar DuckDB OLAP
--
-- Business Purpose:
--   Harmonizes commercial hospital rates with statutory CMS Medicare Part B
--   Average Sales Price (ASP) baselines to evaluate:
--   1. Commercial hospital price premiums over federal payment limits
--   2. Hospital chargemaster list-price inflation
--   3. The "Cash Paradox" (instances where cash price is cheaper than insured rate)
--   4. Direct patient 20% coinsurance financial liability
-- =============================================================================

CREATE OR REPLACE TABLE gold_oncology_markups AS 

WITH 
-- -----------------------------------------------------------------------------
-- CTE 1: Cleaned & Validated Hospital Rates
-- Extracts all harmonized hospital contract rates, verifying positive pricing
-- -----------------------------------------------------------------------------
cleaned_hospital_rates AS (
    SELECT 
        hospital_name,
        ownership_type,
        hcpcs_code,
        payer_name,
        plan_name,
        standardized_payer_name,
        standardized_market_segment,
        service_line_scope,
        reimbursement_methodology,
        carve_out_type,
        network_status,
        is_in_network,
        include_in_commercial_benchmark,
        include_in_general_commercial_benchmark,
        include_in_transplant_carveout_benchmark,
        include_in_ma_benchmark,
        contract_cluster_id,
        data_quality_status,
        gross_charge,
        cash_discount_rate,
        negotiated_rate
    FROM silver_hospital_rates
    WHERE negotiated_rate IS NOT NULL 
      AND negotiated_rate > 0
),

-- -----------------------------------------------------------------------------
-- CTE 2: Validated Federal Statutory Benchmarks
-- Ensures 1:1 referential join determinism via window partitioning on HCPCS code
-- -----------------------------------------------------------------------------
validated_asp_benchmarks AS (
    SELECT 
        hcpcs_code,
        brand_name,
        generic_name,
        billing_unit,
        dosage_mg,
        asp_payment_limit,
        ROW_NUMBER() OVER (
            PARTITION BY hcpcs_code 
            ORDER BY asp_payment_limit DESC
        ) AS dedup_rank
    FROM silver_cms_asp
    WHERE asp_payment_limit IS NOT NULL 
      AND asp_payment_limit > 0
),

-- -----------------------------------------------------------------------------
-- CTE 3: Deterministic Contract & Benchmark Integration
-- Joins validated hospital rates to single-record ASP statutory limits
-- -----------------------------------------------------------------------------
joined_contract_universe AS (
    SELECT 
        h.hospital_name,
        h.ownership_type,
        h.hcpcs_code,
        b.brand_name,
        b.generic_name,
        b.billing_unit,
        b.dosage_mg,
        h.payer_name,
        h.plan_name,
        h.standardized_payer_name,
        h.standardized_market_segment,
        h.service_line_scope,
        h.reimbursement_methodology,
        h.carve_out_type,
        h.network_status,
        h.is_in_network,
        h.include_in_commercial_benchmark,
        h.include_in_general_commercial_benchmark,
        h.include_in_transplant_carveout_benchmark,
        h.include_in_ma_benchmark,
        h.contract_cluster_id,
        h.data_quality_status,
        b.asp_payment_limit AS asp_rate,
        h.gross_charge,
        h.cash_discount_rate,
        h.negotiated_rate
    FROM cleaned_hospital_rates h
    INNER JOIN validated_asp_benchmarks b
        ON h.hcpcs_code = b.hcpcs_code
       AND b.dedup_rank = 1
),

-- -----------------------------------------------------------------------------
-- CTE 4: Econometric Modeling & Friction Calculations
-- Derives markup multipliers, cash discount spreads, and coinsurance exposure
-- -----------------------------------------------------------------------------
calculated_economic_metrics AS (
    SELECT 
        hospital_name,
        ownership_type,
        hcpcs_code,
        brand_name,
        generic_name,
        billing_unit,
        dosage_mg,
        payer_name,
        plan_name,
        standardized_payer_name,
        standardized_market_segment,
        service_line_scope,
        reimbursement_methodology,
        carve_out_type,
        network_status,
        is_in_network,
        include_in_commercial_benchmark,
        include_in_general_commercial_benchmark,
        include_in_transplant_carveout_benchmark,
        include_in_ma_benchmark,
        contract_cluster_id,
        data_quality_status,
        
        -- Federal Baseline Acquisition Price (ASP + 6% Statutory Cap)
        ROUND(asp_rate, 2) AS asp_benchmark_rate,
        
        -- Hospital Published Charges
        ROUND(gross_charge, 2) AS hospital_gross_charge,
        ROUND(cash_discount_rate, 2) AS hospital_cash_rate,
        ROUND(negotiated_rate, 2) AS commercial_negotiated_rate,
        
        -- Econometric Multiplier 1: Commercial Markup Ratio over Statutory ASP
        ROUND(negotiated_rate / asp_rate, 2) AS commercial_markup_ratio,
        
        -- Econometric Multiplier 2: Chargemaster Gross Markup Ratio over Statutory ASP
        ROUND(gross_charge / asp_rate, 2) AS chargemaster_markup_ratio,
        
        -- Friction Indicator: Cash vs Commercial Dollar Spread
        -- Positive value indicates Cash price is cheaper than Insured commercial rate!
        ROUND(negotiated_rate - cash_discount_rate, 2) AS cash_discount_advantage,
        
        -- Patient Financial Liability: Standard 20% Coinsurance Exposure per Billing Unit
        ROUND(negotiated_rate * 0.20, 2) AS patient_coinsurance_20pct
        
    FROM joined_contract_universe
)

-- -----------------------------------------------------------------------------
-- Final Production Output
-- -----------------------------------------------------------------------------
SELECT * FROM calculated_economic_metrics;
