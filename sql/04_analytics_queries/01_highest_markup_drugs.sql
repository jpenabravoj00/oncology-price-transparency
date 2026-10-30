-- =============================================================================
-- Query 1: Which oncology biologics have the highest median commercial markups?
-- =============================================================================
-- Purpose:
--   Rank oncology drugs by their median negotiated commercial markup relative
--   to Medicare Part B ASP acquisition benchmarks across all hospital contracts.
-- =============================================================================

SELECT 
    hcpcs_code,
    brand_name,
    COUNT(*) AS total_contracts_analyzed,
    ROUND(AVG(commercial_markup_ratio), 2) AS avg_markup_ratio,
    ROUND(MEDIAN(commercial_markup_ratio), 2) AS median_markup_ratio
FROM gold_oncology_markups
WHERE commercial_markup_ratio BETWEEN 1.0 AND 20.0  -- Filters out bundled case rates / unit errors
GROUP BY hcpcs_code, brand_name
ORDER BY median_markup_ratio DESC;
