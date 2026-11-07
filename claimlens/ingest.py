"""Download every source and land it as parquet in data/raw.

    python -m claimlens.ingest

Synthetic claim files are stored as text (all VARCHAR), exactly as delivered, partitioned by service year.
Typing and cleaning happen in the SQL staging layer, so nothing is lost or silently coerced at ingest.
The real CMS benchmark files are large (the provider file is 3.2 GB), so they are reduced at ingest to what
the analysis needs. Provider names and addresses are never stored.
"""
from __future__ import annotations

import hashlib
import json
import logging
import shutil
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import httpx

from claimlens import sources
from claimlens.config import RAW_DIR

log = logging.getLogger(__name__)


def download(url: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    log.info("downloading %s", url)
    tmp = dest.with_suffix(dest.suffix + ".part")
    with httpx.stream("GET", url, timeout=600, follow_redirects=True,
                      headers={"User-Agent": "claimlens-analytics/1.0"}) as r:
        r.raise_for_status()
        with tmp.open("wb") as f:
            for chunk in r.iter_bytes(1 << 20):
                f.write(chunk)
    tmp.rename(dest)
    log.info("  %.1f MB", dest.stat().st_size / 1e6)
    return dest


def _csv_paths(path: Path, workdir: Path) -> list[Path]:
    if path.suffix.lower() != ".zip":
        return [path]
    out = workdir / path.stem
    if not out.exists():
        with zipfile.ZipFile(path) as z:
            z.extractall(out)
    return sorted(p for p in out.rglob("*") if p.suffix.lower() in {".csv", ".txt"})


def _read_pipe(paths: list[Path]) -> str:
    files = ", ".join(f"'{p.as_posix()}'" for p in paths)
    return (f"read_csv([{files}], delim='|', header=true, all_varchar=true, quote='', "
            f"union_by_name=true, ignore_errors=false)")


def ingest_synthetic(con: duckdb.DuckDBPyConnection, cache: Path, out: Path) -> dict:
    counts = {}
    bene_dir = out / "synthetic" / "beneficiary"
    bene_dir.mkdir(parents=True, exist_ok=True)
    for year, url in sources.SYNTHETIC_BENEFICIARY.items():
        src = download(url, cache / f"beneficiary_{year}.csv")
        dest = bene_dir / f"{year}.parquet"
        con.execute(f"COPY (SELECT * FROM {_read_pipe([src])}) TO '{dest}' (FORMAT parquet, COMPRESSION zstd)")
        counts[f"beneficiary_{year}"] = con.execute(f"SELECT count(*) FROM '{dest}'").fetchone()[0]

    for name, (url, date_col) in sources.SYNTHETIC_CLAIMS.items():
        src = download(url, cache / url.rsplit("/", 1)[-1].replace("%20", "_"))
        paths = _csv_paths(src, cache)
        dest = out / "synthetic" / name
        if dest.exists():
            shutil.rmtree(dest)
        # Partition by service year so no single file approaches GitHub's 100 MB limit.
        con.execute(f"""
            COPY (SELECT *, right({date_col}, 4) AS svc_year FROM {_read_pipe(paths)})
            TO '{dest}' (FORMAT parquet, COMPRESSION zstd, PARTITION_BY (svc_year))
        """)
        counts[name] = con.execute(f"SELECT count(*) FROM read_parquet('{dest}/**/*.parquet')").fetchone()[0]
        cols = [r[0] for r in con.execute(f"DESCRIBE SELECT * FROM read_parquet('{dest}/**/*.parquet')").fetchall()]
        log.info("%s: %s rows, %s columns", name, f"{counts[name]:,}", len(cols))
    return counts


def _hash_npi(column: str) -> str:
    # One-way pseudonym: lets us count and compare providers without publishing who they are.
    return f"'P' || left(sha256('claimlens:' || {column}), 10)"


def ingest_benchmarks(con: duckdb.DuckDBPyConnection, cache: Path, out: Path) -> dict:
    bench = out / "benchmarks"
    bench.mkdir(parents=True, exist_ok=True)
    counts = {}

    geo = download(sources.PUF_GEO_SERVICE, cache / "puf_geo_service.csv")
    con.execute(f"""
        COPY (
            SELECT HCPCS_Cd AS hcpcs, HCPCS_Desc AS hcpcs_desc, HCPCS_Drug_Ind AS drug_ind,
                   Place_Of_Srvc AS place_of_service,
                   CAST(Tot_Rndrng_Prvdrs AS BIGINT) AS providers, CAST(Tot_Benes AS BIGINT) AS benes,
                   CAST(Tot_Srvcs AS DOUBLE) AS services,
                   CAST(Avg_Sbmtd_Chrg AS DOUBLE) AS avg_submitted, CAST(Avg_Mdcr_Alowd_Amt AS DOUBLE) AS avg_allowed,
                   CAST(Avg_Mdcr_Pymt_Amt AS DOUBLE) AS avg_paid, {sources.PUF_YEAR} AS puf_year
            FROM read_csv('{geo}', header=true, all_varchar=true)
            WHERE Rndrng_Prvdr_Geo_Lvl = 'National'
        ) TO '{bench / "hcpcs_national.parquet"}' (FORMAT parquet, COMPRESSION zstd)
    """)
    counts["hcpcs_national"] = con.execute(f"SELECT count(*) FROM '{bench / 'hcpcs_national.parquet'}'").fetchone()[0]

    prov = download(sources.PUF_PROVIDER_SERVICE, cache / "puf_provider_service.csv")
    codes = ", ".join(f"'{c}'" for c in sources.EM_NEW + sources.EM_ESTABLISHED)
    con.execute(f"""
        COPY (
            SELECT {_hash_npi('Rndrng_NPI')} AS provider_key,
                   any_value(Rndrng_Prvdr_Type)          AS specialty,
                   any_value(Rndrng_Prvdr_State_Abrvtn)  AS state,
                   any_value(Rndrng_Prvdr_Ent_Cd)        AS entity_type,
                   HCPCS_Cd                              AS hcpcs,
                   sum(CAST(Tot_Srvcs AS DOUBLE))        AS services,
                   sum(CAST(Tot_Benes AS BIGINT))        AS benes,
                   sum(CAST(Tot_Srvcs AS DOUBLE) * CAST(Avg_Mdcr_Pymt_Amt AS DOUBLE)) AS paid,
                   {sources.PUF_YEAR}                    AS puf_year
            FROM read_csv('{prov}', header=true, all_varchar=true)
            WHERE HCPCS_Cd IN ({codes})
            GROUP BY Rndrng_NPI, HCPCS_Cd
        ) TO '{bench / "em_by_provider.parquet"}' (FORMAT parquet, COMPRESSION zstd)
    """)
    counts["em_by_provider_rows"] = con.execute(f"SELECT count(*) FROM '{bench / 'em_by_provider.parquet'}'").fetchone()[0]

    inp = download(sources.PUF_INPATIENT, cache / "puf_inpatient.csv")
    con.execute(f"""
        COPY (
            SELECT lpad(DRG_Cd, 3, '0') AS drg, any_value(DRG_Desc) AS drg_desc,
                   sum(CAST(Tot_Dschrgs AS BIGINT)) AS discharges,
                   sum(CAST(Tot_Dschrgs AS DOUBLE) * CAST(Avg_Mdcr_Pymt_Amt AS DOUBLE))
                       / sum(CAST(Tot_Dschrgs AS DOUBLE)) AS avg_medicare_paid,
                   count(DISTINCT Rndrng_Prvdr_CCN) AS hospitals, {sources.PUF_YEAR} AS puf_year
            FROM read_csv('{inp}', header=true, all_varchar=true)
            GROUP BY 1
        ) TO '{bench / "drg_national.parquet"}' (FORMAT parquet, COMPRESSION zstd)
    """)
    counts["drg_national"] = con.execute(f"SELECT count(*) FROM '{bench / 'drg_national.parquet'}'").fetchone()[0]

    ndc_zip = download(sources.FDA_NDC_ZIP, cache / "ndctext.zip")
    ndc_dir = cache / "ndctext"
    with zipfile.ZipFile(ndc_zip) as z:
        z.extractall(ndc_dir)
    product = next(ndc_dir.rglob("product.txt"))
    package = next(ndc_dir.rglob("package.txt"))
    # Convert FDA 10-digit package codes (4-4-2, 5-3-2 or 5-4-1) to the 11-digit 5-4-2 format used on claims.
    con.execute(f"""
        COPY (
            WITH pkg AS (
                SELECT PRODUCTID, NDCPACKAGECODE,
                       lpad(split_part(NDCPACKAGECODE, '-', 1), 5, '0') ||
                       lpad(split_part(NDCPACKAGECODE, '-', 2), 4, '0') ||
                       lpad(split_part(NDCPACKAGECODE, '-', 3), 2, '0') AS ndc11
                FROM read_csv('{package}', delim='\t', header=true, all_varchar=true, quote='', ignore_errors=true)
            )
            SELECT DISTINCT ON (pkg.ndc11) pkg.ndc11,
                   p.PROPRIETARYNAME AS brand_name, p.NONPROPRIETARYNAME AS generic_name,
                   p.DOSAGEFORMNAME AS dosage_form, p.PHARM_CLASSES AS pharm_classes,
                   p.MARKETINGCATEGORYNAME AS marketing_category
            FROM pkg JOIN read_csv('{product}', delim='\t', header=true, all_varchar=true, quote='', ignore_errors=true) p
              USING (PRODUCTID)
            ORDER BY pkg.ndc11
        ) TO '{bench / "ndc_directory.parquet"}' (FORMAT parquet, COMPRESSION zstd)
    """)
    counts["ndc_directory"] = con.execute(f"SELECT count(*) FROM '{bench / 'ndc_directory.parquet'}'").fetchone()[0]
    return counts


def fingerprint(folder: Path) -> str:
    h = hashlib.sha256()
    for p in sorted(folder.rglob("*.parquet")):
        h.update(p.name.encode())
        h.update(str(p.stat().st_size).encode())
    return h.hexdigest()[:12]


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    cache = Path(tempfile.gettempdir()) / "claimlens_cache"
    cache.mkdir(exist_ok=True)
    con = duckdb.connect()
    counts = {"synthetic": ingest_synthetic(con, cache, RAW_DIR), "benchmarks": ingest_benchmarks(con, cache, RAW_DIR)}
    meta = {"ingested_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "puf_year": sources.PUF_YEAR, "rows": counts, "raw_fingerprint": fingerprint(RAW_DIR)}
    (RAW_DIR / "ingest_meta.json").write_text(json.dumps(meta, indent=2))
    log.info("ingest complete: %s", json.dumps(counts))


if __name__ == "__main__":
    main()
