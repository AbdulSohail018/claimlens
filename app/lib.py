"""Shared dashboard helpers: data access, theme tokens, chart template and small components."""
from __future__ import annotations

import json
import os
from pathlib import Path

import duckdb
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
MARTS = Path(os.getenv("CLAIMLENS_MARTS_DIR", ROOT / "data" / "marts"))

# ---- Tokens ----------------------------------------------------------------------------------------
INK = "#1C2541"        # data, headlines
RED = "#C8372D"        # claim-form dropout red: structure, labels, integrity flags
RED_SOFT = "#F6DCD8"
RULE = "#E8C4BF"
MUTED = "#5B6170"
PAPER = "#FFFFFF"
GRID = "#EEF0F3"

SETTING_COLOURS = {
    "Inpatient": "#1C2541", "Outpatient": "#3D6EA8", "Professional": "#8FB3DE", "Skilled nursing": "#6B5B95",
    "Home health": "#3F9C88", "Hospice": "#A7A9AC", "DME": "#D4A93C", "Pharmacy": "#E27D4E",
}
SETTING_ORDER = list(SETTING_COLOURS)


# ---- Data ------------------------------------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def _con() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    for path in sorted(MARTS.glob("mart_*.parquet")):
        con.execute(f"CREATE VIEW {path.stem} AS SELECT * FROM read_parquet('{path.as_posix()}')")
    return con


@st.cache_data(show_spinner=False)
def q(sql: str) -> pd.DataFrame:
    return _con().execute(sql).df()


def meta() -> dict:
    path = MARTS / "meta.json"
    return json.loads(path.read_text()) if path.exists() else {}


def has_data() -> bool:
    return (MARTS / "mart_pmpm.parquet").exists()


@st.cache_data(show_spinner=False)
def analysis_years() -> list[int]:
    """Years with a full, credible membership base (at least 50% of the peak year's member months)."""
    e = q("SELECT year, medical_member_months FROM mart_enrollment ORDER BY year")
    peak = e.medical_member_months.max()
    return e[e.medical_member_months >= 0.5 * peak].year.astype(int).tolist()


# ---- Formatting -------------------------------------------------------------------------------------
def money(v: float, decimals: int = 0) -> str:
    if v is None or v != v:
        return "–"
    if abs(v) >= 1e9:
        return f"${v / 1e9:.1f}B"
    if abs(v) >= 1e6:
        return f"${v / 1e6:.1f}M"
    if abs(v) >= 1e4:
        return f"${v / 1e3:.0f}K"
    return f"${v:,.{decimals}f}"


def pct(v: float, decimals: int = 1) -> str:
    return "–" if v is None or v != v else f"{100 * v:.{decimals}f}%"


def num(v: float, decimals: int = 0) -> str:
    return "–" if v is None or v != v else f"{v:,.{decimals}f}"


# ---- Theme ------------------------------------------------------------------------------------------
CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Public+Sans:ital,wght@0,400;0,500;0,600;0,700;0,800;1,400&display=swap');
:root {{ --ink:{INK}; --red:{RED}; --red-soft:{RED_SOFT}; --rule:{RULE}; --muted:{MUTED}; }}
html, body, .stApp, .stMarkdown, p, li, label, input, button, textarea, select, [class*="css"] {{
  font-family: 'Public Sans', system-ui, sans-serif; font-variant-numeric: tabular-nums;
}}
.stApp {{ background: {PAPER}; color: var(--ink); }}
.block-container {{ padding-top: 3.6rem; max-width: 1240px; }}
h1, h2, h3 {{ font-family: 'Public Sans', sans-serif !important; color: var(--ink) !important; letter-spacing: -0.015em; }}
h2 {{ font-size: 1.35rem !important; font-weight: 700 !important; margin-top: 1.6rem !important;
      padding-top: .9rem; border-top: 1px solid var(--rule); }}
h3 {{ font-size: 1.05rem !important; font-weight: 600 !important; }}

[data-testid="stSidebar"] {{ background: #FCFAF9; border-right: 2px solid var(--red); }}
[data-testid="stSidebarNav"] a[aria-current="page"] {{ background: var(--red-soft); border-radius: 3px; }}
[data-testid="stSidebarNav"] a[aria-current="page"] span {{ color: var(--ink) !important; font-weight: 700; }}

.cl-kicker {{ color: var(--muted); font-size: .92rem; margin-bottom: .15rem; }}
.cl-headline {{ font-weight: 800; color: var(--ink); font-size: clamp(1.8rem, 3.3vw, 2.75rem); line-height: 1.08;
  letter-spacing: -0.025em; max-width: 24ch; margin: .1rem 0 .6rem; }}
.cl-sub {{ color: var(--muted); font-size: 1.04rem; max-width: 64ch; margin-bottom: 1.1rem; line-height: 1.5; }}

/* KPI fields drawn like boxes on a claim form: red hairline frame, small red field label. */
.fields {{ display: grid; grid-template-columns: repeat(var(--n), minmax(0, 1fr)); gap: 0;
  border: 1.5px solid var(--red); margin: .6rem 0 1.4rem; background: {PAPER}; }}
.field {{ padding: .5rem .8rem .65rem; border-right: 1px solid var(--rule); border-bottom: 1px solid var(--rule); }}
.field .lab {{ color: var(--red); font-size: .74rem; font-weight: 600; line-height: 1.2; }}
.field .val {{ color: var(--ink); font-size: 1.45rem; font-weight: 700; line-height: 1.15; margin-top: .25rem; }}
.field .ctx {{ color: var(--muted); font-size: .8rem; margin-top: .1rem; }}
.field .ctx.up {{ color: var(--red); }}

@media (max-width: 900px) {{ .fields {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }} }}
.note {{ color: var(--muted); font-size: .87rem; max-width: 74ch; line-height: 1.5; }}
.flag {{ color: var(--red); font-weight: 600; }}
:focus-visible {{ outline: 2px solid var(--red) !important; outline-offset: 2px; }}
</style>
"""


def setup_page(show_year: bool = True) -> int | None:
    """Apply the theme, draw the sidebar, and return the selected analysis year."""
    st.markdown(CSS, unsafe_allow_html=True)
    with st.sidebar:
        st.markdown("### ClaimLens")
        st.caption("Medicare claims analytics and payment integrity")
        year = None
        if has_data() and show_year:
            years = analysis_years()
            year = st.selectbox("Plan year", years[::-1], index=0)
        if has_data():
            m = meta()
            if m.get("built_at"):
                st.caption(f"Pipeline run {m['built_at'][:10]}")
        st.caption("Member data is CMS synthetic (no real patients). Provider benchmarks are real 2024 "
                   "Medicare public data, with providers anonymised.")
    return year


def fields(items: list[tuple[str, str, str | None]]) -> None:
    """KPI boxes: (label, value, context). Context starting with '▲' is drawn in red."""
    cells = []
    for label, value, ctx in items:
        cls = "ctx up" if ctx and ctx.startswith("▲") else "ctx"
        ctx_html = f'<div class="{cls}">{ctx}</div>' if ctx else ""
        cells.append(f'<div class="field"><div class="lab">{label}</div><div class="val">{value}</div>{ctx_html}</div>')
    st.markdown(f'<div class="fields" style="--n:{len(cells)}">{"".join(cells)}</div>', unsafe_allow_html=True)


def headline(kicker: str, text: str, sub: str | None = None) -> None:
    st.markdown(f'<div class="cl-kicker">{kicker}</div><div class="cl-headline">{text}</div>'
                + (f'<div class="cl-sub">{sub}</div>' if sub else ""), unsafe_allow_html=True)


def note(text: str) -> None:
    st.markdown(f'<p class="note">{text}</p>', unsafe_allow_html=True)


def no_data() -> None:
    st.info("No published data yet. Run `python -m claimlens.ingest` then "
            "`python -m claimlens.warehouse --test --export` to build it.")
    st.stop()


# ---- Charts -------------------------------------------------------------------------------------------
pio.templates["claimlens"] = go.layout.Template(layout=go.Layout(
    font=dict(family="Public Sans, system-ui, sans-serif", color=INK, size=13),
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor=PAPER,
    xaxis=dict(gridcolor=GRID, linecolor="#C9CED6", zeroline=False, automargin=True, ticks="outside", tickcolor="#C9CED6"),
    yaxis=dict(gridcolor=GRID, linecolor="#C9CED6", zeroline=False, automargin=True),
    margin=dict(l=8, r=16, t=44, b=8),
    hoverlabel=dict(bgcolor=INK, bordercolor=INK, font=dict(color="#FFFFFF", family="Public Sans")),
    legend=dict(orientation="h", y=-0.18, x=0, font=dict(size=12), title=None),
    title=dict(font=dict(size=15, color=INK), x=0, xanchor="left"),
    colorway=[INK, "#3D6EA8", "#8FB3DE", "#6B5B95", "#3F9C88", "#D4A93C", "#E27D4E"],
))
pio.templates.default = "claimlens"


def show(fig: go.Figure, height: int = 400, key: str | None = None) -> None:
    fig.update_layout(height=height)
    st.plotly_chart(fig, width="stretch", theme=None, config={"displayModeBar": False}, key=key)
