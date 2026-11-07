import plotly.graph_objects as go
import streamlit as st

from lib import INK, MUTED, RED, SETTING_COLOURS, has_data, headline, money, no_data, note, pct, q, setup_page, show

year = setup_page()
if not has_data():
    no_data()

cond = q(f"SELECT * FROM mart_conditions WHERE year = {year} ORDER BY members DESC")
comorb = q(f"SELECT * FROM mart_comorbidity WHERE year = {year}")
order = ["0", "1", "2", "3", "4", "5", "6+"]
comorb["conditions"] = comorb.conditions.astype(str)
comorb = comorb.set_index("conditions").reindex([o for o in order if o in set(comorb.conditions)]).reset_index()

base = comorb[comorb.conditions == "0"].pmpm
top = comorb.iloc[-1]
mult = top.pmpm / float(base.iloc[0]) if not base.empty and float(base.iloc[0]) > 0 else None
headline(
    f"Plan year {year} · cost drivers",
    f"Members with {top.conditions} chronic conditions cost {mult:.0f}× as much as members with none"
    if mult else "Chronic conditions drive cost",
    "Total cost per member per month (medical plus pharmacy), by how many of eleven tracked chronic conditions a "
    "member has. Conditions are found from diagnosis codes on claims.",
)

left, right = st.columns([1, 1.2], gap="large")
with left:
    fig = go.Figure(go.Bar(
        x=comorb.conditions, y=comorb.pmpm, marker_color=[INK] * (len(comorb) - 1) + [RED],
        text=[money(v) for v in comorb.pmpm], textposition="outside",
        customdata=comorb.members, hovertemplate="%{x} conditions: $%{y:,.0f} PMPM, %{customdata:,} members<extra></extra>",
    ))
    fig.update_layout(title="Total PMPM by number of chronic conditions",
                      xaxis=dict(title="Chronic conditions", type="category"),
                      yaxis=dict(tickprefix="$", title=None), bargap=0.3)
    show(fig, 420)

with right:
    c = cond.sort_values("prevalence").reset_index(drop=True)
    # Alternate label positions so neighbouring bubbles don't print on top of each other.
    positions = ["top center", "bottom center", "middle right", "middle left"]
    fig = go.Figure(go.Scatter(
        x=c.prevalence, y=c.pmpm_with_condition, mode="markers+text",
        # Label the six most common conditions; rarer ones cluster near zero and are named on hover.
        text=[name if rank < 6 else "" for name, rank in zip(c.condition, c.members.rank(ascending=False) - 1, strict=False)],
        hovertext=c.condition,
        textposition=[positions[i % len(positions)] for i in range(len(c))],
        textfont=dict(size=11, color=INK),
        marker=dict(size=(c.members / c.members.max()) ** 0.5 * 46 + 8, color="rgba(61,110,168,0.35)",
                    line=dict(color=INK, width=1)),
        customdata=c[["members", "avg_conditions"]].values,
        hovertemplate="<b>%{hovertext}</b><br>%{x:.1%} of members, $%{y:,.0f} PMPM<br>"
                      "%{customdata[0]:,} members, %{customdata[1]:.1f} conditions on average<extra></extra>",
    ))
    fig.update_layout(title="How common, and how costly", xaxis=dict(title="Share of members", tickformat=".0%"),
                      yaxis=dict(title="PMPM for members with the condition", tickprefix="$"))
    show(fig, 420)
note("Condition rule (in the style of the CMS Chronic Conditions Warehouse): at least one inpatient, skilled nursing or "
     "home health claim with a qualifying ICD-10 code, or two other claims on different dates. Members usually have "
     "several conditions, so condition costs overlap and do not add up to total spend.")

# ---- Diagnosis chapters ------------------------------------------------------------------------------
st.markdown("## Where the money goes, by diagnosis")
dx = q(f"SELECT chapter, setting, sum(paid) AS paid FROM mart_dx_chapters WHERE year = {year} GROUP BY ALL")
totals = dx.groupby("chapter").paid.sum().sort_values()
dx = dx[dx.chapter.isin(totals.tail(12).index)]
fig = go.Figure()
for setting, colour in SETTING_COLOURS.items():
    d = dx[dx.setting == setting].set_index("chapter").reindex(totals.tail(12).index)
    if d.paid.notna().any():
        fig.add_trace(go.Bar(y=d.index, x=d.paid, name=setting, orientation="h", marker_color=colour,
                             hovertemplate=f"{setting}: %{{x:$,.0f}}<extra>%{{y}}</extra>"))
fig.update_layout(barmode="stack", title="Paid claims by ICD-10 chapter of the principal diagnosis (top 12)",
                  xaxis=dict(tickprefix="$", title=None), bargap=0.25)
show(fig, 470)

# ---- DRGs ---------------------------------------------------------------------------------------------
st.markdown("## Costliest hospital stays")
drg = q("SELECT * FROM mart_drgs ORDER BY paid DESC LIMIT 15")
if drg.empty:
    st.info("No DRG-coded inpatient stays.")
else:
    t = drg.assign(desc=lambda d: d.drg_desc.str.capitalize().fillna("Not in the 2024 CMS file (code retired or renumbered)"))
    st.dataframe(
        t[["drg", "desc", "stays", "paid", "avg_paid", "national_avg_paid_2024", "avg_los", "readmit_rate"]],
        hide_index=True, width="stretch",
        column_config={
            "drg": "MS-DRG", "desc": st.column_config.TextColumn("Description", width="large"),
            "stays": st.column_config.NumberColumn("Stays", format="localized"),
            "paid": st.column_config.NumberColumn("Total paid", format="$%,.0f"),
            "avg_paid": st.column_config.NumberColumn("Avg paid per stay", format="$%,.0f"),
            "national_avg_paid_2024": st.column_config.NumberColumn("Real Medicare avg, 2024", format="$%,.0f"),
            "avg_los": st.column_config.NumberColumn("Avg days", format="%.1f"),
            "readmit_rate": st.column_config.NumberColumn("Readmitted in 30 days", format="percent"),
        },
    )
    note("All synthetic years combined. The 2024 column is the real national average Medicare payment for the same "
         "DRG, from the CMS Inpatient Hospitals public use file, as a reality check on the synthetic payments.")
_ = (MUTED, pct)
