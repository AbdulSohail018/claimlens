-- Chronic condition flags per member per year, using ICD-10 code groups and a CCW-style claims rule:
-- at least one inpatient, skilled nursing or home health claim, or two other claims on different dates.
WITH groups(condition, pattern) AS (
    VALUES ('Diabetes', '^E(0[89]|1[0-3])'),
           ('Heart failure', '^(I50|I11\.?0|I13\.?[02])'),
           ('Hypertension', '^I1[0-5]'),
           ('Ischemic heart disease', '^I2[0-5]'),
           ('Atrial fibrillation', '^I48'),
           ('COPD', '^J4[1-4]'),
           ('Chronic kidney disease', '^N18'),
           ('Depression', '^F3[23]'),
           ('Alzheimer''s and dementia', '^(G30|F0[1-3])'),
           ('Stroke', '^I63'),
           ('Hyperlipidemia', '^E78')
),
hits AS (
    SELECT g.condition, d.bene_id, year(d.from_date) AS year, d.setting, d.from_date
    FROM stg_claim_dx d JOIN groups g ON regexp_matches(d.dx, g.pattern)
)
SELECT condition, bene_id, year
FROM hits
GROUP BY ALL
HAVING count(*) FILTER (WHERE setting IN ('Inpatient', 'Skilled nursing', 'Home health')) >= 1
    OR count(DISTINCT from_date) FILTER (WHERE setting NOT IN ('Inpatient', 'Skilled nursing', 'Home health')) >= 2
