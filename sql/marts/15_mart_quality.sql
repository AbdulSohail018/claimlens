-- Quality measures in the style of HEDIS and Medicare Star Ratings (simplified; see README for definitions).
WITH diabetics AS (SELECT bene_id, year FROM int_conditions WHERE condition = 'Diabetes'),
members AS (SELECT * FROM mart_member_year),
a1c AS (  -- HbA1c test: lab codes 83036/83037 or result codes 3044F-3052F
    SELECT DISTINCT c.bene_id, c.year FROM int_claims c JOIN stg_claim_lines l USING (claim_id)
    WHERE l.hcpcs IN ('83036', '83037', '3044F', '3046F', '3051F', '3052F')
),
statin AS (
    SELECT DISTINCT p.bene_id, p.year FROM stg_pde p JOIN stg_drug d USING (ndc11) WHERE d.is_statin
),
mammo AS (  -- screening or diagnostic mammography
    SELECT DISTINCT c.bene_id, c.year FROM int_claims c JOIN stg_claim_lines l USING (claim_id)
    WHERE l.hcpcs IN ('77065', '77066', '77067', 'G0202', 'G0204', 'G0206')
),
measures AS (
    SELECT m.year, 'Diabetes: HbA1c testing' AS measure, 'Members with diabetes who had an HbA1c test' AS description,
           count(*) AS denominator, count(a1c.bene_id) AS numerator, 'higher' AS better
    FROM members m JOIN diabetics USING (bene_id, year) LEFT JOIN a1c USING (bene_id, year)
    GROUP BY m.year
    UNION ALL
    SELECT m.year, 'Statin use in persons with diabetes',
           'Part D members aged 40-75 with diabetes who filled a statin',
           count(*), count(statin.bene_id), 'higher'
    FROM members m JOIN diabetics USING (bene_id, year) LEFT JOIN statin USING (bene_id, year)
    WHERE m.age BETWEEN 40 AND 75 AND m.rx_months > 0
    GROUP BY m.year
    UNION ALL
    SELECT m.year, 'Breast cancer screening', 'Women aged 50-74 with a mammogram in the year',
           count(*), count(mammo.bene_id), 'higher'
    FROM members m LEFT JOIN mammo USING (bene_id, year)
    WHERE m.sex = 'Female' AND m.age BETWEEN 50 AND 74
    GROUP BY m.year
    UNION ALL
    SELECT year, '30-day all-cause readmissions', 'Index hospital stays followed by another admission within 30 days',
           count(*) FILTER (WHERE is_index), count(*) FILTER (WHERE is_index AND readmitted_30d), 'lower'
    FROM int_admissions GROUP BY year
)
-- Measurability: a measure is only published if the qualifying codes actually occur in the data.
-- (The synthetic files contain almost no HbA1c lab or mammography codes, so those rates would be meaningless 0%s.)
, support AS (
    SELECT 'Diabetes: HbA1c testing' AS measure, count(*) AS qualifying_events FROM a1c
    UNION ALL SELECT 'Breast cancer screening', count(*) FROM mammo
    UNION ALL SELECT 'Statin use in persons with diabetes', count(*) FROM statin
    UNION ALL SELECT '30-day all-cause readmissions', count(*) FROM int_admissions WHERE readmitted_30d
),
ndc AS (SELECT avg((d.ndc11 IS NOT NULL)::INT) AS match_rate FROM stg_pde p LEFT JOIN stg_drug d USING (ndc11))
SELECT m.*, m.numerator / nullif(m.denominator, 0) AS rate,
       s.qualifying_events >= 100 AS measurable,
       CASE
         WHEN s.qualifying_events < 100 THEN
           'Not measurable: ' || CASE WHEN s.qualifying_events = 0 THEN 'no' ELSE 'only ' || s.qualifying_events END
           || ' member-years with a qualifying claim across all years of the synthetic data.'
         WHEN m.measure LIKE 'Statin%' THEN
           'Understated: only ' || CAST(round(100 * ndc.match_rate) AS INT) || '% of synthetic drug codes match the FDA directory, '
           || 'so most statin fills cannot be recognised.'
       END AS data_note
FROM measures m JOIN support s USING (measure) CROSS JOIN ndc
ORDER BY m.measure, m.year
