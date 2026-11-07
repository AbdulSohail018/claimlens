-- How do synthetic professional payments compare with what Medicare really paid for the same code in 2024?
-- Used to judge how far the synthetic data's dollar values can be trusted, not to flag providers.
WITH synth AS (
    SELECT hcpcs, count(*) AS lines, median(line_paid / nullif(units, 0)) AS synthetic_paid_per_unit
    FROM stg_claim_lines
    WHERE setting = 'Professional' AND line_paid > 0 AND hcpcs IS NOT NULL
    GROUP BY 1 HAVING count(*) >= 100
),
real AS (
    SELECT hcpcs, any_value(hcpcs_desc) AS hcpcs_desc,
           sum(avg_paid * services) / sum(services) AS medicare_paid_2024, sum(services) AS medicare_services_2024
    FROM raw_hcpcs_national GROUP BY 1
)
SELECT s.hcpcs, r.hcpcs_desc, s.lines, s.synthetic_paid_per_unit, r.medicare_paid_2024, r.medicare_services_2024,
       s.synthetic_paid_per_unit / nullif(r.medicare_paid_2024, 0) AS ratio
FROM synth s JOIN real r USING (hcpcs)
ORDER BY s.lines DESC
