-- =============================================================================
-- SILVER LAYER: Cleaned & Harmonized Healthcare Tables
-- =============================================================================
-- Purpose: 
--   1. Clean data types, standardize string formatting (TRIM, UPPER).
--   2. Harmonize different hospital schemas (Baptist, Moffitt, HCA) into
--      one uniform relational table using column aliasing (AS) and UNION ALL.
--   3. Filter out invalid/empty pricing records (WHERE rate > 0).
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. SILVER CMS MEDICARE PART B ASP BENCHMARKS
-- -----------------------------------------------------------------------------
CREATE OR REPLACE TABLE silver_cms_asp AS 
SELECT 
    TRIM(hcpcs_code) AS hcpcs_code,
    TRIM(brand_name) AS brand_name,
    TRIM(generic_name) AS generic_name,
    TRIM(billing_unit) AS billing_unit,
    CAST(dosage_mg AS DOUBLE) AS dosage_mg,
    CAST(asp_payment_limit AS DOUBLE) AS asp_payment_limit
FROM bronze_cms_asp
WHERE asp_payment_limit > 0;

-- -----------------------------------------------------------------------------
-- 2. DIMENSION: PAYER-PLAN REGULATORY CROSSWALK
-- -----------------------------------------------------------------------------
CREATE OR REPLACE TABLE dim_payer_plan_crosswalk AS 
SELECT * FROM read_csv_auto('data/processed/dim_payer_plan_crosswalk.csv');

-- -----------------------------------------------------------------------------
-- 3. SILVER HOSPITAL NEGOTIATED RATES (HARMONIZED & ENRICHED)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE TABLE silver_hospital_rates AS 
WITH raw_harmonized_rates AS (
    -- A. BAPTIST HEALTH SOUTH FLORIDA
    SELECT 
        'Baptist Health South Florida' AS hospital_name,
        'Non-Profit Community' AS ownership_type,
        TRIM("code|1") AS hcpcs_code,
        TRIM(description) AS drug_description,
        UPPER(TRIM(payer_name)) AS payer_name,
        TRIM(plan_name) AS plan_name,
        TRY_CAST("standard_charge|gross" AS DOUBLE) AS gross_charge,
        TRY_CAST("standard_charge|discounted_cash" AS DOUBLE) AS cash_discount_rate,
        TRY_CAST("standard_charge|negotiated_dollar" AS DOUBLE) AS negotiated_rate
    FROM bronze_baptist_mrf
    WHERE "standard_charge|negotiated_dollar" IS NOT NULL 
      AND TRY_CAST("standard_charge|negotiated_dollar" AS DOUBLE) > 0

    UNION ALL

    -- B. HCA FLORIDA MEMORIAL HOSPITAL
    SELECT 
        'HCA Florida Memorial Hospital' AS hospital_name,
        'For-Profit' AS ownership_type,
        TRIM(code) AS hcpcs_code,
        TRIM(description) AS drug_description,
        UPPER(TRIM(payer_name)) AS payer_name,
        TRIM(plan_name) AS plan_name,
        TRY_CAST(gross_charge AS DOUBLE) AS gross_charge,
        TRY_CAST(discounted_cash AS DOUBLE) AS cash_discount_rate,
        TRY_CAST(negotiated_rate AS DOUBLE) AS negotiated_rate
    FROM bronze_hca_mrf
    WHERE negotiated_rate IS NOT NULL 
      AND TRY_CAST(negotiated_rate AS DOUBLE) > 0

    UNION ALL

    -- C. MOFFITT CANCER CENTER (Harmonized Outpatient Facility Roster)
    SELECT 
        hospital_name,
        ownership_type,
        hcpcs_code,
        drug_description,
        payer_name,
        plan_name,
        gross_charge,
        cash_discount_rate,
        negotiated_rate
    FROM silver_moffitt_clean
)
SELECT 
    r.hospital_name,
    r.ownership_type,
    r.hcpcs_code,
    r.drug_description,
    r.payer_name,
    r.plan_name,
    r.gross_charge,
    r.cash_discount_rate,
    r.negotiated_rate,
    
    -- Standardized Crosswalk Dimensions & Benchmark Inclusion Flags
    c.standardized_payer_name,
    c.standardized_market_segment,
    c.service_line_scope,
    c.reimbursement_methodology,
    c.carve_out_type,
    c.network_status,
    c.is_in_network,
    c.include_in_commercial_benchmark,
    c.include_in_general_commercial_benchmark,
    c.include_in_transplant_carveout_benchmark,
    c.include_in_ma_benchmark,
    c.contract_cluster_id,
    c.data_quality_status
FROM raw_harmonized_rates r
LEFT JOIN dim_payer_plan_crosswalk c
    ON r.hospital_name = c.hospital_name
   AND r.payer_name = c.raw_payer_name
   AND r.plan_name = c.raw_plan_name;

