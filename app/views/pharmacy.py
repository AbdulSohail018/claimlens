import plotly.graph_objects as go
import streamlit as st

from lib import INK, RED, fields, has_data, headline, money, no_data, note, num, pct, q, setup_page, show

year = setup_page()
if not has_data():
    no_data()

ph = q("SELECT * FROM mart_pharmacy ORDER BY year")
r = ph[ph.year == year].iloc[0]
drugs = q(f"SELECT * FROM mart_top_drugs WHERE year = {year} ORDER BY plan_paid DESC")
named = drugs[drugs.drug != "NDC not in FDA directory"]
top = named.iloc[0] if not named.empty else None

headline(f"Plan year {year} · Part D pharmacy",
         f"{pct(r.generic_dispensing_rate, 0)} of prescriptions were generics, but brand drugs took "
         f"{pct(r.brand_share_of_cost, 0)} of plan spending",
         (f"The single costliest drug was {top.drug} at {money(top.plan_paid)} for {num(top.members)} members."
          if top is not None else None))
fields([
    ("Pharmacy PMPM", money(r.rx_pmpm, 2), None),
    ("Fills per member per year", f"{r.fills_per_member_year:.1f}", None),
    ("Average cost per fill", money(r.avg_cost_per_fill, 2), None),
    ("Generic dispensing rate", pct(r.generic_dispensing_rate), None),
    ("Member cost share", pct(r.member_cost_share), "of total drug cost"),
    ("NDCs matched to FDA directory", pct(r.ndc_match_rate), "of fills"),
])

left, right = st.columns([1, 1.25], gap="large")
with left:
    fig = go.Figure()
    fig.add_trace(go.Bar(x=ph.year, y=ph.rx_pmpm, marker_color=[RED if y == year else INK for y in ph.year],
                         hovertemplate="%{x}: $%{y:,.2f} PMPM<extra></extra>", name="PMPM"))
    fig.add_trace(go.Scatter(x=ph.year, y=ph.generic_dispensing_rate, yaxis="y2", mode="lines+markers",
                             line=dict(color="#3F9C88", width=2.5), name="Generic dispensing rate",
                             hovertemplate="%{x}: %{y:.1%} generic<extra></extra>"))
    fig.update_layout(title="Pharmacy PMPM and generic dispensing rate", xaxis=dict(dtick=1),
                      yaxis=dict(tickprefix="$", title=None),
                      yaxis2=dict(overlaying="y", side="right", tickformat=".0%", range=[0, 1], showgrid=False),
                      bargap=0.3)
    show(fig, 420)
with right:
    t = named.head(15).iloc[::-1]
    fig = go.Figure(go.Bar(y=t.drug.str.title(), x=t.plan_paid, orientation="h",
                           marker_color=[RED if b > 0.5 else INK for b in t.brand_share],
                           customdata=t[["fills", "members", "drug_class"]].values,
                           hovertemplate="<b>%{y}</b><br>$%{x:,.0f} plan paid<br>%{customdata[0]:,} fills, "
                                         "%{customdata[1]:,} members<br>%{customdata[2]}<extra></extra>"))
    fig.update_layout(title="Costliest drugs (red = mostly dispensed as brand)", xaxis=dict(tickprefix="$"), bargap=0.25)
    show(fig, 420)

note("Drug names and classes come from the FDA National Drug Code Directory, matched on the 11-digit NDC. "
     "Synthetic claims include some NDCs that are not in the current directory (discontinued products or synthetic "
     "codes); those are grouped as unmatched rather than dropped, so totals still reconcile.")

st.markdown("## Spend by drug class")
cls = (drugs.groupby("drug_class", as_index=False).agg(plan_paid=("plan_paid", "sum"), fills=("fills", "sum"))
       .sort_values("plan_paid", ascending=False).head(15))
st.dataframe(cls, hide_index=True, width="stretch",
             column_config={"drug_class": st.column_config.TextColumn("Drug class (FDA established pharmacologic class)"),
                            "plan_paid": st.column_config.NumberColumn("Plan paid", format="$%,.0f"),
                            "fills": st.column_config.NumberColumn("Fills", format="%d")})
