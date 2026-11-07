import numpy as np
import plotly.graph_objects as go
import streamlit as st

from lib import INK, MUTED, RED, fields, has_data, headline, money, no_data, note, num, pct, q, setup_page, show

setup_page()
if not has_data():
    no_data()

summary = q("SELECT * FROM mart_em_outlier_summary")
spec = q("SELECT * FROM mart_em_specialty ORDER BY visits DESC")
total_flagged = int(summary.high_outliers.sum())
total_assessed = int(summary.providers.sum())
excess = float(summary.outlier_payment_above_peer_mix.sum())

headline(
    "Payment integrity · real 2024 Medicare data",
    f"{num(total_flagged)} of {num(total_assessed)} providers bill the top office-visit level far more often "
    f"than their specialty peers",
    f"Together their visits were paid {money(excess)} more than the same visits at their peers' coding mix. "
    "That's a list for review, not proof of wrongdoing: some practices really do see sicker patients.",
)
fields([
    ("Providers assessed", num(total_assessed), "50+ established-patient visits"),
    ("High outliers", num(total_flagged), pct(total_flagged / total_assessed) + " of providers"),
    ("Paid above peer mix", money(excess), "at 2024 national rates"),
    ("Specialties compared", num(len(summary)), "30+ providers each"),
])

# ---- Funnel plot ----------------------------------------------------------------------------------------
st.markdown("## The funnel plot")
choices = summary.sort_values("providers", ascending=False).specialty.tolist()
default = choices.index("Internal Medicine") if "Internal Medicine" in choices else 0
sp = st.selectbox("Specialty", choices, index=default)
f = q(f"SELECT * FROM mart_em_funnel WHERE specialty = '{sp.replace(chr(39), chr(39) * 2)}'")
row = summary[summary.specialty == sp].iloc[0]
p0, phi = float(row.peer_share_l5), float(row.overdispersion_phi)

xs = np.geomspace(max(50, f.visits.min()), f.visits.max(), 200)
upper = np.minimum(p0 + 3.09 * np.sqrt(phi * p0 * (1 - p0) / xs), 1)
upper95 = np.minimum(p0 + 1.96 * np.sqrt(phi * p0 * (1 - p0) / xs), 1)
lower = np.maximum(p0 - 3.09 * np.sqrt(phi * p0 * (1 - p0) / xs), 0)
sample = f if len(f) <= 6000 else f[f.high_outlier].pipe(lambda o: o._append(f[~f.high_outlier].sample(6000, random_state=1)))

fig = go.Figure()
fig.add_trace(go.Scatter(x=xs, y=upper, mode="lines", line=dict(color=RED, width=1.6), name="99.8% limit"))
fig.add_trace(go.Scatter(x=xs, y=upper95, mode="lines", line=dict(color=RED, width=1, dash="dot"), name="95% limit"))
fig.add_trace(go.Scatter(x=xs, y=lower, mode="lines", line=dict(color=RED, width=1.6), showlegend=False))
fig.add_hline(y=p0, line=dict(color=INK, width=1.2), annotation_text=f"specialty average {p0:.1%}",
              annotation_position="top left", annotation_font=dict(color=INK, size=12))
normal = sample[~sample.high_outlier]
flag = sample[sample.high_outlier]
fig.add_trace(go.Scattergl(x=normal.visits, y=normal.share_l5, mode="markers", name="Within expected range",
                           marker=dict(color="rgba(28,37,65,0.28)", size=5),
                           hovertemplate="%{x:,} visits, %{y:.1%} level 5<extra></extra>"))
fig.add_trace(go.Scattergl(x=flag.visits, y=flag.share_l5, mode="markers", name="High outlier",
                           marker=dict(color=RED, size=7, line=dict(color="#FFFFFF", width=0.6)),
                           customdata=flag[["provider_key", "payment_above_peer_mix"]].values,
                           hovertemplate="Provider %{customdata[0]}<br>%{x:,} visits, %{y:.1%} level 5<br>"
                                         "$%{customdata[1]:,.0f} above peer mix<extra></extra>"))
fig.update_layout(xaxis=dict(type="log", title="Established-patient office visits in 2024 (log scale)"),
                  yaxis=dict(title="Share billed as level 5 (99215)", tickformat=".0%", range=[0, min(1, max(0.25, float(f.share_l5.quantile(0.999)) * 1.1))]),
                  legend=dict(y=-0.2))
show(fig, 520)
note(f"Each dot is one provider. The funnel narrows as volume grows because a busy practice's share is measured more "
     f"precisely. Limits are widened by an overdispersion factor (φ = {phi:.1f} for {sp}), estimated from the "
     "specialty's own spread, so ordinary practice variation isn't flagged. Providers are shown only as anonymous keys.")

# ---- Specialty table + state map ----------------------------------------------------------------------
left, right = st.columns([1.15, 1], gap="large")
with left:
    st.markdown("## By specialty")
    t = summary.sort_values("outlier_payment_above_peer_mix", ascending=False).head(20)
    st.dataframe(
        t[["specialty", "providers", "high_outliers", "outlier_share", "peer_share_l5", "outlier_median_share_l5",
           "outlier_payment_above_peer_mix"]],
        hide_index=True, width="stretch", height=480,
        column_config={"specialty": "Specialty", "providers": st.column_config.NumberColumn("Providers", format="%d"),
                       "high_outliers": st.column_config.NumberColumn("Outliers", format="%d"),
                       "outlier_share": st.column_config.NumberColumn("Outlier share", format="percent"),
                       "peer_share_l5": st.column_config.NumberColumn("Peer level-5 share", format="percent"),
                       "outlier_median_share_l5": st.column_config.NumberColumn("Outliers' level-5 share", format="percent"),
                       "outlier_payment_above_peer_mix": st.column_config.NumberColumn("Paid above peer mix", format="$%,.0f")},
    )
with right:
    st.markdown("## By state")
    states = q("SELECT * FROM mart_em_state")
    fig = go.Figure(go.Choropleth(
        locations=states.state, z=states.outlier_share, locationmode="USA-states",
        colorscale=[[0, "#FFFFFF"], [0.5, "#F2B8B1"], [1, RED]], marker_line_color="#FFFFFF",
        colorbar=dict(title=dict(text="Outlier<br>share", font=dict(size=11)), tickformat=".0%", thickness=10),
        customdata=states[["providers", "high_outliers"]].values,
        hovertemplate="<b>%{location}</b>: %{z:.1%} of providers<br>%{customdata[1]:,} of %{customdata[0]:,}<extra></extra>",
    ))
    fig.update_layout(geo=dict(scope="usa", bgcolor="rgba(0,0,0,0)", lakecolor="#FFFFFF"), margin=dict(l=0, r=0, t=10, b=0))
    show(fig, 400)
    note("States with at least 100 assessed providers.")

# ---- Synthetic claim rules ----------------------------------------------------------------------------
st.markdown("## Rule checks on the plan's own claims")
rules = q("SELECT * FROM mart_integrity_summary")
note("Deterministic edits that a claims system runs before or after payment, applied to the synthetic member claims. "
     "Findings here are excluded from PMPM.")
st.dataframe(rules, hide_index=True, width="stretch",
             column_config={"rule": "Rule", "findings": st.column_config.NumberColumn("Findings", format="%d"),
                            "members": st.column_config.NumberColumn("Members", format="%d"),
                            "amount_at_risk": st.column_config.NumberColumn("Amount at risk", format="$%,.0f"),
                            "share_of_all_paid": st.column_config.NumberColumn("Share of all paid", format="percent")})
_ = MUTED
