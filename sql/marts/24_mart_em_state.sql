-- Share of providers flagged as level-5 outliers, by state (states with 100+ assessed providers).
SELECT p.state, count(*) AS providers, count(*) FILTER (WHERE f.high_outlier) AS high_outliers,
       avg(f.high_outlier::INT) AS outlier_share, sum(f.visits) AS visits
FROM mart_em_funnel f JOIN int_em_provider p USING (provider_key)
GROUP BY p.state HAVING count(*) >= 100
ORDER BY outlier_share DESC
