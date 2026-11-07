-- Part D prescription drug events: one row per fill.
SELECT
    PDE_ID                                       AS pde_id,
    BENE_ID                                      AS bene_id,
    cms_date(SRVC_DT)                            AS fill_date,
    year(cms_date(SRVC_DT))                      AS year,
    month(cms_date(SRVC_DT))                     AS month,
    code(PRSCRBR_ID)                             AS prescriber_id,
    lpad(trim(PROD_SRVC_ID), 11, '0')            AS ndc11,
    num(QTY_DSPNSD_NUM)                          AS quantity,
    CAST(num(DAYS_SUPLY_NUM) AS INT)             AS days_supply,
    CAST(num(FILL_NUM) AS INT)                   AS fill_number,
    CASE code(BRND_GNRC_CD) WHEN 'B' THEN 'Brand' WHEN 'G' THEN 'Generic' ELSE 'Unknown' END AS brand_generic,
    coalesce(num(CVRD_D_PLAN_PD_AMT), 0) + coalesce(num(NCVRD_PLAN_PD_AMT), 0) AS plan_paid,
    coalesce(num(PTNT_PAY_AMT), 0)               AS patient_paid,
    coalesce(num(LICS_AMT), 0)                   AS low_income_subsidy,
    coalesce(num(TOT_RX_CST_AMT), 0)             AS total_cost,
    code(PHRMCY_SRVC_TYPE_CD)                    AS pharmacy_type
FROM raw_pde
WHERE year(cms_date(SRVC_DT)) BETWEEN {{first_year}} AND {{last_year}}
