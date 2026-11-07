-- Referential integrity: every claim and fill belongs to a beneficiary in the enrollment file.
SELECT 'claim' AS kind, claim_id FROM stg_claims c
WHERE NOT EXISTS (SELECT 1 FROM stg_beneficiary_year b WHERE b.bene_id = c.bene_id)
UNION ALL
SELECT 'pde', pde_id FROM stg_pde p
WHERE NOT EXISTS (SELECT 1 FROM stg_beneficiary_year b WHERE b.bene_id = p.bene_id)
