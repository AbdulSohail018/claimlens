"""Every model builds on the fixture, every data test passes, and every rule finds what it should."""
import io
from contextlib import redirect_stdout

import pytest

from claimlens import warehouse


@pytest.fixture()
def con(raw):
    return warehouse.build(raw)


def q(con, sql):
    return con.execute(sql).fetchall()


def test_all_data_tests_pass(con):
    with redirect_stdout(io.StringIO()):
        assert warehouse.run_tests(con) == []


def test_eligibility_spine(con):
    # B1: 12 FFS months; B2: 6 months; B3 is Medicare Advantage, so 0 medical months.
    rows = dict(q(con, "SELECT bene_id, medical_months FROM mart_member_year WHERE year = 2020"))
    assert rows == {"B1": 12, "B2": 6}
    assert q(con, "SELECT medical_member_months, rx_member_months FROM mart_enrollment WHERE year = 2020") == [(18, 24)]


def test_pmpm_excludes_ineligible_claims(con):
    paid = dict(q(con, "SELECT setting, paid FROM mart_pmpm WHERE year = 2020"))
    # Professional: B1's 100 + 10 + 100 + 80; B2's September claim is outside coverage; B3 is Medicare Advantage.
    assert paid["Professional"] == pytest.approx(290.0)
    assert paid["Inpatient"] == pytest.approx(17000.0)
    pmpm = dict(q(con, "SELECT setting, pmpm FROM mart_pmpm WHERE year = 2020"))
    assert pmpm["Inpatient"] == pytest.approx(17000.0 / 18)


def test_conditions_need_two_dates_or_a_facility_claim(con):
    conds = set(q(con, "SELECT bene_id, condition FROM int_conditions WHERE year = 2020"))
    assert ("B1", "Diabetes") in conds              # two professional claims on different dates
    assert ("B1", "Heart failure") in conds         # inpatient claim
    assert ("B2", "Hypertension") not in conds      # only one professional claim (and it is outside coverage)


def test_readmission_and_utilization(con):
    stays = q(con, "SELECT claim_id, is_index, readmitted_30d FROM int_admissions ORDER BY claim_id")
    assert stays == [("I1", True, True), ("I2", True, False)]
    util = q(con, "SELECT admits, er_visits, readmit_rate FROM mart_utilization WHERE year = 2020")[0]
    assert util == (2, 1, 0.5)


def test_quality_measures(con):
    rates = dict(q(con, "SELECT measure, rate FROM mart_quality WHERE year = 2020"))
    assert rates["Diabetes: HbA1c testing"] == 1.0
    assert rates["Statin use in persons with diabetes"] == 1.0
    assert rates["30-day all-cause readmissions"] == 0.5


def test_integrity_rules(con):
    found = {r[0]: r[1] for r in q(con, "SELECT rule, findings FROM mart_integrity_summary")}
    assert found["Duplicate professional line"] == 1
    assert found["Service after date of death"] == 1
    assert found["Service outside covered months"] >= 1


def test_pharmacy(con):
    gdr, match = q(con, "SELECT generic_dispensing_rate, ndc_match_rate FROM mart_pharmacy WHERE year = 2020")[0]
    assert gdr == pytest.approx(2 / 3)
    assert match == pytest.approx(2 / 3)


def test_em_funnel_flags_the_heavy_level5_biller(con):
    flagged = q(con, "SELECT provider_key FROM mart_em_funnel WHERE high_outlier")
    assert flagged == [("Pffffffffff",)]
    excess = q(con, "SELECT payment_above_peer_mix FROM mart_em_funnel WHERE provider_key = 'Pffffffffff'")[0][0]
    assert excess > 0


def test_export_marts(con, tmp_path):
    counts = warehouse.export_marts(con, tmp_path / "marts")
    assert "mart_pmpm" in counts and (tmp_path / "marts" / "mart_pmpm.parquet").exists()
    assert not any(name.startswith(("int_", "stg_")) for name in counts)
