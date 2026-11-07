-- Claims enriched with eligibility. A claim counts toward PMPM only if its service month is a
-- covered fee-for-service month while the member was alive; everything else is an integrity finding.
SELECT
    c.*,
    coalesce(mm.medical_ffs AND mm.alive, false)        AS in_eligible_month,
    b.death_date IS NOT NULL AND c.from_date > b.death_date AS after_death
FROM stg_claims c
LEFT JOIN stg_member_month mm ON mm.bene_id = c.bene_id AND mm.year = c.year AND mm.month = c.month
LEFT JOIN (SELECT bene_id, max(death_date) AS death_date FROM stg_beneficiary_year GROUP BY 1) b ON b.bene_id = c.bene_id
