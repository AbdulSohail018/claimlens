-- Every claim line from all seven fee-for-service files, in one shape.
-- Professional and DME lines carry their own payment; institutional revenue-center lines carry charges.
WITH prof AS (
    SELECT 'Professional' AS setting, BENE_ID, CLM_ID, CAST(LINE_NUM AS INT) AS line_num,
           code(HCPCS_CD) AS hcpcs, code(HCPCS_1ST_MDFR_CD) AS modifier, CAST(NULL AS VARCHAR) AS rev_center,
           num(LINE_SRVC_CNT) AS units, cms_date(LINE_1ST_EXPNS_DT) AS line_date,
           code(LINE_PLACE_OF_SRVC_CD) AS place_of_service, code(PRF_PHYSN_NPI) AS performing_npi,
           code(PRVDR_SPCLTY) AS specialty_cd, code(BETOS_CD) AS betos,
           num(LINE_NCH_PMT_AMT) AS line_paid, num(LINE_ALOWD_CHRG_AMT) AS line_allowed,
           num(LINE_SBMTD_CHRG_AMT) AS line_charge
    FROM raw_carrier
    UNION ALL
    SELECT 'DME', BENE_ID, CLM_ID, CAST(LINE_NUM AS INT), code(HCPCS_CD), code(HCPCS_1ST_MDFR_CD), NULL,
           num(LINE_SRVC_CNT), cms_date(LINE_1ST_EXPNS_DT), code(LINE_PLACE_OF_SRVC_CD), code(PRVDR_NPI),
           code(PRVDR_SPCLTY), code(BETOS_CD), num(LINE_NCH_PMT_AMT), num(LINE_ALOWD_CHRG_AMT), num(LINE_SBMTD_CHRG_AMT)
    FROM raw_dme
),
inst AS (
    SELECT 'Outpatient' AS setting, BENE_ID, CLM_ID, CAST(CLM_LINE_NUM AS INT) AS line_num, code(HCPCS_CD) AS hcpcs,
           code(HCPCS_1ST_MDFR_CD) AS modifier, code(REV_CNTR) AS rev_center, num(REV_CNTR_UNIT_CNT) AS units,
           cms_date(REV_CNTR_DT) AS line_date, CAST(NULL AS VARCHAR) AS place_of_service,
           code(RNDRNG_PHYSN_NPI) AS performing_npi, CAST(NULL AS VARCHAR) AS specialty_cd,
           CAST(NULL AS VARCHAR) AS betos, num(REV_CNTR_PMT_AMT_AMT) AS line_paid, CAST(NULL AS DOUBLE) AS line_allowed,
           num(REV_CNTR_TOT_CHRG_AMT) AS line_charge
    FROM raw_outpatient
    UNION ALL
    SELECT 'Inpatient', BENE_ID, CLM_ID, CAST(CLM_LINE_NUM AS INT), code(HCPCS_CD), NULL, code(REV_CNTR), NULL,
           NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL
    FROM raw_inpatient
    UNION ALL
    SELECT 'Skilled nursing', BENE_ID, CLM_ID, CAST(CLM_LINE_NUM AS INT), code(HCPCS_CD), NULL, code(REV_CNTR),
           num(REV_CNTR_UNIT_CNT), NULL, NULL, code(RNDRNG_PHYSN_NPI), NULL, NULL, NULL, NULL, num(REV_CNTR_TOT_CHRG_AMT)
    FROM raw_snf
)
SELECT BENE_ID AS bene_id, CLM_ID AS claim_id, * EXCLUDE (BENE_ID, CLM_ID) FROM prof
UNION ALL BY NAME
SELECT BENE_ID AS bene_id, CLM_ID AS claim_id, * EXCLUDE (BENE_ID, CLM_ID) FROM inst
