-- Membership by year: the denominators behind every rate in the dashboard.
WITH mm AS (
    SELECT year,
           count(DISTINCT bene_id) FILTER (WHERE medical_ffs AND alive)  AS medical_members,
           count(*) FILTER (WHERE medical_ffs AND alive)                 AS medical_member_months,
           count(DISTINCT bene_id) FILTER (WHERE part_d AND alive)       AS rx_members,
           count(*) FILTER (WHERE part_d AND alive)                      AS rx_member_months,
           avg(dual_eligible::INT) FILTER (WHERE medical_ffs AND alive)  AS dual_share
    FROM stg_member_month GROUP BY year
),
demo AS (
    SELECT year, count(*) AS beneficiaries, avg(age) AS avg_age, avg((sex = 'Female')::INT) AS female_share,
           count(*) FILTER (WHERE year(death_date) = year) AS deaths
    FROM stg_beneficiary_year GROUP BY year
)
SELECT * FROM mm JOIN demo USING (year) ORDER BY year
