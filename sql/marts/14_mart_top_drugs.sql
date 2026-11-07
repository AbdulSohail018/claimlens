-- Highest-cost drugs, named through the FDA NDC directory. Unmatched NDCs are grouped, not dropped.
SELECT p.year,
       coalesce(d.generic_name, 'NDC not in FDA directory') AS drug,
       coalesce(d.drug_class, CASE WHEN d.ndc11 IS NULL THEN 'Not identified (NDC not in FDA directory)'
                                   ELSE 'No established class in FDA directory' END) AS drug_class,
       count(*)                                            AS fills,
       count(DISTINCT p.bene_id)                           AS members,
       sum(p.plan_paid)                                    AS plan_paid,
       avg((p.brand_generic = 'Brand')::INT)               AS brand_share
FROM stg_pde p LEFT JOIN stg_drug d USING (ndc11)
GROUP BY ALL
ORDER BY p.year, plan_paid DESC
