-- Cost rises steeply with the number of chronic conditions.
SELECT year,
       CASE WHEN conditions >= 6 THEN '6+' ELSE CAST(conditions AS VARCHAR) END AS conditions,
       count(*) AS members,
       sum(total_paid) / nullif(sum(medical_months), 0) AS pmpm,
       sum(total_paid) AS total_paid
FROM mart_member_year
GROUP BY ALL
ORDER BY year, conditions
