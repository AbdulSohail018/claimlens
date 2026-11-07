-- Top inpatient DRGs, with real 2024 national Medicare payment for the same DRG as a benchmark.
SELECT a.drg, d.drg_desc,
       count(*)                                         AS stays,
       sum(a.paid)                                      AS paid,
       avg(a.paid)                                      AS avg_paid,
       avg(a.los_days)                                  AS avg_los,
       avg(a.readmitted_30d::INT) FILTER (WHERE a.is_index) AS readmit_rate,
       d.avg_medicare_paid                              AS national_avg_paid_2024,
       d.discharges                                     AS national_discharges_2024
FROM int_admissions a
LEFT JOIN raw_drg_national d ON d.drg = lpad(a.drg, 3, '0')
WHERE a.in_eligible_month AND a.drg IS NOT NULL
GROUP BY a.drg, d.drg_desc, d.avg_medicare_paid, d.discharges
ORDER BY paid DESC
