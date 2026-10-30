-- ==============================================================================
-- Query 5: Patient Coinsurance Toxicity & Out-of-Pocket Exposure
-- ==============================================================================
-- Portfolio Project 004: Oncology Price Transparency & Economic Analysis
-- Layer: Gold Analytical Queries
--
-- Business Objective:
-- Quantify the out-of-pocket financial exposure for cancer patients subject to
-- standard 20% commercial coinsurance for blockbuster oncology biologics
-- (Keytruda, Opdivo, Herceptin) across hospital ownership structures.
-- Demonstrates the "hospital lottery" (inter-facility cost disparity) and
-- the "plan lottery" (intra-facility insurance spread).
-- ==============================================================================

SELECT
    brand_name,
    hospital_name,
    ownership_type,
    COUNT(*) AS negotiated_plan_count,
    ROUND(MIN(patient_coinsurance_20pct), 2) AS min_patient_coinsurance,
    ROUND(MEDIAN(patient_coinsurance_20pct), 2) AS median_patient_coinsurance,
    ROUND(MAX(patient_coinsurance_20pct), 2) AS max_patient_coinsurance,
    ROUND(MAX(patient_coinsurance_20pct) - MIN(patient_coinsurance_20pct), 2) AS coinsurance_spread,
    -- Package min, median, max into a single struct for clean reporting / API payloads:
    {'min': ROUND(MIN(patient_coinsurance_20pct), 2),
     'median': ROUND(MEDIAN(patient_coinsurance_20pct), 2),
     'max': ROUND(MAX(patient_coinsurance_20pct), 2)} AS coinsurance_exposure
FROM gold_oncology_markups
WHERE brand_name IN ('Keytruda', 'Opdivo', 'Herceptin')
GROUP BY 
    brand_name,
    hospital_name,
    ownership_type
ORDER BY 
    brand_name,
    median_patient_coinsurance DESC;
