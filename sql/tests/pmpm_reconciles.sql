-- Financial reconciliation: medical spend in the PMPM mart equals eligible paid claims in staging, to the cent.
SELECT m.total, c.total FROM
    (SELECT sum(paid) AS total FROM mart_pmpm WHERE setting <> 'Pharmacy') m,
    (SELECT sum(paid) AS total FROM int_claims WHERE in_eligible_month) c
WHERE abs(m.total - c.total) > 0.01
