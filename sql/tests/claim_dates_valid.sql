-- Every claim has a service date in range and does not end before it starts.
SELECT claim_id, from_date, thru_date FROM stg_claims
WHERE from_date IS NULL OR thru_date < from_date
   OR from_date NOT BETWEEN make_date({{first_year}}, 1, 1) AND make_date({{last_year}}, 12, 31)
