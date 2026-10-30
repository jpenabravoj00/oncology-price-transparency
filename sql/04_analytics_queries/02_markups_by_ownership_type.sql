-- =============================================================================
-- Query 2: How do commercial markups differ across hospital ownership types?
-- =============================================================================
-- Purpose:
--   Compare commercial pricing behavior across For-Profit, Non-Profit Community,
--   and Comprehensive Cancer Center systems relative to Medicare ASP.
-- =============================================================================

SELECT
    hospital_name,
    ownership_type,
    COUNT(*) AS total_contracts_analyzed,
    ROUND(AVG(commercial_markup_ratio), 2) AS avg_markup_ratio,
    ROUND(MEDIAN(commercial_markup_ratio), 2) AS median_markup_ratio
FROM gold_oncology_markups
WHERE commercial_markup_ratio BETWEEN 1.0 AND 20.0  -- Filters out bundled/anomalous rates
GROUP BY hospital_name, ownership_type
ORDER BY median_markup_ratio DESC;
