-- One row per beneficiary per year (Master Beneficiary Summary File).
SELECT
    BENE_ID                                         AS bene_id,
    CAST(BENE_ENROLLMT_REF_YR AS INT)               AS year,
    code(STATE_CODE)                                AS state_code,
    cms_date(BENE_BIRTH_DT)                         AS birth_date,
    cms_date(BENE_DEATH_DT)                         AS death_date,
    CASE SEX_IDENT_CD WHEN '1' THEN 'Male' WHEN '2' THEN 'Female' ELSE 'Unknown' END AS sex,
    CASE RTI_RACE_CD WHEN '1' THEN 'White' WHEN '2' THEN 'Black' WHEN '4' THEN 'Asian/Pacific Islander'
         WHEN '5' THEN 'Hispanic' WHEN '6' THEN 'American Indian/Alaska Native' WHEN '3' THEN 'Other'
         ELSE 'Unknown' END                         AS race,
    CAST(num(AGE_AT_END_REF_YR) AS INT)             AS age,
    ESRD_IND = 'Y'                                  AS esrd,
    CAST(num(DUAL_ELGBL_MONS) AS INT)               AS dual_months,
    ENTLMT_RSN_CURR                                 AS entitlement_reason   -- 0 age, 1 disability, 2 ESRD, 3 both
FROM raw_beneficiary
WHERE CAST(BENE_ENROLLMT_REF_YR AS INT) BETWEEN {{first_year}} AND {{last_year}}
