"""DuckDB claims warehouse: raw parquet → staging → marts, plus data-quality tests.

    python -m claimlens.warehouse                    # build and print row counts
    python -m claimlens.warehouse --test             # build, then run sql/tests (exit 1 on any failure)
    python -m claimlens.warehouse --test --export    # ...and publish marts to data/marts for the dashboard
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import duckdb

from claimlens.config import MARTS_DIR, RAW_DIR, SQL_DIR, year_range

CLAIM_FILES = ["carrier", "outpatient", "inpatient", "snf", "hha", "hospice", "dme"]


def _register_raw(con: duckdb.DuckDBPyConnection, raw: Path) -> None:
    def view(name: str, pattern: str) -> None:
        files = sorted(raw.glob(pattern))
        if not files:
            raise FileNotFoundError(f"no raw files for {name} ({raw / pattern}); run python -m claimlens.ingest")
        paths = ", ".join(f"'{p.as_posix()}'" for p in files)
        con.execute(f"CREATE OR REPLACE VIEW {name} AS SELECT * FROM read_parquet([{paths}], "
                    f"union_by_name=true, hive_partitioning=true)")

    view("raw_beneficiary", "synthetic/beneficiary/*.parquet")
    for name in CLAIM_FILES + ["pde"]:
        view(f"raw_{name}", f"synthetic/{name}/**/*.parquet")
    view("raw_hcpcs_national", "benchmarks/hcpcs_national.parquet")
    view("raw_em_by_provider", "benchmarks/em_by_provider.parquet")
    view("raw_ndc_directory", "benchmarks/ndc_directory.parquet")
    view("raw_drg_national", "benchmarks/drg_national.parquet")


def _render(sql: str) -> str:
    first, last = year_range()
    return sql.replace("{{first_year}}", str(first)).replace("{{last_year}}", str(last))


def _run_sql_dir(con: duckdb.DuckDBPyConnection, folder: Path) -> list[str]:
    built = []
    for path in sorted(folder.glob("*.sql")):
        name = re.sub(r"^\d+_", "", path.stem)
        try:
            con.execute(f"CREATE OR REPLACE TABLE {name} AS {_render(path.read_text())}")
        except duckdb.Error as exc:
            raise RuntimeError(f"model {path.name} failed: {exc}") from exc
        built.append(name)
    return built


def build(raw: Path | None = None, db_path: str = ":memory:") -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(db_path)
    _register_raw(con, raw or RAW_DIR)
    # RIF files store everything as text: dates like 25-Mar-2015, blanks for missing values.
    con.execute("CREATE OR REPLACE MACRO cms_date(s) AS CAST(try_strptime(nullif(trim(s), ''), '%d-%b-%Y') AS DATE)")
    con.execute("CREATE OR REPLACE MACRO num(s) AS try_cast(nullif(trim(s), '') AS DOUBLE)")
    con.execute("CREATE OR REPLACE MACRO code(s) AS nullif(upper(trim(s)), '')")
    _run_sql_dir(con, SQL_DIR / "staging")
    _run_sql_dir(con, SQL_DIR / "marts")
    return con


def run_tests(con: duckdb.DuckDBPyConnection, verbose: bool = True) -> list[tuple[str, int]]:
    """Each test returns the rows that break a rule. Zero rows = pass."""
    failures = []
    for path in sorted((SQL_DIR / "tests").glob("*.sql")):
        rows = con.execute(_render(path.read_text())).fetchall()
        if verbose:
            print(f"  {'PASS' if not rows else f'FAIL ({len(rows)})':<12} {path.stem}")
            if rows:
                print(f"      e.g. {rows[:3]}")
        if rows:
            failures.append((path.stem, len(rows)))
    return failures


def export_marts(con: duckdb.DuckDBPyConnection, out: Path | None = None) -> dict[str, int]:
    out = out or MARTS_DIR
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("*.parquet"):
        old.unlink()
    marts = [r[0] for r in con.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_name LIKE 'mart_%' ORDER BY 1").fetchall()]
    counts = {}
    for name in marts:
        con.execute(f"COPY {name} TO '{out / name}.parquet' (FORMAT parquet, COMPRESSION zstd)")
        counts[name] = con.execute(f"SELECT count(*) FROM {name}").fetchone()[0]
    meta_path = RAW_DIR / "ingest_meta.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    meta.update({"built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "marts": counts,
                 "tests_passed": len(list((SQL_DIR / "tests").glob("*.sql")))})
    (out / "meta.json").write_text(json.dumps(meta, indent=2))
    return counts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true")
    parser.add_argument("--export", action="store_true")
    parser.add_argument("--db", default=":memory:")
    args = parser.parse_args()

    con = build(db_path=args.db)
    for (name,) in con.execute("SELECT table_name FROM information_schema.tables "
                               "WHERE table_name LIKE 'stg_%' OR table_name LIKE 'mart_%' ORDER BY 1").fetchall():
        print(f"  {name:<36} {con.execute(f'SELECT count(*) FROM {name}').fetchone()[0]:>12,}")
    if args.test:
        print("\nData-quality tests:")
        if run_tests(con):
            sys.exit(1)
    if args.export:
        export_marts(con)
        print(f"\nExported marts to {MARTS_DIR}")


if __name__ == "__main__":
    main()
