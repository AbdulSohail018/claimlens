-- Specialty benchmarks for established office visits (providers with 50+ such visits, specialties with 30+ providers).
WITH p AS (SELECT * FROM int_em_provider WHERE visits >= 50)
SELECT specialty,
       count(*)                                 AS providers,
       sum(visits)                              AS visits,
       sum(coalesce(l1, 0)) / sum(visits)       AS share_l1,
       sum(coalesce(l2, 0)) / sum(visits)       AS share_l2,
       sum(coalesce(l3, 0)) / sum(visits)       AS share_l3,
       sum(coalesce(l4, 0)) / sum(visits)       AS share_l4,
       sum(coalesce(l5, 0)) / sum(visits)       AS share_l5,
       sum(mean_level * visits) / sum(visits)   AS mean_level
FROM p
GROUP BY specialty
HAVING count(*) >= 30
ORDER BY visits DESC
