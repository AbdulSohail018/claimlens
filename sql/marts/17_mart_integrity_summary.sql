-- Every rule is listed, including those that found nothing, so a clean result is visible rather than silent.
WITH rules(rule, description) AS (
    VALUES ('Service outside covered months', 'Paid claim for a month without Part A + B fee-for-service coverage'),
           ('Duplicate professional line', 'Same member, service, date, provider and amount billed on two claims'),
           ('Service after date of death', 'Service dated after the member''s death (synthetic files carry no death dates)'),
           ('Discharge before admission', 'Inpatient stay that ends before it starts'),
           ('Paid on a $0 charge', 'Payment made against a claim with no submitted charge')
)
SELECT r.rule, r.description,
       count(f.claim_id)                                    AS findings,
       count(DISTINCT f.bene_id)                            AS members,
       coalesce(sum(f.amount_at_risk), 0)                   AS amount_at_risk,
       coalesce(sum(f.amount_at_risk), 0) / (SELECT sum(paid) FROM int_claims) AS share_of_all_paid
FROM rules r LEFT JOIN int_integrity_findings f USING (rule)
GROUP BY r.rule, r.description
ORDER BY amount_at_risk DESC, r.rule
