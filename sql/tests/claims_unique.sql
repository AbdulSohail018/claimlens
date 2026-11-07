-- Each claim appears once in the header table.
SELECT claim_id, count(*) FROM stg_claims GROUP BY 1 HAVING count(*) > 1
