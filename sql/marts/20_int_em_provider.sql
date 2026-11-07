-- REAL 2024 Medicare data: established-patient office visit levels billed by each provider.
-- Providers appear only as one-way hashed keys (see ingest.py); names and addresses are never loaded.
WITH unit_pay AS (  -- national average Medicare payment per visit level, used to price level mixes consistently
    SELECT hcpcs, sum(avg_paid * services) / sum(services) AS pay FROM raw_hcpcs_national
    WHERE hcpcs IN ('99211', '99212', '99213', '99214', '99215') GROUP BY 1
)
SELECT
    e.provider_key, any_value(e.specialty) AS specialty, any_value(e.state) AS state,
    any_value(e.entity_type) AS entity_type,
    sum(e.services)                                                  AS visits,
    sum(e.services) FILTER (WHERE e.hcpcs = '99211')                 AS l1,
    sum(e.services) FILTER (WHERE e.hcpcs = '99212')                 AS l2,
    sum(e.services) FILTER (WHERE e.hcpcs = '99213')                 AS l3,
    sum(e.services) FILTER (WHERE e.hcpcs = '99214')                 AS l4,
    sum(e.services) FILTER (WHERE e.hcpcs = '99215')                 AS l5,
    sum(e.services * u.pay)                                          AS paid_at_national_rates,
    sum(e.services * CAST(right(e.hcpcs, 1) AS INT)) / sum(e.services) AS mean_level
FROM raw_em_by_provider e
JOIN unit_pay u USING (hcpcs)
GROUP BY e.provider_key
