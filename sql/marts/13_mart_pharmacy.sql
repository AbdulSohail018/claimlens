-- Part D pharmacy KPIs by year.
WITH fills AS (
    SELECT p.*, d.generic_name, d.ndc11 IS NOT NULL AS ndc_matched
    FROM stg_pde p LEFT JOIN stg_drug d USING (ndc11)
)
SELECT f.year,
       count(*)                                                       AS fills,
       sum(plan_paid)                                                 AS plan_paid,
       sum(plan_paid) / any_value(e.rx_member_months)                 AS rx_pmpm,
       12.0 * count(*) / any_value(e.rx_member_months)                AS fills_per_member_year,
       avg(total_cost)                                                AS avg_cost_per_fill,
       avg((brand_generic = 'Generic')::INT) FILTER (WHERE brand_generic <> 'Unknown') AS generic_dispensing_rate,
       sum(plan_paid) FILTER (WHERE brand_generic = 'Brand') / nullif(sum(plan_paid), 0) AS brand_share_of_cost,
       avg(ndc_matched::INT)                                          AS ndc_match_rate,
       sum(patient_paid) / nullif(sum(total_cost), 0)                 AS member_cost_share
FROM fills f JOIN mart_enrollment e USING (year)
GROUP BY f.year
ORDER BY f.year
