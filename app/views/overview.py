import plotly.graph_objects as go
import streamlit as st

from lib import (
    INK,
    MUTED,
    RED,
    SETTING_COLOURS,
    SETTING_ORDER,
    fields,
    has_data,
    headline,
    money,
    no_data,
    note,
    num,
    pct,
    q,
    setup_page,
    show,
)

year = setup_page()
if not has_data():
    no_data()

pmpm = q("SELECT * FROM mart_pmpm ORDER BY year")
enr = q("SELECT * FROM mart_enrollment ORDER BY year")
util = q("SELECT * FROM mart_utilization ORDER BY year")
conc = q(f"SELECT * FROM mart_cost_concentration WHERE year = {year} ORDER BY top_pct_of_members")
years = sorted(set(pmpm.year))

y = pmpm[pmpm.year == year]
prev = pmpm[pmpm.year == year - 1]
med = y[y.setting != "Pharmacy"]
e = enr[enr.year == year].iloc[0]
u = util[util.year == year].iloc[0]
medical_pmpm = med.paid.sum() / e.medical_member_months
rx_pmpm = float(y[y.setting == "Pharmacy"].pmpm.sum())
prev_medical_pmpm = (prev[prev.setting != "Pharmacy"].paid.sum() / enr[enr.year == year - 1].medical_member_months.iloc[0]
                     if not prev.empty else None)


def share_of_spend(top_pct: int) -> float | None:
    """Share of spend held by the costliest top_pct% of members (nearest computed point at or below it)."""
    rows = conc[conc.top_pct_of_members <= top_pct]
    return float(rows.cumulative_share_of_spend.iloc[-1]) if not rows.empty else None


top5 = share_of_spend(5)
biggest = med.sort_values("paid", ascending=False).iloc[0]


def change(now, before):
    if before is None or before != before or before == 0:
        return None
    d = now / before - 1
    return f"{'▲' if d > 0 else '▼'} {abs(d):.1%} vs {year - 1}"


headline(
    f"Plan year {year} · {num(e.medical_members)} fee-for-service members",
    f"Medical claims cost {money(medical_pmpm, 0)} per member per month, and the costliest 5% of members drove "
    f"{pct(top5, 0)} of spend",
    f"{biggest.setting} care was the largest single cost, at {money(biggest.pmpm, 0)} PMPM. "
    f"Pharmacy added {money(rx_pmpm, 0)} PMPM for members with Part D.",
)

fields([
    ("Members (A+B fee-for-service)", num(e.medical_members), f"{num(e.medical_member_months)} member months"),
    ("Medical PMPM", money(medical_pmpm, 0), change(medical_pmpm, prev_medical_pmpm)),
    ("Pharmacy PMPM", money(rx_pmpm, 0), f"{num(e.rx_members)} Part D members"),
    ("Total paid", money(y.paid.sum()), "medical and pharmacy"),
    ("Admissions per 1,000", num(u.admits_per_1000, 0), f"avg stay {u.avg_length_of_stay:.1f} days"),
    ("30-day readmission rate", pct(u.readmit_rate), f"{num(u.index_stays)} index stays"),
])

left, right = st.columns([1.45, 1], gap="large")
with left:
    fig = go.Figure()
    for setting in SETTING_ORDER:
        d = pmpm[pmpm.setting == setting]
        if d.empty:
            continue
        fig.add_trace(go.Bar(x=d.year, y=d.pmpm, name=setting, marker_color=SETTING_COLOURS[setting],
                             hovertemplate=f"{setting} %{{x}}: $%{{y:,.0f}} PMPM<extra></extra>"))
    fig.add_vrect(x0=year - 0.5, x1=year + 0.5, fillcolor=RED, opacity=0.06, line_width=0)
    fig.update_layout(barmode="stack", title="PMPM by care setting", yaxis_tickprefix="$",
                      xaxis=dict(tickmode="array", tickvals=years), bargap=0.25)
    show(fig, 430)

with right:
    fig = go.Figure()
    x = [0] + conc.top_pct_of_members.tolist()
    yv = [0] + conc.cumulative_share_of_spend.tolist()
    fig.add_trace(go.Scatter(x=[0, 100], y=[0, 1], mode="lines", line=dict(color=MUTED, dash="dot", width=1),
                             hoverinfo="skip", showlegend=False))
    fig.add_trace(go.Scatter(x=x, y=yv, mode="lines", line=dict(color=INK, width=3), fill="tozeroy",
                             fillcolor="rgba(28,37,65,0.08)", showlegend=False,
                             hovertemplate="Top %{x}% of members: %{y:.0%} of spend<extra></extra>"))
    for p in (1, 5, 20):
        v = share_of_spend(p)
        if v is not None:
            fig.add_trace(go.Scatter(x=[p], y=[v], mode="markers+text", marker=dict(color=RED, size=9),
                                     text=[f"top {p}%: {v:.0%}"], textposition="middle right",
                                     textfont=dict(color=INK, size=12), showlegend=False, hoverinfo="skip"))
    fig.update_layout(title="Spend concentration", xaxis=dict(title="Costliest members (%)", range=[0, 100]),
                      yaxis=dict(title="Share of total spend", tickformat=".0%", range=[0, 1.02]))
    show(fig, 430)

note("PMPM divides paid claims by member months. Medical uses months with both Part A and Part B fee-for-service "
     "coverage; pharmacy uses Part D months. Claims for months without coverage are left out of PMPM and reported "
     "on the Payment integrity page.")

# ---- Trend table --------------------------------------------------------------------------------------
st.markdown("## Year over year")
trend = (pmpm.assign(group=lambda d: d.setting.where(d.setting == "Pharmacy", "Medical"))
         .groupby(["year", "group"]).paid.sum().unstack().reset_index()
         .merge(enr[["year", "medical_members", "medical_member_months", "rx_member_months"]], on="year")
         .merge(util[["year", "admits_per_1000", "er_visits_per_1000", "readmit_rate"]], on="year"))
trend["Medical PMPM"] = trend.Medical / trend.medical_member_months
trend["Pharmacy PMPM"] = trend.Pharmacy / trend.rx_member_months
table = trend.rename(columns={"year": "Year", "medical_members": "Members", "admits_per_1000": "Admits per 1,000",
                              "er_visits_per_1000": "ER visits per 1,000", "readmit_rate": "Readmission rate"})[
    ["Year", "Members", "Medical PMPM", "Pharmacy PMPM", "Admits per 1,000", "ER visits per 1,000", "Readmission rate"]]
st.dataframe(
    table.sort_values("Year", ascending=False), hide_index=True, width="stretch",
    column_config={"Year": st.column_config.NumberColumn(format="%d"),
                   "Members": st.column_config.NumberColumn(format="%d"),
                   "Medical PMPM": st.column_config.NumberColumn(format="$%.0f"),
                   "Pharmacy PMPM": st.column_config.NumberColumn(format="$%.0f"),
                   "Admits per 1,000": st.column_config.NumberColumn(format="%.0f"),
                   "ER visits per 1,000": st.column_config.NumberColumn(format="%.0f"),
                   "Readmission rate": st.column_config.NumberColumn(format="percent")},
)
