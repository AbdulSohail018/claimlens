-- Utilization per 1,000 member-years: the rates payers manage to.
WITH e AS (SELECT year, medical_member_months / 12.0 AS member_years FROM mart_enrollment),
ip AS (
    SELECT year, count(*) AS admits, sum(los_days) AS ip_days,
           avg(readmitted_30d::INT) FILTER (WHERE is_index) AS readmit_rate,
           count(*) FILTER (WHERE is_index) AS index_stays
    FROM int_admissions WHERE in_eligible_month GROUP BY 1
),
er AS (  -- emergency department visits: outpatient facility claims with an ED revenue center (0450-0459, 0981)
    SELECT year(l_from) AS year, count(DISTINCT claim_id) AS er_visits FROM (
        SELECT c.claim_id, c.from_date AS l_from FROM int_claims c
        JOIN stg_claim_lines l USING (claim_id)
        WHERE c.setting = 'Outpatient' AND c.in_eligible_month
          AND (l.rev_center BETWEEN '0450' AND '0459' OR l.rev_center = '0981')
    ) GROUP BY 1
),
snf AS (SELECT year, sum(coalesce(covered_days, date_diff('day', from_date, thru_date))) AS snf_days
        FROM int_claims WHERE setting = 'Skilled nursing' AND in_eligible_month GROUP BY 1),
office AS (  -- office E/M visits from professional claims
    SELECT c.year, count(*) AS office_visits FROM int_claims c JOIN stg_claim_lines l USING (claim_id)
    WHERE c.setting = 'Professional' AND c.in_eligible_month AND l.hcpcs BETWEEN '99202' AND '99215'
    GROUP BY 1
)
SELECT e.year, e.member_years,
       ip.admits, 1000 * ip.admits / e.member_years        AS admits_per_1000,
       1000 * ip.ip_days / e.member_years                  AS ip_days_per_1000,
       ip.ip_days / nullif(ip.admits, 0)                   AS avg_length_of_stay,
       ip.readmit_rate, ip.index_stays,
       er.er_visits, 1000 * er.er_visits / e.member_years  AS er_visits_per_1000,
       1000 * snf.snf_days / e.member_years                AS snf_days_per_1000,
       1000 * office.office_visits / e.member_years        AS office_visits_per_1000
FROM e
LEFT JOIN ip USING (year) LEFT JOIN er USING (year) LEFT JOIN snf USING (year) LEFT JOIN office USING (year)
ORDER BY e.year
