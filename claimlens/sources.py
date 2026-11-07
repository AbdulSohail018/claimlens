"""Where every dataset comes from. All sources are public and free to use."""

CMS = "https://data.cms.gov/sites/default/files"

# CMS Synthetic Medicare Enrollment, Fee-for-Service Claims and Prescription Drug Event files (RIF format).
# Realistic-but-not-real data for 8,671 beneficiaries, 2015-2025. No real patients.
# https://data.cms.gov/collection/synthetic-medicare-enrollment-fee-for-service-claims-and-prescription-drug-event
SYNTHETIC_BENEFICIARY = {
    2015: f"{CMS}/2023-04/d5da04d5-61c8-4174-be11-02d0f58217e7/beneficiary_2015.csv",
    2016: f"{CMS}/2023-04/c401e869-f85e-4c57-a9ae-fa7b982593d6/beneficiary_2016.csv",
    2017: f"{CMS}/2023-04/b70edfc5-cd50-4983-9837-b5ece38d400f/beneficiary_2017.csv",
    2018: f"{CMS}/2023-04/bf7aac0e-3ba3-4e7e-9463-073316a17d8a/beneficiary_2018.csv",
    2019: f"{CMS}/2023-04/7f65254b-174e-4460-aa49-6759ea8397af/beneficiary_2019.csv",
    2020: f"{CMS}/2023-04/74b86018-5148-45bb-87f7-c551eda070d8/beneficiary_2020.csv",
    2021: f"{CMS}/2023-04/98832739-88bd-4243-87fe-ee12b8542baf/beneficiary_2021.csv",
    2022: f"{CMS}/2023-04/831cfb41-3a7a-4ce0-b02f-04d27df56b31/beneficiary_2022.csv",
    2023: f"{CMS}/2023-04/18fe0f5d-4126-432f-b12b-2569db9bdefa/beneficiary_2023.csv",
    2024: f"{CMS}/2023-04/402c0430-aab0-47f9-ab51-4274e30d2f79/beneficiary_2024.csv",
    2025: f"{CMS}/2023-04/428fe76b-964d-48ca-b310-86f246fac829/beneficiary_2025.csv",
}

# claim file -> (url, column holding the service date used to partition by year)
SYNTHETIC_CLAIMS = {
    "carrier": (f"{CMS}/2023-04/b6fe03a8-82e2-49b7-a9fe-9eb68c8ac4d0/Carrier.zip", "CLM_FROM_DT"),
    "outpatient": (f"{CMS}/2023-04/c3d8a962-c6b8-4a59-adb5-f0495cc81fda/Outpatient.zip", "CLM_FROM_DT"),
    "inpatient": (f"{CMS}/2023-04/67157de9-d962-4af0-bf0e-3578b3afec58/inpatient.csv", "CLM_FROM_DT"),
    "snf": (f"{CMS}/2023-04/1138e453-f79d-4bd9-8561-26a7d7a7cc36/snf.csv", "CLM_FROM_DT"),
    "hha": (f"{CMS}/2023-04/cf87867a-c878-4709-84f4-29be1b07ae5b/hha.csv", "CLM_FROM_DT"),
    "hospice": (f"{CMS}/2023-04/72c61730-dcb4-4246-af69-f573c997e5dd/hospice.csv", "CLM_FROM_DT"),
    "dme": (f"{CMS}/2023-04/647931dd-f8ea-423a-98a3-655e586a7c1f/dme.csv", "CLM_FROM_DT"),
    "pde": (f"{CMS}/2023-04/a3969dcf-0799-49fe-8380-9eef788d5ac4/pde.csv", "SRVC_DT"),
}

# Real Medicare Physician & Other Practitioners public use files, 2024 (released May 2026).
# https://data.cms.gov/provider-summary-by-type-of-service/medicare-physician-other-practitioners
PUF_YEAR = 2024
PUF_GEO_SERVICE = f"{CMS}/2026-05/e534c74b-79b8-4892-8a95-5a17e2dfec9f/MUP_PHY_R26_P05_V10_D24_Geo.csv"
PUF_PROVIDER_SERVICE = f"{CMS}/2026-05/b5ebab5a-f490-418a-9bce-4b9f31419356/PHY_R26_P05_V10_D24_Prov_Svc.csv"

# Real Medicare Inpatient Hospitals by Provider and Service, 2024: MS-DRG names and national payment benchmarks.
PUF_INPATIENT = f"{CMS}/2026-04/828defb5-c9e6-4442-8c1b-f27bc0799daf/MUP_INP_RY26_P03_V10_DY24_PrvSvc.CSV"

# FDA National Drug Code Directory: drug names and pharmacologic classes for Part D NDCs.
FDA_NDC_ZIP = "https://www.accessdata.fda.gov/cder/ndctext.zip"

# Office and outpatient evaluation & management visit codes, used for the coding-intensity analysis.
EM_NEW = ["99202", "99203", "99204", "99205"]
EM_ESTABLISHED = ["99211", "99212", "99213", "99214", "99215"]
