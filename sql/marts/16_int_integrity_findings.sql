-- Payment-integrity rules on the synthetic claims. Each row is one finding on one claim or line.
WITH dup_lines AS (
    -- the same member, service, date, performing provider and amount, billed on two different claims
    SELECT l.claim_id, l.bene_id, l.line_paid AS amount,
           count(*) OVER (PARTITION BY l.bene_id, l.hcpcs, l.line_date, l.performing_npi, l.line_paid) AS copies,
           row_number() OVER (PARTITION BY l.bene_id, l.hcpcs, l.line_date, l.performing_npi, l.line_paid
                              ORDER BY l.claim_id, l.line_num) AS copy_num,
           count(DISTINCT l.claim_id) OVER (PARTITION BY l.bene_id, l.hcpcs, l.line_date, l.performing_npi, l.line_paid) AS claims
    FROM stg_claim_lines l
    WHERE l.setting = 'Professional' AND l.line_paid > 0 AND l.hcpcs IS NOT NULL AND l.line_date IS NOT NULL
)
SELECT 'Duplicate professional line' AS rule, claim_id, bene_id, amount AS amount_at_risk
FROM dup_lines WHERE claims > 1 AND copy_num > 1
UNION ALL
SELECT 'Service after date of death', claim_id, bene_id, paid FROM int_claims WHERE after_death AND paid > 0  -- needs death dates; the synthetic files have none
UNION ALL
SELECT 'Service outside covered months', claim_id, bene_id, paid FROM int_claims
WHERE NOT in_eligible_month AND NOT after_death AND paid > 0
UNION ALL
SELECT 'Discharge before admission', claim_id, bene_id, paid FROM int_claims
WHERE setting = 'Inpatient' AND admit_date IS NOT NULL AND discharge_date < admit_date
UNION ALL
SELECT 'Paid on a $0 charge', claim_id, bene_id, paid FROM int_claims WHERE coalesce(charge, 0) <= 0 AND paid > 0
