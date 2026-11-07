-- Acute inpatient stays with 30-day all-cause readmission flags.
-- Index stays exclude members who died in hospital (status 20), were transferred to another acute
-- hospital (02) or left against medical advice (07), following the CMS hospital-wide readmission logic.
-- Simplification: planned readmissions are not removed (the synthetic files lack the needed procedure detail).
WITH stays AS (
    SELECT claim_id, bene_id, coalesce(admit_date, from_date) AS admit_date, discharge_date, admit_type,
           paid, drg, principal_dx, discharge_status, in_eligible_month,
           greatest(date_diff('day', coalesce(admit_date, from_date), discharge_date), 1) AS los_days
    FROM int_claims
    WHERE setting = 'Inpatient' AND discharge_date IS NOT NULL
),
nexts AS (
    SELECT s.*,
           lead(admit_date) OVER (PARTITION BY bene_id ORDER BY admit_date, claim_id) AS next_admit,
           lead(claim_id)   OVER (PARTITION BY bene_id ORDER BY admit_date, claim_id) AS next_claim
    FROM stays s
)
SELECT *,
       year(admit_date) AS year,
       -- Index stays need a full 30-day follow-up window inside the data, so discharges in the last 30 days of
       -- the analysis period are excluded (otherwise the final year's rate is understated).
       (coalesce(discharge_status, '') NOT IN ('20', '02', '07') AND in_eligible_month
        AND discharge_date <= make_date({{last_year}}, 12, 31) - INTERVAL 30 DAY) AS is_index,
       coalesce(date_diff('day', discharge_date, next_admit) BETWEEN 1 AND 30, false) AS readmitted_30d
FROM nexts
