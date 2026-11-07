-- Eligibility spine: one row per beneficiary per month. The denominator for every PMPM and per-1,000 rate.
-- Medical (Parts A+B fee-for-service) months: entitled to both A and B (buy-in 3 or C) and not in Medicare Advantage.
-- Pharmacy months: enrolled in a Part D plan.
WITH months AS (
    SELECT BENE_ID AS bene_id, CAST(BENE_ENROLLMT_REF_YR AS INT) AS year, m AS month,
           CASE m WHEN 1 THEN MDCR_ENTLMT_BUYIN_IND_01 WHEN 2 THEN MDCR_ENTLMT_BUYIN_IND_02
                  WHEN 3 THEN MDCR_ENTLMT_BUYIN_IND_03 WHEN 4 THEN MDCR_ENTLMT_BUYIN_IND_04
                  WHEN 5 THEN MDCR_ENTLMT_BUYIN_IND_05 WHEN 6 THEN MDCR_ENTLMT_BUYIN_IND_06
                  WHEN 7 THEN MDCR_ENTLMT_BUYIN_IND_07 WHEN 8 THEN MDCR_ENTLMT_BUYIN_IND_08
                  WHEN 9 THEN MDCR_ENTLMT_BUYIN_IND_09 WHEN 10 THEN MDCR_ENTLMT_BUYIN_IND_10
                  WHEN 11 THEN MDCR_ENTLMT_BUYIN_IND_11 ELSE MDCR_ENTLMT_BUYIN_IND_12 END AS buyin,
           CASE m WHEN 1 THEN HMO_IND_01 WHEN 2 THEN HMO_IND_02 WHEN 3 THEN HMO_IND_03 WHEN 4 THEN HMO_IND_04
                  WHEN 5 THEN HMO_IND_05 WHEN 6 THEN HMO_IND_06 WHEN 7 THEN HMO_IND_07 WHEN 8 THEN HMO_IND_08
                  WHEN 9 THEN HMO_IND_09 WHEN 10 THEN HMO_IND_10 WHEN 11 THEN HMO_IND_11 ELSE HMO_IND_12 END AS hmo,
           CASE m WHEN 1 THEN PTD_CNTRCT_ID_01 WHEN 2 THEN PTD_CNTRCT_ID_02 WHEN 3 THEN PTD_CNTRCT_ID_03
                  WHEN 4 THEN PTD_CNTRCT_ID_04 WHEN 5 THEN PTD_CNTRCT_ID_05 WHEN 6 THEN PTD_CNTRCT_ID_06
                  WHEN 7 THEN PTD_CNTRCT_ID_07 WHEN 8 THEN PTD_CNTRCT_ID_08 WHEN 9 THEN PTD_CNTRCT_ID_09
                  WHEN 10 THEN PTD_CNTRCT_ID_10 WHEN 11 THEN PTD_CNTRCT_ID_11 ELSE PTD_CNTRCT_ID_12 END AS ptd,
           CASE m WHEN 1 THEN DUAL_STUS_CD_01 WHEN 2 THEN DUAL_STUS_CD_02 WHEN 3 THEN DUAL_STUS_CD_03
                  WHEN 4 THEN DUAL_STUS_CD_04 WHEN 5 THEN DUAL_STUS_CD_05 WHEN 6 THEN DUAL_STUS_CD_06
                  WHEN 7 THEN DUAL_STUS_CD_07 WHEN 8 THEN DUAL_STUS_CD_08 WHEN 9 THEN DUAL_STUS_CD_09
                  WHEN 10 THEN DUAL_STUS_CD_10 WHEN 11 THEN DUAL_STUS_CD_11 ELSE DUAL_STUS_CD_12 END AS dual
    FROM raw_beneficiary, range(1, 13) t(m)
    WHERE CAST(BENE_ENROLLMT_REF_YR AS INT) BETWEEN {{first_year}} AND {{last_year}}
)
SELECT
    m.bene_id, m.year, m.month, make_date(m.year, m.month, 1) AS month_start,
    (m.buyin IN ('3', 'C') AND coalesce(trim(m.hmo), '0') = '0')            AS medical_ffs,
    (length(trim(coalesce(m.ptd, ''))) = 5 AND left(trim(m.ptd), 1) NOT IN ('N', 'X', '0', '*')) AS part_d,
    (coalesce(trim(m.dual), 'NA') NOT IN ('NA', '00', '09', '99', ''))      AS dual_eligible,
    (b.death_date IS NULL OR make_date(m.year, m.month, 1) <= b.death_date) AS alive
FROM months m
JOIN stg_beneficiary_year b USING (bene_id, year)
