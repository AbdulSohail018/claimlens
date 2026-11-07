-- At least 99% of diagnosis codes must look like ICD-10-CM (letter, digit, then up to 5 characters).
SELECT avg((NOT regexp_matches(dx, '^[A-Z][0-9][0-9A-Z]{1,5}$'))::INT) AS bad_share
FROM stg_claim_dx
HAVING avg((NOT regexp_matches(dx, '^[A-Z][0-9][0-9A-Z]{1,5}$'))::INT) > 0.01
