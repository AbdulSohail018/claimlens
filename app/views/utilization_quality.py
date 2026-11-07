import plotly.graph_objects as go
import streamlit as st

from lib import INK, MUTED, RED, fields, has_data, headline, no_data, note, num, pct, q, setup_page, show

year = setup_page()
if not has_data():
    no_data()

util = q("SELECT * FROM mart_utilization ORDER BY year")
qual = q("SELECT * FROM mart_quality ORDER BY measure, year")
u = util[util.year == year].iloc[0]
p = util[util.year == year - 1]


def vs(col, fmt):
    if p.empty or p[col].iloc[0] != p[col].iloc[0]:
        return None
    before, now = float(p[col].iloc[0]), float(u[col])
    if before == 0:
        return None
    return f"{'▲' if now > before else '▼'} from {fmt(before)} in {year - 1}"


headline(f"Plan year {year} · utilization and quality",
         f"{num(u.admits_per_1000)} hospital admissions per 1,000 members, and {pct(u.emergency_admit_share, 0)} "
         f"of them came through the emergency department",
         "Rates per 1,000 member-years are how health plans compare utilization across populations of different sizes.")
fields([
    ("Admissions per 1,000", num(u.admits_per_1000), vs("admits_per_1000", lambda v: f"{v:,.0f}")),
    ("Inpatient days per 1,000", num(u.ip_days_per_1000), None),
    ("Average length of stay", f"{u.avg_length_of_stay:.1f} days", None),
    ("Emergency admissions per 1,000", num(u.emergency_admits_per_1000),
     vs("emergency_admits_per_1000", lambda v: f"{v:,.0f}")),
    ("SNF days per 1,000", num(u.snf_days_per_1000), None),
    ("Office visits per 1,000", num(u.office_visits_per_1000), f"urgent care {num(u.urgent_care_visits_per_1000)}"),
])

left, right = st.columns(2, gap="large")
with left:
    fig = go.Figure()
    for col, name, colour in [("admits_per_1000", "All admissions", INK),
                              ("emergency_admits_per_1000", "Emergency admissions", "#3D6EA8")]:
        fig.add_trace(go.Scatter(x=util.year, y=util[col], name=name, mode="lines+markers",
                                 line=dict(color=colour, width=2.5), marker=dict(size=7),
                                 hovertemplate=f"{name} %{{x}}: %{{y:,.0f}} per 1,000<extra></extra>"))
    fig.add_vline(x=year, line=dict(color=RED, width=1, dash="dot"))
    fig.update_layout(title="Hospital admissions per 1,000 member-years", xaxis=dict(dtick=1),
                      yaxis=dict(rangemode="tozero"))
    show(fig, 380)
with right:
    fig = go.Figure(go.Scatter(x=util.year, y=util.readmit_rate, mode="lines+markers", line=dict(color=RED, width=2.5),
                               marker=dict(size=7), hovertemplate="%{x}: %{y:.1%}<extra></extra>"))
    fig.update_layout(title="30-day all-cause readmission rate", yaxis=dict(tickformat=".0%", rangemode="tozero"),
                      xaxis=dict(dtick=1))
    show(fig, 380)

st.markdown("## Quality measures")
note("Simplified versions of HEDIS and Medicare Star Ratings measures, calculated from claims alone. Real HEDIS "
     "reporting adds continuous-enrollment rules, exclusions and lookback periods; see the README for exact definitions.")
shown = qual[qual.measurable]
hidden = qual[~qual.measurable].drop_duplicates("measure")
cols = st.columns(max(len(shown.measure.unique()), 1))
for col, (measure, d) in zip(cols, shown.groupby("measure", sort=False), strict=False):
    cur = d[d.year == year]
    rate = float(cur.rate.iloc[0]) if not cur.empty else None
    better = d.better.iloc[0]
    with col:
        st.markdown(f"**{measure}**")
        dn = d.data_note.iloc[0]
        caveat = f"<br><span class='flag'>{dn}</span>" if isinstance(dn, str) and dn else ""
        st.markdown(f"<div style='font-size:2rem;font-weight:800;color:{INK}'>{pct(rate)}</div>"
                    f"<div class='note'>{d.description.iloc[0]}. "
                    f"{num(cur.numerator.iloc[0]) if rate is not None else '–'} of "
                    f"{num(cur.denominator.iloc[0]) if rate is not None else '–'}. "
                    f"{'Higher' if better == 'higher' else 'Lower'} is better.{caveat}</div>", unsafe_allow_html=True)
        fig = go.Figure(go.Scatter(x=d.year, y=d.rate, mode="lines+markers",
                                   line=dict(color=INK if better == "higher" else RED, width=2),
                                   marker=dict(size=5), hovertemplate="%{x}: %{y:.1%}<extra></extra>"))
        fig.update_layout(margin=dict(l=4, r=4, t=8, b=4), yaxis=dict(tickformat=".0%", rangemode="tozero"),
                          xaxis=dict(dtick=2, tickfont=dict(size=10, color=MUTED)))
        show(fig, 170, key=f"quality-{measure}")
if not hidden.empty:
    st.markdown("#### Not reported")
    for r in hidden.itertuples():
        st.markdown(f"- **{r.measure}**: {r.data_note}")
