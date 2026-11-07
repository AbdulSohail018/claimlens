"""Project settings."""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.getenv("CLAIMLENS_DATA_DIR", ROOT / "data"))
RAW_DIR = Path(os.getenv("CLAIMLENS_RAW_DIR", DATA_DIR / "raw"))
MARTS_DIR = Path(os.getenv("CLAIMLENS_MARTS_DIR", DATA_DIR / "marts"))
SQL_DIR = ROOT / "sql"


def year_range() -> tuple[int, int]:
    """Analysis years. Enrollment in the synthetic files runs 2015-2025, but claims stop in early 2023,
    so the full claim years are 2015-2022. Override with CLAIMLENS_FIRST_YEAR / CLAIMLENS_LAST_YEAR."""
    return int(os.getenv("CLAIMLENS_FIRST_YEAR", "2015")), int(os.getenv("CLAIMLENS_LAST_YEAR", "2022"))
