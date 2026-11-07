-- Drug reference: FDA NDC directory reduced to the NDCs that appear on claims, with therapeutic flags.
SELECT
    n.ndc11,
    lower(trim(coalesce(nullif(trim(n.generic_name), ''), n.brand_name))) AS generic_name,
    n.brand_name,
    n.dosage_form,
    n.pharm_classes,
    n.pharm_classes ILIKE '%HMG-CoA Reductase Inhibitor%'                       AS is_statin,
    (n.pharm_classes ILIKE '%Insulin%' OR n.pharm_classes ILIKE '%Biguanide%'
      OR n.pharm_classes ILIKE '%Sulfonylurea%' OR n.pharm_classes ILIKE '%Dipeptidyl Peptidase 4%'
      OR n.pharm_classes ILIKE '%Sodium-Glucose Transporter 2%' OR n.pharm_classes ILIKE '%GLP-1%'
      OR n.pharm_classes ILIKE '%Thiazolidinedione%')                            AS is_diabetes_med,
    nullif(trim(regexp_extract(n.pharm_classes, '([^,\[]+) \[EPC\]', 1)), '')  AS drug_class
FROM raw_ndc_directory n
WHERE n.ndc11 IN (SELECT DISTINCT ndc11 FROM stg_pde)
