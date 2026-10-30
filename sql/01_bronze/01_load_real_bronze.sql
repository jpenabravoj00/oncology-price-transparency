-- =============================================================================
-- BRONZE LAYER: Real Federal & Hospital Datasets
-- =============================================================================
-- Ingests verified raw CSV files from CMS.gov and Florida hospitals directly
-- into staging tables with zero alterations to preserve raw source lineage.
-- =============================================================================

-- 1. Official CMS Medicare Part B Payment Limits (From CMS.gov)
CREATE OR REPLACE TABLE bronze_cms_asp AS 
SELECT * 
FROM read_csv('data/raw/cms_part_b_asp_pricing.csv', auto_detect = true);

-- 2. Real Moffitt Cancer Center Streamed MRF (From eforms.moffitt.org)
CREATE OR REPLACE TABLE bronze_moffitt_mrf AS 
SELECT * 
FROM read_csv('data/raw/real_moffitt_oncology_mrf.csv', auto_detect = true);

-- 3. Real Baptist Health South Florida Streamed MRF (From baptisthealth.net)
CREATE OR REPLACE TABLE bronze_baptist_mrf AS 
SELECT * 
FROM read_csv('data/raw/real_baptist_oncology_mrf.csv', auto_detect = true);

-- 4. Real HCA Florida Memorial Hospital Streamed MRF (From Azure Blob)
CREATE OR REPLACE TABLE bronze_hca_mrf AS 
SELECT * 
FROM read_csv('data/raw/real_hca_oncology_mrf.csv', auto_detect = true);
