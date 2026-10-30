-- =============================================================================
-- Query 3: Which commercial payer secures the best discounts?
-- =============================================================================
-- Purpose:
--   Evaluate payer bargaining power across three market segments:
--     1. Medicare Advantage (Statutory/Government anchored)
--     2. ACA Individual Exchange (Narrow network leverage)
--     3. Commercial Employer Group (Private employer contracts)
-- =============================================================================

SELECT 
    payer_name,
    CASE 
        WHEN plan_name ILIKE '%medicare%' 
          OR plan_name ILIKE '%mcr%' 
          OR plan_name ILIKE '%tricare%' 
          OR plan_name ILIKE '%mc hmo%' THEN '1. Medicare Advantage'
        WHEN plan_name ILIKE '%exchange%' 
          OR plan_name ILIKE '%ex%'      THEN '2. ACA Individual Exchange'
        ELSE '3. Commercial Employer Group'
    END AS market_segment,
    COUNT(*) AS total_contracts,
    ROUND(AVG(commercial_markup_ratio), 2) AS avg_markup_ratio,
    ROUND(MEDIAN(commercial_markup_ratio), 2) AS median_markup_ratio
FROM gold_oncology_markups
WHERE commercial_markup_ratio BETWEEN 1.0 AND 20.0  -- Filters out bundled/anomalous rates
GROUP BY payer_name, market_segment
HAVING COUNT(*) >= 20  -- Focus on payers with significant market presence
ORDER BY market_segment ASC, median_markup_ratio ASC;
