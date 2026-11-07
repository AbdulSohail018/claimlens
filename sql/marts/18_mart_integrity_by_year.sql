SELECT c.year, f.rule, count(*) AS findings, sum(f.amount_at_risk) AS amount_at_risk
FROM int_integrity_findings f JOIN stg_claims c USING (claim_id)
GROUP BY ALL ORDER BY c.year, f.rule
