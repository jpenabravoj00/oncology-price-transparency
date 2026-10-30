-- =============================================================================
-- Query 4: The Cash Price Paradox
-- =============================================================================
-- Purpose:
--   Identify contracts and drugs where the hospital's discounted cash price
--   is cheaper than commercial insurance negotiated rates.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- ANGLE 1: Hospital-Level Prevalence of the Paradox
-- -----------------------------------------------------------------------------
SELECT
    hospital_name,
    ownership_type,
    COUNT(*) AS total_contracts,
    COUNT(CASE WHEN cash_discount_advantage > 0 THEN 1 END) AS contracts_where_cash_cheaper,
    ROUND(100.0 * COUNT(CASE WHEN cash_discount_advantage > 0 THEN 1 END) / COUNT(*), 1) AS pct_contracts_cash_cheaper,
    ROUND(MEDIAN(CASE WHEN cash_discount_advantage > 0 THEN cash_discount_advantage END), 2) AS med_cash_savings
FROM gold_oncology_markups
GROUP BY hospital_name, ownership_type
ORDER BY pct_contracts_cash_cheaper DESC;

-- -----------------------------------------------------------------------------
-- ANGLE 2: Drug-Level Cash Advantage Summary (Unique Drugs Ranked by Savings)
-- -----------------------------------------------------------------------------
SELECT 
    hospital_name,
    brand_name,
    COUNT(*) AS total_contracts_with_cash_advantage,
    COUNT(DISTINCT payer_name) AS distinct_payers_paying_more_than_cash,
    ROUND(AVG(hospital_cash_rate), 2) AS avg_cash_price,
    ROUND(AVG(commercial_negotiated_rate), 2) AS avg_insured_price,
    ROUND(MEDIAN(cash_discount_advantage), 2) AS median_cash_savings_per_unit,
    ROUND(MAX(cash_discount_advantage), 2) AS max_cash_savings_per_unit
FROM gold_oncology_markups
WHERE cash_discount_advantage > 0
  AND commercial_markup_ratio BETWEEN 1.0 AND 20.0
GROUP BY hospital_name, brand_name
ORDER BY median_cash_savings_per_unit DESC;
