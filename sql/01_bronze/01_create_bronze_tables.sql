-- =============================================================================
-- BRONZE LAYER: Raw Staging Tables
-- =============================================================================
-- Pattern: Create Table As Select (CTAS)
-- Purpose: Ingest raw CSV data files into the database with zero modifications,
--          preserving the exact source data for auditability and lineage.
-- =============================================================================

-- 1. Raw CMS Medicare Part B Average Sales Price (ASP) Benchmark
CREATE OR REPLACE TABLE bronze_cms_asp AS 
SELECT * 
FROM read_csv('data/raw/cms_part_b_asp_pricing.csv', auto_detect = true);

-- 2. Raw Florida Hospitals Directory & System Registry
CREATE OR REPLACE TABLE bronze_florida_hospitals AS 
SELECT * 
FROM read_csv('data/raw/florida_hospitals.csv', auto_detect = true);

-- 3. Raw Florida Hospital Machine-Readable Pricing (MRF)
CREATE OR REPLACE TABLE bronze_hospital_charges AS 
SELECT * 
FROM read_csv('data/raw/florida_hospital_charges_mrf.csv', auto_detect = true);
