SELECT pde_id, count(*) FROM stg_pde GROUP BY 1 HAVING count(*) > 1
