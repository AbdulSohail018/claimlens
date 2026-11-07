-- One row per claim (header level) across every fee-for-service setting.
-- Claim-level fields repeat on each line in RIF files, so they are taken once per claim with any_value().
WITH carrier AS (
    SELECT 'Professional' AS setting, BENE_ID, CLM_ID,
           any_value(cms_date(CLM_FROM_DT)) AS from_date, any_value(cms_date(CLM_THRU_DT)) AS thru_date,
           any_value(num(CLM_PMT_AMT)) AS paid, any_value(num(NCH_CARR_CLM_ALOWD_AMT)) AS allowed,
           any_value(num(NCH_CARR_CLM_SBMTD_CHRG_AMT)) AS charge,
           any_value(code(CARR_CLM_BLG_NPI_NUM)) AS billing_npi, any_value(code(PRF_PHYSN_NPI)) AS attending_npi,
           any_value(code(PRNCPAL_DGNS_CD)) AS principal_dx, any_value(code(PRVDR_STATE_CD)) AS provider_state,
           CAST(NULL AS VARCHAR) AS drg, CAST(NULL AS DATE) AS admit_date, CAST(NULL AS DATE) AS discharge_date,
           CAST(NULL AS VARCHAR) AS discharge_status, CAST(NULL AS DOUBLE) AS covered_days,
           CAST(NULL AS VARCHAR) AS admit_type, any_value(code(CARR_CLM_PMT_DNL_CD)) AS denial_cd
    FROM raw_carrier GROUP BY BENE_ID, CLM_ID
),
dme AS (
    SELECT 'DME', BENE_ID, CLM_ID, any_value(cms_date(CLM_FROM_DT)), any_value(cms_date(CLM_THRU_DT)),
           any_value(num(CLM_PMT_AMT)), any_value(num(NCH_CARR_CLM_ALOWD_AMT)), any_value(num(NCH_CARR_CLM_SBMTD_CHRG_AMT)),
           any_value(code(PRVDR_NPI)), any_value(code(RFR_PHYSN_NPI)), any_value(code(PRNCPAL_DGNS_CD)),
           any_value(code(PRVDR_STATE_CD)), NULL, NULL, NULL, NULL, NULL, NULL, any_value(code(CARR_CLM_PMT_DNL_CD))
    FROM raw_dme GROUP BY BENE_ID, CLM_ID
),
institutional AS (
    SELECT setting, BENE_ID, CLM_ID,
           any_value(cms_date(CLM_FROM_DT)), any_value(cms_date(CLM_THRU_DT)),
           any_value(num(CLM_PMT_AMT)), any_value(num(CLM_PMT_AMT)), any_value(num(CLM_TOT_CHRG_AMT)),
           any_value(code(ORG_NPI_NUM)), any_value(code(AT_PHYSN_NPI)), any_value(code(PRNCPAL_DGNS_CD)),
           any_value(code(PRVDR_STATE_CD)), any_value(drg), any_value(cms_date(admit_dt)),
           any_value(cms_date(dischg_dt)), any_value(code(PTNT_DSCHRG_STUS_CD)), any_value(num(util_days)),
           any_value(code(admit_type)), any_value(code(CLM_MDCR_NON_PMT_RSN_CD))
    FROM (
        SELECT 'Inpatient' AS setting, BENE_ID, CLM_ID, CLM_FROM_DT, CLM_THRU_DT, CLM_PMT_AMT, CLM_TOT_CHRG_AMT,
               ORG_NPI_NUM, AT_PHYSN_NPI, PRNCPAL_DGNS_CD, PRVDR_STATE_CD, CLM_DRG_CD AS drg,
               CLM_ADMSN_DT AS admit_dt, NCH_BENE_DSCHRG_DT AS dischg_dt, PTNT_DSCHRG_STUS_CD,
               CLM_UTLZTN_DAY_CNT AS util_days, CLM_IP_ADMSN_TYPE_CD AS admit_type, CLM_MDCR_NON_PMT_RSN_CD
        FROM raw_inpatient
        UNION ALL BY NAME
        SELECT 'Skilled nursing' AS setting, BENE_ID, CLM_ID, CLM_FROM_DT, CLM_THRU_DT, CLM_PMT_AMT, CLM_TOT_CHRG_AMT,
               ORG_NPI_NUM, AT_PHYSN_NPI, PRNCPAL_DGNS_CD, PRVDR_STATE_CD, CLM_DRG_CD AS drg,
               CLM_ADMSN_DT AS admit_dt, NCH_BENE_DSCHRG_DT AS dischg_dt, PTNT_DSCHRG_STUS_CD,
               CLM_UTLZTN_DAY_CNT AS util_days, CLM_IP_ADMSN_TYPE_CD AS admit_type, CLM_MDCR_NON_PMT_RSN_CD
        FROM raw_snf
        UNION ALL BY NAME
        SELECT 'Outpatient' AS setting, BENE_ID, CLM_ID, CLM_FROM_DT, CLM_THRU_DT, CLM_PMT_AMT, CLM_TOT_CHRG_AMT,
               ORG_NPI_NUM, AT_PHYSN_NPI, PRNCPAL_DGNS_CD, PRVDR_STATE_CD, PTNT_DSCHRG_STUS_CD, CLM_MDCR_NON_PMT_RSN_CD
        FROM raw_outpatient
        UNION ALL BY NAME
        SELECT 'Home health' AS setting, BENE_ID, CLM_ID, CLM_FROM_DT, CLM_THRU_DT, CLM_PMT_AMT, CLM_TOT_CHRG_AMT,
               ORG_NPI_NUM, AT_PHYSN_NPI, PRNCPAL_DGNS_CD, PRVDR_STATE_CD, PTNT_DSCHRG_STUS_CD, CLM_MDCR_NON_PMT_RSN_CD
        FROM raw_hha
        UNION ALL BY NAME
        SELECT 'Hospice' AS setting, BENE_ID, CLM_ID, CLM_FROM_DT, CLM_THRU_DT, CLM_PMT_AMT, CLM_TOT_CHRG_AMT,
               ORG_NPI_NUM, AT_PHYSN_NPI, PRNCPAL_DGNS_CD, PRVDR_STATE_CD, PTNT_DSCHRG_STUS_CD, CLM_MDCR_NON_PMT_RSN_CD
        FROM raw_hospice
    )
    GROUP BY setting, BENE_ID, CLM_ID
),
unioned AS (
    SELECT * FROM carrier UNION ALL SELECT * FROM dme UNION ALL SELECT * FROM institutional
)
SELECT
    CLM_ID AS claim_id, BENE_ID AS bene_id, setting,
    from_date, thru_date, year(from_date) AS year, month(from_date) AS month,
    coalesce(paid, 0) AS paid, allowed, charge,
    billing_npi, attending_npi, principal_dx, provider_state,
    nullif(drg, '0') AS drg, admit_date, coalesce(discharge_date, thru_date) AS discharge_date,
    discharge_status, covered_days, admit_type, denial_cd
FROM unioned
WHERE year(from_date) BETWEEN {{first_year}} AND {{last_year}}
