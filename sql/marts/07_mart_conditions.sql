-- Prevalence and cost by chronic condition, per year.
SELECT c.year, c.condition,
       count(*)                                                    AS members,
       count(*) / any_value(e.medical_members)                     AS prevalence,
       sum(m.total_paid) / nullif(sum(m.medical_months), 0)        AS pmpm_with_condition,
       avg(m.conditions)                                           AS avg_conditions
FROM int_conditions c
JOIN mart_member_year m USING (bene_id, year)
JOIN mart_enrollment e USING (year)
GROUP BY ALL
ORDER BY c.year, members DESC
