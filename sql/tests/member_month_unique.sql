SELECT bene_id, year, month, count(*) FROM stg_member_month GROUP BY ALL HAVING count(*) > 1
