-- Privacy: the real-provider marts must never contain a raw 10-digit NPI, only hashed keys.
SELECT provider_key FROM mart_em_funnel WHERE NOT regexp_matches(provider_key, '^P[0-9a-f]{10}$')
UNION ALL
SELECT provider_key FROM int_em_provider WHERE regexp_matches(provider_key, '^[0-9]{10}$')
