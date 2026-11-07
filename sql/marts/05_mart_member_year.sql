-- One row per member per year with total cost, demographics and condition burden.
WITH months AS (
    SELECT bene_id, year,
           count(*) FILTER (WHERE medical_ffs AND alive) AS medical_months,
           count(*) FILTER (WHERE part_d AND alive)      AS rx_months,
           bool_or(dual_eligible)                        AS dual
    FROM stg_member_month GROUP BY ALL
),
med AS (SELECT bene_id, year, sum(paid) AS medical_paid FROM int_claims WHERE in_eligible_month GROUP BY ALL),
rx AS (SELECT bene_id, year, sum(plan_paid) AS rx_paid FROM stg_pde GROUP BY ALL),
cond AS (SELECT bene_id, year, count(*) AS conditions FROM int_conditions GROUP BY ALL)
SELECT
    m.bene_id, m.year, b.age, b.sex, b.race, b.state_code, m.dual,
    CASE WHEN b.age < 65 THEN 'Under 65' WHEN b.age < 75 THEN '65-74' WHEN b.age < 85 THEN '75-84' ELSE '85+' END AS age_band,
    m.medical_months, m.rx_months,
    coalesce(med.medical_paid, 0)                         AS medical_paid,
    coalesce(rx.rx_paid, 0)                               AS rx_paid,
    coalesce(med.medical_paid, 0) + coalesce(rx.rx_paid, 0) AS total_paid,
    coalesce(cond.conditions, 0)                          AS conditions
FROM months m
JOIN stg_beneficiary_year b USING (bene_id, year)
LEFT JOIN med USING (bene_id, year)
LEFT JOIN rx USING (bene_id, year)
LEFT JOIN cond USING (bene_id, year)
WHERE m.medical_months > 0
