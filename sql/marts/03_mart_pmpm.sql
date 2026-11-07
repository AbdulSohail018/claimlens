-- Paid amounts and PMPM (per member per month) by year and care setting.
-- Medical PMPM divides by fee-for-service A+B member months; pharmacy PMPM by Part D member months.
WITH medical AS (
    SELECT year, setting,
           sum(paid) FILTER (WHERE in_eligible_month)  AS paid,
           sum(paid)                                   AS paid_all_claims,
           count(*) FILTER (WHERE in_eligible_month)   AS claims
    FROM int_claims GROUP BY ALL
),
rx AS (
    SELECT p.year, 'Pharmacy' AS setting,
           sum(p.plan_paid) FILTER (WHERE mm.part_d AND mm.alive) AS paid,
           sum(p.plan_paid)                                        AS paid_all_claims,
           count(*) FILTER (WHERE mm.part_d AND mm.alive)          AS claims
    FROM stg_pde p
    LEFT JOIN stg_member_month mm ON mm.bene_id = p.bene_id AND mm.year = p.year AND mm.month = p.month
    GROUP BY ALL
),
spend AS (SELECT * FROM medical UNION ALL SELECT * FROM rx)
SELECT s.year, s.setting, s.paid, s.paid_all_claims, s.claims,
       CASE WHEN s.setting = 'Pharmacy' THEN e.rx_member_months ELSE e.medical_member_months END AS member_months,
       s.paid / nullif(CASE WHEN s.setting = 'Pharmacy' THEN e.rx_member_months ELSE e.medical_member_months END, 0) AS pmpm
FROM spend s
JOIN mart_enrollment e USING (year)
ORDER BY s.year, s.setting
