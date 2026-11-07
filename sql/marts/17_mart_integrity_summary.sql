SELECT f.rule,
       count(*)                     AS findings,
       count(DISTINCT f.bene_id)    AS members,
       sum(f.amount_at_risk)        AS amount_at_risk,
       sum(f.amount_at_risk) / (SELECT sum(paid) FROM int_claims) AS share_of_all_paid
FROM int_integrity_findings f
GROUP BY f.rule
ORDER BY amount_at_risk DESC
