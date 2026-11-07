"""A tiny raw layer in the exact CMS RIF column layout, with known answers for every rule.

Members:
  B1  fee-for-service and Part D all of 2020: diabetes, HbA1c test, statin, readmission, ED visit,
      and a professional line billed twice on two claims.
  B2  covered January to June 2020 only, died 15 March 2021: one claim outside coverage, one after death.
  B3  Medicare Advantage all year (no fee-for-service months): excluded from every denominator.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

YEAR = 2020


def _write(df: pd.DataFrame, folder: Path, date_col: str) -> None:
    df = df.astype(str).replace({"None": "", "nan": ""})
    df["svc_year"] = df[date_col].str[-4:]
    for year, part in df.groupby("svc_year"):
        out = folder / f"svc_year={year}"
        out.mkdir(parents=True, exist_ok=True)
        part.drop(columns="svc_year").to_parquet(out / "data_0.parquet", index=False)


def bene_row(bene, year, buyin, hmo, ptd, death="", sex="1", age="70", birth="01-Jan-1950"):
    row = {"BENE_ID": bene, "BENE_ENROLLMT_REF_YR": str(year), "STATE_CODE": "05", "BENE_BIRTH_DT": birth,
           "BENE_DEATH_DT": death, "SEX_IDENT_CD": sex, "RTI_RACE_CD": "1", "AGE_AT_END_REF_YR": age,
           "ESRD_IND": "0", "DUAL_ELGBL_MONS": "0", "ENTLMT_RSN_CURR": "0"}
    for m in range(1, 13):
        row[f"MDCR_ENTLMT_BUYIN_IND_{m:02d}"] = buyin[m - 1]
        row[f"HMO_IND_{m:02d}"] = hmo[m - 1]
        row[f"PTD_CNTRCT_ID_{m:02d}"] = ptd[m - 1]
        row[f"DUAL_STUS_CD_{m:02d}"] = "NA"
    return row


def prof(bene, clm, date, line, hcpcs, paid, dx="E119", npi="1111111111", claim_paid=None):
    # In RIF files the claim-level total repeats on every line of the claim.
    row = {"BENE_ID": bene, "CLM_ID": clm, "CLM_FROM_DT": date, "CLM_THRU_DT": date,
           "CLM_PMT_AMT": str(claim_paid if claim_paid is not None else paid),
           "NCH_CARR_CLM_ALOWD_AMT": str(paid * 1.25), "NCH_CARR_CLM_SBMTD_CHRG_AMT": str(paid * 2),
           "CARR_CLM_BLG_NPI_NUM": "1063654341", "PRF_PHYSN_NPI": npi, "PRNCPAL_DGNS_CD": dx,
           "PRVDR_STATE_CD": "CA", "CARR_CLM_PMT_DNL_CD": "1", "LINE_NUM": str(line), "HCPCS_CD": hcpcs,
           "HCPCS_1ST_MDFR_CD": "", "LINE_SRVC_CNT": "1", "LINE_1ST_EXPNS_DT": date, "LINE_PLACE_OF_SRVC_CD": "11",
           "PRVDR_SPCLTY": "11", "BETOS_CD": "M1B", "LINE_NCH_PMT_AMT": str(paid),
           "LINE_ALOWD_CHRG_AMT": str(paid * 1.25), "LINE_SBMTD_CHRG_AMT": str(paid * 2)}
    for i in range(1, 13):
        row[f"ICD_DGNS_CD{i}"] = dx if i == 1 else ""
    return row


def inst(bene, clm, from_dt, thru_dt, paid, dx, line=1, rev="0001", hcpcs="", extra=None):
    row = {"BENE_ID": bene, "CLM_ID": clm, "CLM_FROM_DT": from_dt, "CLM_THRU_DT": thru_dt, "CLM_PMT_AMT": str(paid),
           "CLM_TOT_CHRG_AMT": str(paid * 3), "ORG_NPI_NUM": "1578657367", "AT_PHYSN_NPI": "9999870899",
           "PRNCPAL_DGNS_CD": dx, "PRVDR_STATE_CD": "05", "PTNT_DSCHRG_STUS_CD": "01", "CLM_MDCR_NON_PMT_RSN_CD": "",
           "CLM_LINE_NUM": str(line), "HCPCS_CD": hcpcs, "HCPCS_1ST_MDFR_CD": "", "REV_CNTR": rev,
           "REV_CNTR_UNIT_CNT": "1", "REV_CNTR_DT": from_dt, "RNDRNG_PHYSN_NPI": "9999870899",
           "REV_CNTR_PMT_AMT_AMT": str(paid), "REV_CNTR_TOT_CHRG_AMT": str(paid * 3)}
    for i in range(1, 26):
        row[f"ICD_DGNS_CD{i}"] = dx if i == 1 else ""
    row.update(extra or {})
    return row


def ip(bene, clm, admit, discharge, paid, drg, status="01", dx="I5023"):
    return inst(bene, clm, admit, discharge, paid, dx, extra={
        "CLM_DRG_CD": drg, "CLM_ADMSN_DT": admit, "NCH_BENE_DSCHRG_DT": discharge, "PTNT_DSCHRG_STUS_CD": status,
        "CLM_UTLZTN_DAY_CNT": "4", "CLM_IP_ADMSN_TYPE_CD": "1"})


def pde(pde_id, bene, date, ndc, paid, brand="G"):
    return {"PDE_ID": pde_id, "BENE_ID": bene, "SRVC_DT": date, "PRSCRBR_ID": "9999987089", "PROD_SRVC_ID": ndc,
            "QTY_DSPNSD_NUM": "30", "DAYS_SUPLY_NUM": "30", "FILL_NUM": "1", "BRND_GNRC_CD": brand,
            "CVRD_D_PLAN_PD_AMT": str(paid), "NCVRD_PLAN_PD_AMT": "0", "PTNT_PAY_AMT": "5", "LICS_AMT": "0",
            "TOT_RX_CST_AMT": str(paid + 5), "PHRMCY_SRVC_TYPE_CD": "01"}


def build_raw(root: Path) -> None:
    syn = root / "synthetic"
    full = ["3"] * 12
    ffs, ma = ["0"] * 12, ["C"] * 12
    ptd = ["Z0004"] * 12
    half = ["3"] * 6 + ["0"] * 6
    benes = pd.DataFrame([
        bene_row("B1", YEAR, full, ffs, ptd, age="70"),
        bene_row("B2", YEAR, half, ffs, [""] * 12, age="80"),
        bene_row("B2", YEAR + 1, half, ffs, [""] * 12, death="15-Mar-2021", age="81"),
        bene_row("B3", YEAR, full, ma, ptd, sex="2", age="60"),
    ])
    (syn / "beneficiary").mkdir(parents=True)
    for year, part in benes.groupby("BENE_ENROLLMT_REF_YR"):
        part.to_parquet(syn / "beneficiary" / f"{year}.parquet", index=False)

    carrier = pd.DataFrame([
        prof("B1", "C1", "10-Feb-2020", 1, "99214", 100.0, claim_paid=110.0),
        prof("B1", "C1", "10-Feb-2020", 2, "83036", 10.0, claim_paid=110.0),
        prof("B1", "C2", "10-Feb-2020", 1, "99214", 100.0),          # duplicate of C1 line 1 on another claim
        prof("B1", "C3", "15-Jun-2020", 1, "99213", 80.0),           # second diabetes date -> condition flag
        prof("B2", "C4", "10-Sep-2020", 1, "99213", 70.0, dx="I10"),  # outside B2's coverage (Jan-Jun)
        prof("B2", "C5", "01-May-2021", 1, "99213", 75.0, dx="I10"),  # after B2's death
        prof("B3", "C6", "05-Mar-2020", 1, "77067", 90.0, dx="Z1231"),  # Medicare Advantage member
    ])
    _write(carrier, syn / "carrier", "CLM_FROM_DT")
    dme = pd.DataFrame([{**prof("B1", "D1", "01-Mar-2020", 1, "E0601", 50.0), "PRVDR_NPI": "1336780048",
                         "RFR_PHYSN_NPI": "9999841890"}])
    _write(dme, syn / "dme", "CLM_FROM_DT")
    _write(pd.DataFrame([
        ip("B1", "I1", "01-Apr-2020", "05-Apr-2020", 8000.0, "291"),
        ip("B1", "I2", "20-Apr-2020", "24-Apr-2020", 9000.0, "291"),   # readmission 15 days later
    ]), syn / "inpatient", "CLM_FROM_DT")
    _write(pd.DataFrame([
        inst("B1", "O1", "02-Mar-2020", "02-Mar-2020", 500.0, "R079", line=1, rev="0450", hcpcs="99284"),
        inst("B1", "O1", "02-Mar-2020", "02-Mar-2020", 500.0, "R079", line=2, rev="0001"),
    ]), syn / "outpatient", "CLM_FROM_DT")
    _write(pd.DataFrame([ip("B1", "S1", "25-Apr-2020", "10-May-2020", 6000.0, "")]), syn / "snf", "CLM_FROM_DT")
    _write(pd.DataFrame([inst("B1", "H1", "15-May-2020", "30-May-2020", 1200.0, "I5023")]), syn / "hha", "CLM_FROM_DT")
    _write(pd.DataFrame([inst("B2", "P1", "01-Feb-2020", "28-Feb-2020", 3000.0, "C3490")]), syn / "hospice",
           "CLM_FROM_DT")
    _write(pd.DataFrame([
        pde("R1", "B1", "15-Feb-2020", "68115025030", 20.0),            # statin
        pde("R2", "B1", "15-Mar-2020", "00002143380", 400.0, brand="B"),  # insulin, brand
        pde("R3", "B3", "15-Mar-2020", "99999999999", 10.0),            # NDC not in directory
    ]), syn / "pde", "SRVC_DT")

    bench = root / "benchmarks"
    bench.mkdir()
    pd.DataFrame([{"hcpcs": c, "hcpcs_desc": f"Visit {c}", "drug_ind": "N", "place_of_service": "O",
                   "providers": 1000, "benes": 1000, "services": 1000.0, "avg_submitted": 200.0,
                   "avg_allowed": p * 1.25, "avg_paid": p, "puf_year": 2024}
                  for c, p in [("99211", 20.0), ("99212", 45.0), ("99213", 75.0), ("99214", 110.0),
                               ("99215", 150.0), ("83036", 9.0), ("77067", 95.0), ("E0601", 45.0)]]
                 ).to_parquet(bench / "hcpcs_national.parquet", index=False)
    rows = []
    # 40 internal-medicine providers with a typical mix, plus one who bills mostly level 5.
    for i in range(40):
        for code, n in [("99212", 20), ("99213", 120), ("99214", 140), ("99215", 20 + i % 5)]:
            rows.append({"provider_key": f"P{i:010x}", "specialty": "Internal Medicine", "state": "CA",
                         "entity_type": "I", "hcpcs": code, "services": float(n), "benes": n, "paid": n * 100.0,
                         "puf_year": 2024})
    for code, n in [("99213", 40), ("99214", 60), ("99215", 200)]:
        rows.append({"provider_key": "Pffffffffff", "specialty": "Internal Medicine", "state": "NV",
                     "entity_type": "I", "hcpcs": code, "services": float(n), "benes": n, "paid": n * 100.0,
                     "puf_year": 2024})
    pd.DataFrame(rows).to_parquet(bench / "em_by_provider.parquet", index=False)
    pd.DataFrame([
        {"ndc11": "68115025030", "brand_name": "Atorvastatin", "generic_name": "atorvastatin calcium",
         "dosage_form": "TABLET", "pharm_classes": "HMG-CoA Reductase Inhibitor [EPC],Hydroxymethylglutaryl-CoA Reductase Inhibitors [MoA]",
         "marketing_category": "ANDA"},
        {"ndc11": "00002143380", "brand_name": "Humalog", "generic_name": "insulin lispro",
         "dosage_form": "INJECTION", "pharm_classes": "Insulin Analog [EPC],Insulin [CS]", "marketing_category": "BLA"},
    ]).to_parquet(bench / "ndc_directory.parquet", index=False)
    pd.DataFrame([{"drg": "291", "drg_desc": "HEART FAILURE AND SHOCK WITH MCC", "discharges": 100000,
                   "avg_medicare_paid": 9500.0, "hospitals": 3000, "puf_year": 2024}]
                 ).to_parquet(bench / "drg_national.parquet", index=False)


@pytest.fixture()
def raw(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAIMLENS_FIRST_YEAR", "2020")
    monkeypatch.setenv("CLAIMLENS_LAST_YEAR", "2021")
    build_raw(tmp_path)
    return tmp_path
