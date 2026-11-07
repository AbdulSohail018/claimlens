SELECT 'quality' AS mart, measure AS item, rate FROM mart_quality WHERE rate NOT BETWEEN 0 AND 1
UNION ALL
SELECT 'pharmacy', CAST(year AS VARCHAR), generic_dispensing_rate FROM mart_pharmacy
WHERE generic_dispensing_rate NOT BETWEEN 0 AND 1
UNION ALL
SELECT 'concentration', CAST(year AS VARCHAR), max(cumulative_share_of_spend) FROM mart_cost_concentration
GROUP BY year HAVING abs(max(cumulative_share_of_spend) - 1) > 1e-6
