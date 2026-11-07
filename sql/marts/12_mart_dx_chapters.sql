-- Spend by ICD-10 chapter of the claim's principal diagnosis.
WITH chapters(letter_from, letter_to, chapter) AS (
    VALUES ('A00', 'B99', 'Infections'), ('C00', 'D49', 'Cancer and neoplasms'), ('D50', 'D89', 'Blood and immune'),
           ('E00', 'E89', 'Endocrine and metabolic'), ('F01', 'F99', 'Mental and behavioral'),
           ('G00', 'G99', 'Nervous system'), ('H00', 'H59', 'Eye'), ('H60', 'H95', 'Ear'),
           ('I00', 'I99', 'Circulatory'), ('J00', 'J99', 'Respiratory'), ('K00', 'K95', 'Digestive'),
           ('L00', 'L99', 'Skin'), ('M00', 'M99', 'Musculoskeletal'), ('N00', 'N99', 'Genitourinary'),
           ('O00', 'O9A', 'Pregnancy'), ('Q00', 'Q99', 'Congenital'), ('R00', 'R99', 'Symptoms and abnormal findings'),
           ('S00', 'T88', 'Injury and poisoning'), ('V00', 'Y99', 'External causes'),
           ('Z00', 'Z99', 'Health status and encounters')
)
SELECT c.year, coalesce(ch.chapter, 'Unknown') AS chapter, c.setting,
       sum(c.paid) AS paid, count(*) AS claims
FROM int_claims c
LEFT JOIN chapters ch ON left(c.principal_dx, 3) BETWEEN ch.letter_from AND ch.letter_to
WHERE c.in_eligible_month
GROUP BY ALL
