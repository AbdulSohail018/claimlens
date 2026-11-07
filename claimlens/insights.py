"""Write INSIGHTS.md from the published marts:  python -m claimlens.insights"""
from __future__ import annotations

from datetime import datetime, timezone

import duckdb

from claimlens.config import MARTS_DIR, ROOT


def _df(con, sql):
    return con.execute(sql).df()


def generate() -> str:
    con = duckdb.connect()
    for p in sorted(MARTS_DIR.glob("mart_*.parquet")):
        con.execute(f"CREATE VIEW {p.stem} AS SELECT * FROM read_parquet('{p.as_posix()}')")

    enr = _df(con, "SELECT * FROM mart_enrollment ORDER BY year")
    peak = enr.medical_member_months.max()
    years = enr[enr.medical_member_months >= 0.5 * peak].year.tolist()
    year = int(max(years))
    lines = [f"# ClaimLens insights: plan year {year}", "",
             f"_Generated {datetime.now(timezone.utc):%Y-%m-%d} from the published marts. Member-level figures use "
             "CMS synthetic claims (no real patients) and illustrate method, not real-world costs. Provider "
             "benchmarks use real 2024 Medicare data with providers anonymised._", ""]

    pm = _df(con, f"SELECT * FROM mart_pmpm WHERE year = {year}")
    e = enr[enr.year == year].iloc[0]
    med_pmpm = pm[pm.setting != "Pharmacy"].paid.sum() / e.medical_member_months
    top = pm[pm.setting != "Pharmacy"].sort_values("paid", ascending=False).iloc[0]
    conc = _df(con, f"SELECT * FROM mart_cost_concentration WHERE year = {year} AND top_pct_of_members IN (1, 5, 20)")
    share = dict(zip(conc.top_pct_of_members, conc.cumulative_share_of_spend, strict=False))
    lines += ["## Cost", "",
              f"- {int(e.medical_members):,} fee-for-service members; medical PMPM ${med_pmpm:,.0f}.",
              f"- Largest setting: {top.setting} at ${top.pmpm:,.0f} PMPM.",
              f"- The costliest 1% of members drove {share.get(1, 0):.0%} of spend, the top 5% "
              f"{share.get(5, 0):.0%} and the top 20% {share.get(20, 0):.0%}.", ""]

    com = _df(con, f"SELECT * FROM mart_comorbidity WHERE year = {year}")
    if not com.empty:
        zero = com[com.conditions.astype(str) == "0"]
        most = com.iloc[-1]
        if not zero.empty and zero.pmpm.iloc[0] > 0:
            lines += ["## Chronic conditions", "",
                      f"- Members with {most.conditions} chronic conditions cost {most.pmpm / zero.pmpm.iloc[0]:.0f}x "
                      f"as much per month as members with none (${most.pmpm:,.0f} vs ${zero.pmpm.iloc[0]:,.0f}).", ""]

    u = _df(con, f"SELECT * FROM mart_utilization WHERE year = {year}").iloc[0]
    q = _df(con, f"SELECT measure, rate, measurable, data_note FROM mart_quality WHERE year = {year}")
    lines += ["## Utilization and quality", "",
              f"- {u.admits_per_1000:,.0f} admissions per 1,000 member-years, {u.emergency_admit_share:.0%} of them "
              f"emergency admissions; average stay {u.avg_length_of_stay:.1f} days; 30-day readmission rate "
              f"{u.readmit_rate:.1%}."]
    for r in q.itertuples():
        if r.measurable:
            note = r.data_note if isinstance(r.data_note, str) else ""
            lines.append(f"- {r.measure}: {r.rate:.1%}." + (f" {note}" if note else ""))
        else:
            lines.append(f"- {r.measure}: {r.data_note}")
    lines.append("")

    ph = _df(con, f"SELECT * FROM mart_pharmacy WHERE year = {year}")
    if not ph.empty:
        r = ph.iloc[0]
        lines += ["## Pharmacy", "",
                  f"- Pharmacy PMPM ${r.rx_pmpm:,.2f}; {r.fills_per_member_year:.1f} fills per member per year.",
                  f"- Generic dispensing rate {r.generic_dispensing_rate:.1%}. Real Medicare Part D runs near 90%; "
                  "the synthetic files assign brand and generic roughly evenly, a known limit of the data.", ""]

    em = _df(con, "SELECT * FROM mart_em_outlier_summary")
    if not em.empty:
        top_sp = em.sort_values("outlier_payment_above_peer_mix", ascending=False).iloc[0]
        lines += ["## Payment integrity (real 2024 Medicare data)", "",
                  f"- {int(em.high_outliers.sum()):,} of {int(em.providers.sum()):,} providers ("
                  f"{em.high_outliers.sum() / em.providers.sum():.1%}) bill level-5 office visits above the "
                  "overdispersion-adjusted 99.8% funnel limit for their specialty.",
                  f"- Their visits were paid ${em.outlier_payment_above_peer_mix.sum() / 1e6:,.1f}M more than the same "
                  "visits at peer coding patterns would have been, at 2024 national rates.",
                  f"- Largest gap: {top_sp.specialty} (${top_sp.outlier_payment_above_peer_mix / 1e6:,.1f}M across "
                  f"{int(top_sp.high_outliers):,} providers).", ""]
    rules = _df(con, "SELECT * FROM mart_integrity_summary")
    if not rules.empty:
        lines += ["## Claim rule checks (synthetic claims)", ""]
        lines += [f"- {r.rule}: {int(r.findings):,} findings, ${r.amount_at_risk:,.0f}." for r in rules.itertuples()]
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    text = generate()
    (ROOT / "INSIGHTS.md").write_text(text)
    print(text)


if __name__ == "__main__":
    main()
