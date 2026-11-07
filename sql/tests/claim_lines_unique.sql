SELECT claim_id, line_num, count(*) FROM stg_claim_lines GROUP BY 1, 2 HAVING count(*) > 1
