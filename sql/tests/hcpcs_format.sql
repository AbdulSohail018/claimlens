-- At least 99% of procedure codes must be 5-character CPT/HCPCS codes.
SELECT avg((NOT regexp_matches(hcpcs, '^[A-Z0-9]{4}[A-Z0-9]$'))::INT) AS bad_share
FROM stg_claim_lines WHERE hcpcs IS NOT NULL
HAVING avg((NOT regexp_matches(hcpcs, '^[A-Z0-9]{4}[A-Z0-9]$'))::INT) > 0.01
