-- Funnel-plot outlier detection for level-5 (99215) visit share against specialty peers.
-- Control limits are widened for overdispersion (Spiegelhalter 2005): a multiplicative factor phi is
-- estimated per specialty from winsorized z-scores, so busy practices aren't flagged for ordinary variation.
WITH base AS (
    SELECT p.provider_key, p.specialty, p.visits, coalesce(p.l5, 0) / p.visits AS share_l5, p.mean_level,
           p.paid_at_national_rates, s.share_l5 AS peer_share_l5,
           s.share_l1, s.share_l2, s.share_l3, s.share_l4
    FROM int_em_provider p JOIN mart_em_specialty s USING (specialty)
    WHERE p.visits >= 50
),
z AS (
    SELECT *, (share_l5 - peer_share_l5) / sqrt(peer_share_l5 * (1 - peer_share_l5) / visits) AS z_raw
    FROM base WHERE peer_share_l5 BETWEEN 0.001 AND 0.999
),
bounds AS (
    SELECT specialty, quantile_cont(z_raw, 0.1) AS lo, quantile_cont(z_raw, 0.9) AS hi FROM z GROUP BY 1
),
phi AS (
    SELECT z.specialty, greatest(avg(power(least(greatest(z.z_raw, b.lo), b.hi), 2)), 1.0) AS phi
    FROM z JOIN bounds b USING (specialty) GROUP BY 1
),
unit AS (
    SELECT hcpcs, sum(avg_paid * services) / sum(services) AS pay FROM raw_hcpcs_national
    WHERE hcpcs IN ('99211', '99212', '99213', '99214', '99215') GROUP BY 1
),
peer_price AS (  -- what this provider's visits would have been paid at their specialty's level mix
    SELECT z.provider_key,
           z.visits * (z.share_l1 * u1.pay + z.share_l2 * u2.pay + z.share_l3 * u3.pay
                       + z.share_l4 * u4.pay + z.peer_share_l5 * u5.pay) AS paid_at_peer_mix
    FROM z, (SELECT pay FROM unit WHERE hcpcs = '99211') u1, (SELECT pay FROM unit WHERE hcpcs = '99212') u2,
            (SELECT pay FROM unit WHERE hcpcs = '99213') u3, (SELECT pay FROM unit WHERE hcpcs = '99214') u4,
            (SELECT pay FROM unit WHERE hcpcs = '99215') u5
)
SELECT z.provider_key, z.specialty, z.visits, z.share_l5, z.peer_share_l5, z.mean_level,
       ph.phi,
       z.z_raw / sqrt(ph.phi)                                                         AS z_adjusted,
       least(z.peer_share_l5 + 3.09 * sqrt(ph.phi * z.peer_share_l5 * (1 - z.peer_share_l5) / z.visits), 1) AS upper_limit_998,
       z.z_raw / sqrt(ph.phi) > 3.09                                                  AS high_outlier,
       z.paid_at_national_rates - pp.paid_at_peer_mix                                 AS payment_above_peer_mix
FROM z JOIN phi ph USING (specialty) JOIN peer_price pp USING (provider_key)
