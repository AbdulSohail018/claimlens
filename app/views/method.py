import plotly.graph_objects as go
import streamlit as st

from lib import INK, MUTED, RED, has_data, headline, meta, no_data, note, q, setup_page, show

setup_page()
if not has_data():
    no_data()

m = meta()
headline("Method and data", "How ClaimLens is built",
         "A monthly GitHub Actions pipeline downloads every source, lands it as parquet, rebuilds a DuckDB warehouse "
         "from SQL models, and publishes these marts only if every data test passes.")

st.graphviz_chart(f"""
digraph {{
  rankdir=LR; bgcolor="transparent"; nodesep=0.25;
  node [shape=box, style="filled", fillcolor="#FFFFFF", color="{RED}", fontname="Public Sans", fontsize=11, penwidth=1.2];
  edge [color="{MUTED}"];
  syn [label="CMS synthetic Medicare claims\\n8 claim files + 11 years of enrollment\\n(RIF format, no real patients)"];
  puf [label="CMS public use files, 2024\\nphysician services, inpatient DRGs\\n(real, providers hashed at ingest)"];
  fda [label="FDA NDC directory\\ndrug names and classes"];
  raw [label="Raw parquet\\n(all text, as delivered)"];
  stg [label="Staging\\neligibility spine, claims,\\nlines, diagnoses, fills"];
  mart [label="Marts\\nPMPM, utilization, quality,\\nconditions, pharmacy, integrity"];
  test [label="Data tests\\nfailures block the publish", fillcolor="#F6DCD8"];
  app [label="ClaimLens dashboard", fillcolor="{INK}", fontcolor="#FFFFFF", color="{INK}"];
  syn -> raw; puf -> raw; fda -> raw; raw -> stg -> mart -> app; mart -> test;
}}
""")

left, right = st.columns(2, gap="large")
with left:
    st.markdown("## Data loaded")
    rows = m.get("rows", {})
    syn = rows.get("synthetic", {})
    bench = rows.get("benchmarks", {})
    loaded = [
        ("Beneficiary-years (enrollment)", sum(v for k, v in syn.items() if k.startswith("beneficiary"))),
        ("Professional claim lines", syn.get("carrier")),
        ("Outpatient revenue-center lines", syn.get("outpatient")),
        ("Inpatient revenue-center lines", syn.get("inpatient")),
        ("Skilled nursing, home health, hospice lines",
         sum(syn.get(k, 0) or 0 for k in ("snf", "hha", "hospice"))),
        ("DME lines", syn.get("dme")),
        ("Part D prescription fills", syn.get("pde")),
        ("Real 2024 provider × visit-level rows", bench.get("em_by_provider_rows")),
        ("Real 2024 national HCPCS benchmarks", bench.get("hcpcs_national")),
        ("Real 2024 MS-DRG benchmarks", bench.get("drg_national")),
        ("FDA NDC package codes", bench.get("ndc_directory")),
    ]
    st.dataframe([{"Dataset": k, "Rows": v} for k, v in loaded], hide_index=True, width="stretch",
                 column_config={"Rows": st.column_config.NumberColumn(format="%d")})
    if m.get("built_at"):
        st.caption(f"Ingested {m.get('ingested_at', '?')[:10]}, built {m['built_at'][:10]}. "
                   f"All {m.get('tests_passed', '?')} data tests passed on this build.")
with right:
    st.markdown("## How real are the synthetic dollars?")
    cal = q("SELECT * FROM mart_price_calibration ORDER BY lines DESC LIMIT 25")
    if cal.empty:
        st.info("No codes with enough volume to compare.")
    else:
        fig = go.Figure(go.Scatter(
            x=cal.medicare_paid_2024, y=cal.synthetic_paid_per_unit, mode="markers",
            marker=dict(size=(cal.lines / cal.lines.max()) ** 0.5 * 30 + 6, color="rgba(61,110,168,0.45)",
                        line=dict(color=INK, width=1)),
            text=cal.hcpcs, customdata=cal.hcpcs_desc,
            hovertemplate="<b>%{text}</b> %{customdata}<br>Synthetic $%{y:,.2f} vs real $%{x:,.2f}<extra></extra>"))
        hi = float(max(cal.medicare_paid_2024.max(), cal.synthetic_paid_per_unit.max()))
        fig.add_trace(go.Scatter(x=[0.5, hi], y=[0.5, hi], mode="lines", line=dict(color=RED, dash="dot"),
                                 hoverinfo="skip", showlegend=False))
        fig.update_layout(xaxis=dict(type="log", title="Real Medicare average paid, 2024", tickprefix="$"),
                          yaxis=dict(type="log", title="Synthetic median paid", tickprefix="$"), showlegend=False)
        show(fig, 380)
        within = ((cal.ratio > 0.5) & (cal.ratio < 2)).mean()
        note(f"The 25 most common professional codes. {within:.0%} land within a factor of two of what Medicare "
             "really paid in 2024 (the dotted line is a perfect match). CMS warns the synthetic files have limited "
             "inferential value, so dollar figures here show method, not real-world costs.")

st.markdown("## Definitions")
st.markdown("""
- **Member month**: a month in which the beneficiary had both Part A and Part B fee-for-service coverage (buy-in code 3 or C, no Medicare Advantage) and was alive. Part D months are counted separately for pharmacy.
- **PMPM**: paid claims divided by member months. Claims for uncovered months are excluded and reported as integrity findings.
- **Per 1,000**: events divided by member-years (member months / 12), times 1,000.
- **Readmission**: an acute inpatient admission 1 to 30 days after an index discharge. Index stays exclude deaths, transfers and discharges against medical advice. Planned readmissions are not removed.
- **Chronic conditions**: eleven ICD-10 code groups, flagged with one facility claim or two other claims on different dates.
- **Generic dispensing rate**: generic fills divided by fills with a known brand or generic indicator.
- **E/M outliers**: providers whose share of level-5 established-patient visits (99215) is above the overdispersion-adjusted 99.8% funnel limit for their specialty. Payment above peer mix prices the provider's visits at 2024 national rates under their own mix and under the specialty mix.
""")
st.caption("Data: CMS (data.cms.gov) and FDA (accessdata.fda.gov). "
           "ClaimLens is an independent portfolio project, not affiliated with CMS.")
