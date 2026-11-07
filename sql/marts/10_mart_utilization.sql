-- Utilization per 1,000 member-years: the rates payers manage to.
-- The synthetic files carry no emergency-department revenue codes or E/M visit codes, so emergency use is
-- measured through emergency admissions (admission type 1) and professional visits through place of service.
WITH e AS (SELECT year, medical_member_months / 12.0 AS member_years FROM mart_enrollment),
ip AS (
    SELECT year, count(*) AS admits, sum(los_days) AS ip_days,
           count(*) FILTER (WHERE admit_type = '1') AS emergency_admits,
           avg(readmitted_30d::INT) FILTER (WHERE is_index) AS readmit_rate,
           count(*) FILTER (WHERE is_index) AS index_stays
    FROM int_admissions WHERE in_eligible_month GROUP BY 1
),
snf AS (SELECT year, sum(greatest(date_diff('day', from_date, thru_date), 1)) AS snf_days
        FROM int_claims WHERE setting = 'Skilled nursing' AND in_eligible_month GROUP BY 1),
visits AS (  -- one visit = one professional claim, classified by its most common place of service
    SELECT c.year,
           count(DISTINCT c.claim_id) FILTER (WHERE l.place_of_service = '11') AS office_visits,
           count(DISTINCT c.claim_id) FILTER (WHERE l.place_of_service = '20') AS urgent_care_visits
    FROM int_claims c JOIN stg_claim_lines l USING (claim_id)
    WHERE c.setting = 'Professional' AND c.in_eligible_month
    GROUP BY 1
)
SELECT e.year, e.member_years,
       ip.admits, 1000 * ip.admits / e.member_years                       AS admits_per_1000,
       1000 * ip.emergency_admits / e.member_years                        AS emergency_admits_per_1000,
       ip.emergency_admits / nullif(ip.admits, 0)                         AS emergency_admit_share,
       1000 * ip.ip_days / e.member_years                                 AS ip_days_per_1000,
       ip.ip_days / nullif(ip.admits, 0)                                  AS avg_length_of_stay,
       ip.readmit_rate, ip.index_stays,
       1000 * snf.snf_days / e.member_years                               AS snf_days_per_1000,
       1000 * visits.office_visits / e.member_years                       AS office_visits_per_1000,
       1000 * visits.urgent_care_visits / e.member_years                  AS urgent_care_visits_per_1000
FROM e
LEFT JOIN ip USING (year) LEFT JOIN snf USING (year) LEFT JOIN visits USING (year)
ORDER BY e.year
