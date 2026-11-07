-- Member-level medical cost adds back up to the PMPM mart.
SELECT m.total, p.total FROM
    (SELECT sum(medical_paid) AS total FROM mart_member_year) m,
    (SELECT sum(paid) AS total FROM mart_pmpm WHERE setting <> 'Pharmacy') p
WHERE abs(m.total - p.total) > 0.01
