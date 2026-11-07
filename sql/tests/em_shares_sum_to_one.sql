SELECT specialty, share_l1 + share_l2 + share_l3 + share_l4 + share_l5 AS total
FROM mart_em_specialty WHERE abs(share_l1 + share_l2 + share_l3 + share_l4 + share_l5 - 1) > 1e-6
