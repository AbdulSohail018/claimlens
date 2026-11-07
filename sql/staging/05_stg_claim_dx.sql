-- Diagnoses in long form: one row per claim per distinct ICD-10 code. Feeds chronic-condition flags.
-- Institutional claims carry up to 25 codes; professional and DME claims up to 12 plus a principal code.
WITH firsts AS (
    SELECT 'Professional' AS setting, * FROM raw_carrier QUALIFY row_number() OVER (PARTITION BY CLM_ID) = 1
),
prof AS (
    UNPIVOT (SELECT setting, BENE_ID, CLM_ID, CLM_FROM_DT, PRNCPAL_DGNS_CD, COLUMNS('^ICD_DGNS_CD\d+$') FROM firsts)
    ON PRNCPAL_DGNS_CD, COLUMNS('^ICD_DGNS_CD\d+$') INTO NAME position VALUE dx
),
dme AS (
    UNPIVOT (SELECT 'DME' AS setting, BENE_ID, CLM_ID, CLM_FROM_DT, PRNCPAL_DGNS_CD, COLUMNS('^ICD_DGNS_CD\d+$')
             FROM raw_dme QUALIFY row_number() OVER (PARTITION BY CLM_ID) = 1)
    ON PRNCPAL_DGNS_CD, COLUMNS('^ICD_DGNS_CD\d+$') INTO NAME position VALUE dx
),
inst AS (
    UNPIVOT (
        SELECT * FROM (
            SELECT 'Inpatient' AS setting, BENE_ID, CLM_ID, CLM_FROM_DT, PRNCPAL_DGNS_CD, COLUMNS('^ICD_DGNS_CD\d+$') FROM raw_inpatient
            UNION ALL BY NAME
            SELECT 'Outpatient' AS setting, BENE_ID, CLM_ID, CLM_FROM_DT, PRNCPAL_DGNS_CD, COLUMNS('^ICD_DGNS_CD\d+$') FROM raw_outpatient
            UNION ALL BY NAME
            SELECT 'Skilled nursing' AS setting, BENE_ID, CLM_ID, CLM_FROM_DT, PRNCPAL_DGNS_CD, COLUMNS('^ICD_DGNS_CD\d+$') FROM raw_snf
            UNION ALL BY NAME
            SELECT 'Home health' AS setting, BENE_ID, CLM_ID, CLM_FROM_DT, PRNCPAL_DGNS_CD, COLUMNS('^ICD_DGNS_CD\d+$') FROM raw_hha
            UNION ALL BY NAME
            SELECT 'Hospice' AS setting, BENE_ID, CLM_ID, CLM_FROM_DT, PRNCPAL_DGNS_CD, COLUMNS('^ICD_DGNS_CD\d+$') FROM raw_hospice
        ) QUALIFY row_number() OVER (PARTITION BY CLM_ID) = 1
    )
    ON PRNCPAL_DGNS_CD, COLUMNS('^ICD_DGNS_CD\d+$') INTO NAME position VALUE dx
),
allx AS (
    SELECT * FROM prof UNION ALL BY NAME SELECT * FROM dme UNION ALL BY NAME SELECT * FROM inst
)
SELECT DISTINCT
    CLM_ID AS claim_id, BENE_ID AS bene_id, setting, cms_date(CLM_FROM_DT) AS from_date,
    code(dx) AS dx, position = 'PRNCPAL_DGNS_CD' AS is_principal
FROM allx
WHERE code(dx) IS NOT NULL
  AND year(cms_date(CLM_FROM_DT)) BETWEEN {{first_year}} AND {{last_year}}
