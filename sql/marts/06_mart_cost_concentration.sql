-- How concentrated is spending? Cumulative share of total cost held by the costliest members (Lorenz curve).
WITH ranked AS (
    SELECT year, total_paid,
           row_number() OVER (PARTITION BY year ORDER BY total_paid DESC) AS rnk,
           count(*) OVER (PARTITION BY year) AS n,
           sum(total_paid) OVER (PARTITION BY year) AS year_total
    FROM mart_member_year
),
pct AS (
    SELECT year, ceil(100.0 * rnk / n) AS top_pct, sum(total_paid) AS paid, any_value(year_total) AS year_total
    FROM ranked WHERE year_total > 0 GROUP BY ALL
)
SELECT year, CAST(top_pct AS INT) AS top_pct_of_members,
       sum(paid) OVER (PARTITION BY year ORDER BY top_pct) / year_total AS cumulative_share_of_spend
FROM pct
ORDER BY year, top_pct
