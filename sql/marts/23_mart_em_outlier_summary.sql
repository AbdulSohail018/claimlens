-- Outliers by specialty, with the payment difference versus peer coding patterns (at 2024 national rates).
SELECT specialty,
       count(*)                                              AS providers,
       count(*) FILTER (WHERE high_outlier)                  AS high_outliers,
       avg(high_outlier::INT)                                AS outlier_share,
       any_value(peer_share_l5)                              AS peer_share_l5,
       median(share_l5) FILTER (WHERE high_outlier)          AS outlier_median_share_l5,
       sum(payment_above_peer_mix) FILTER (WHERE high_outlier) AS outlier_payment_above_peer_mix,
       any_value(phi)                                        AS overdispersion_phi,
       sum(visits)                                           AS visits
FROM mart_em_funnel
GROUP BY specialty
ORDER BY outlier_payment_above_peer_mix DESC NULLS LAST
