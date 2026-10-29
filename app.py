"""GreenProof – Greenwashing Screener (Streamlit app).

Start with:  streamlit run app.py
"""
from __future__ import annotations

import hashlib
import os
import time
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from screener import climatebert, llm
from screener.classify import CATEGORIES
from screener.naming import company_from_filename
from screener.pipeline import MODES, ReportResult, category_counts, company_summary, screen
from screener.validation import agreement, kappa_label

ROOT = Path(__file__).parent
DEMO_DIR = ROOT / "demo"

# Light and dark palettes. The first six keys mirror .streamlit/config.toml (tests/test_app.py checks it);
# "lights" are softened traffic-light shades that keep their meaning (green / yellow / red / grey).
THEMES = {
    "light": {"primary": "#3F8F5F", "bg": "#F7F8F4", "bg2": "#EDF1EA", "text": "#1F2A24", "border": "#DCE3DA",
              "sidebar": "#EEF2EB", "muted": "#5E6B63", "grid": "#E4E9E2", "card": "#FFFFFF",
              "lights": {"green": "#4E9A6A", "yellow": "#E0AC45", "red": "#C9594E", "grey": "#A3AAA5"},
              "measures": {"score": "#93AFA9", "evidence": "#3F7F5A", "overall": "#D2AE4E"}},
    "dark": {"primary": "#6CBF8C", "bg": "#141B17", "bg2": "#1E2822", "text": "#E3EAE5", "border": "#2D3A32",
             "sidebar": "#18211C", "muted": "#A3B0A8", "grid": "#26312B", "card": "#19221D",
             "lights": {"green": "#62B07F", "yellow": "#E2B24E", "red": "#E0766A", "grey": "#8D9690"},
             "measures": {"score": "#7F9C97", "evidence": "#6CBF8C", "overall": "#D9B65A"}},
}
THEME_CHOICES = {"auto": ":material/brightness_auto: Auto", "light": ":material/light_mode: Light",
                 "dark": ":material/dark_mode: Dark"}
QUADRANT_LIGHTS = {"Credible": "green", "Careful claims, thin data": "yellow", "Good data, weak claims": "yellow",
                   "Greenwashing risk": "red", "–": "grey"}
VIEWS = {"Ranking": ":material/leaderboard: Ranking", "Company detail": ":material/apartment: Company detail",
         "Validate": ":material/fact_check: Validate", "Data": ":material/table_view: Data",
         "Method": ":material/menu_book: Method"}

st.set_page_config(page_title="GreenProof – Greenwashing Screener", page_icon=":material/eco:", layout="wide")


@st.cache_data(ttl=900, show_spinner=False)
def nvidia_models(api_key: str) -> tuple[list[str], dict[str, str]]:
    return llm.nvidia_working_models(api_key)


@st.cache_resource
def _screen_cache() -> dict:
    return {}


def run_screening(pdf_bytes: bytes, company: str, mode: str, api_key: str | None, model: str | None,
                  progress=None) -> ReportResult:
    """Screen once per (file, company, mode, model) and reuse the result.

    A plain dict instead of st.cache_data, because st.cache_data would replay the live progress bar."""
    cache = _screen_cache()
    key = (hashlib.sha256(pdf_bytes).hexdigest(), company, mode, model if mode in ("ai", "nvidia") else None)
    if key not in cache:
        if len(cache) >= 50:
            cache.pop(next(iter(cache)))
        cache[key] = screen(pdf_bytes, company, mode=mode, api_key=api_key, model=model, progress=progress)
    return cache[key]


def active_theme(choice: str | None, device: str | None) -> str:
    """'light' or 'dark': the sidebar choice, or the device theme when the choice is Auto."""
    if choice in ("light", "dark"):
        return choice
    return device if device in ("light", "dark") else "light"


def base_css(p: dict) -> str:
    """Softer look for both themes: more air between blocks, card-style metrics, calm intro lines."""
    return f"""
    .block-container {{ padding-top: 2.2rem; padding-bottom: 4rem; max-width: 1200px; }}
    [data-testid="stVerticalBlock"] {{ gap: 1.1rem; }}
    h1, h2, h3 {{ letter-spacing: -0.01em; }}
    [data-testid="stMetric"] {{ background: {p['card']}; border-color: {p['border']} !important;
        border-radius: 1rem; padding: 0.9rem 1.1rem; }}
    [data-testid="stMetricLabel"] p {{ color: {p['muted']}; }}
    [data-testid="stMetricValue"] {{ overflow: hidden; text-overflow: ellipsis; }}
    .gp-sub {{ color: {p['muted']}; font-size: 1.15rem; margin: -0.6rem 0 0.4rem 0; }}
    .gp-intro {{ color: {p['muted']}; font-size: 1rem; margin: 0.2rem 0 0.2rem 0; }}
    .gp-steps {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 0.9rem; }}
    .gp-step {{ background: {p['card']}; border: 1px solid {p['border']}; border-radius: 1rem; padding: 1rem 1.1rem; }}
    .gp-step b {{ display: block; margin-bottom: 0.25rem; color: {p['text']}; }}
    .gp-step span {{ color: {p['muted']}; font-size: 0.95rem; }}
    .gp-num {{ display: inline-flex; align-items: center; justify-content: center; width: 1.8rem; height: 1.8rem;
        border-radius: 50%; background: {p['primary']}; color: {p['bg']}; font-weight: 700; margin-bottom: 0.5rem; }}
    .gp-badge {{ display: inline-block; border: 1px solid; border-radius: 999px; padding: 0.15rem 0.75rem;
        font-size: 0.9rem; font-weight: 600; }}
    .gp-chart-title {{ font-weight: 600; margin: 0 0 -0.6rem 0; }}
    div.st-key-demo_btn {{ margin-top: 0.4rem; }}
    div.st-key-demo_btn button {{ padding: 0.8rem 1.6rem; font-size: 1.05rem; }}
    div.st-key-theme_choice button {{ padding-left: 0.55rem; padding-right: 0.55rem; }}
    @media (max-width: 640px) {{
        .block-container {{ padding-left: 1rem; padding-right: 1rem; padding-top: 3.2rem; }}
        [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] [data-testid="stMetric"])
            {{ flex-flow: row wrap; gap: 0.7rem; }}
        [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] [data-testid="stMetric"]) > [data-testid="stColumn"]
            {{ flex: 1 1 calc(50% - 0.7rem) !important; min-width: calc(50% - 0.7rem) !important; width: auto !important; }}
        [data-testid="stMetric"] {{ padding: 0.7rem 0.9rem; }}
        div.st-key-demo_btn button {{ width: 100%; }}
    }}
    """


def forced_css(p: dict, theme: str) -> str:
    """Override Streamlit's colours when the switch differs from the device theme (no runtime theme API)."""
    invert = "invert(0.93) hue-rotate(180deg)"   # canvas tables can't be recoloured with CSS
    return f"""
    :root {{ color-scheme: {theme}; }}
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"], [data-testid="stBottomBlockContainer"]
        {{ background: {p['bg']} !important; color: {p['text']}; }}
    [data-testid="stSidebar"], [data-testid="stSidebar"] > div {{ background: {p['sidebar']} !important; }}
    .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp p, .stApp li, .stApp label, .stApp summary,
    .stApp [data-testid="stMarkdownContainer"], .stApp [data-testid="stMetricValue"],
    .stApp [data-testid="stHeader"] button, .stApp [data-testid="stWidgetLabel"] {{ color: {p['text']}; }}
    .stApp [data-testid="stCaptionContainer"], .stApp small {{ color: {p['muted']} !important; }}
    .stApp table, .stApp th, .stApp td {{ color: {p['text']}; border-color: {p['border']} !important; }}
    .stApp code {{ background: {p['bg2']}; color: {p['text']}; }}
    .stApp [data-baseweb="input"], .stApp [data-baseweb="input"] > div, .stApp [data-baseweb="select"] > div,
    .stApp [data-baseweb="textarea"], .stApp input, .stApp textarea
        {{ background: {p['bg2']} !important; color: {p['text']} !important; border-color: {p['border']} !important; }}
    .stApp .stSelectbox div:not([data-testid]), .stApp .stMultiSelect div:not([data-testid])
        {{ background-color: {p['bg2']} !important; color: {p['text']}; border-color: {p['border']}; }}
    .stApp .stSelectbox svg, .stApp .stMultiSelect svg {{ color: {p['text']}; }}
    .stApp [data-testid="stFileUploaderDropzone"] {{ background: {p['bg2']}; color: {p['text']}; }}
    .stApp [data-testid="stFileUploaderDropzone"] *, .stApp [data-testid="stFileUploaderFile"] * {{ color: {p['text']}; }}
    .stApp [data-testid="stExpander"] details {{ background: {p['bg']}; border-color: {p['border']}; }}
    .stApp [data-testid="stExpander"] summary:hover {{ color: {p['primary']}; }}
    .stApp [data-testid="stLayoutWrapper"] > div {{ border-color: {p['border']}; }}
    .stApp button[kind="secondary"], .stApp [data-testid^="stBaseButton-secondary"],
    .stApp [data-testid="stButtonGroup"] button
        {{ background: {p['bg']}; color: {p['text']}; border-color: {p['border']}; }}
    .stApp [data-testid="stButtonGroup"] button * {{ color: {p['text']}; }}
    .stApp [data-testid="stButtonGroup"] button[data-selected="true"]
        {{ background: {p['bg2']}; border-color: {p['primary']}; }}
    .stApp [data-testid="stButtonGroup"] button[data-selected="true"] * {{ color: {p['primary']}; }}
    .stApp button[kind="primary"], .stApp [data-testid="stBaseButton-primary"]
        {{ background: {p['primary']}; border-color: {p['primary']}; color: {p['bg']}; }}
    .stApp [data-testid="stBaseButton-primary"] * {{ color: {p['bg']}; }}
    .stApp [data-baseweb="tag"] {{ background: {p['bg2']}; color: {p['text']}; }}
    .stApp [data-testid="stAlertContainer"] * {{ color: {p['text']}; }}
    body, [data-testid$="VirtualDropdown"], [data-baseweb="popover"] > div
        {{ background: {p['bg2']} !important; color: {p['text']}; }}
    [role="listbox"] [role="option"], [role="listbox"] [role="option"] * {{ color: {p['text']}; }}
    [role="listbox"] [role="option"]:hover, [role="listbox"] [role="option"][aria-selected="true"]
        {{ background: {p['border']}; }}
    .stApp [data-testid="stDataFrame"] {{ filter: {invert}; }}
    .stApp [data-testid="stProgress"] > div > div {{ background: {p['bg2']}; }}
    """


def style_fig(fig, p: dict, height: int):
    """Theme-aware Plotly layout: transparent background, soft grid, readable text in both modes."""
    fig.update_layout(height=height, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(color=p["text"], family="Source Sans Pro, Source Sans 3, sans-serif", size=13),
                      margin=dict(l=10, r=10, t=36, b=10), hoverlabel=dict(bgcolor=p["bg2"], font_color=p["text"]),
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, title=None,
                                  font=dict(color=p["text"]), bgcolor="rgba(0,0,0,0)"))
    fig.update_xaxes(automargin=True, gridcolor=p["grid"], zerolinecolor=p["grid"], linecolor=p["border"],
                     tickfont=dict(color=p["muted"]), title_font=dict(color=p["muted"]))
    fig.update_yaxes(automargin=True, gridcolor=p["grid"], zerolinecolor=p["grid"], linecolor=p["border"],
                     tickfont=dict(color=p["muted"]), title_font=dict(color=p["muted"]))
    return fig


def chart(fig, title: str | None = None, key: str | None = None):
    if title:
        st.markdown(f"<p class='gp-chart-title'>{title}</p>", unsafe_allow_html=True)
    st.plotly_chart(fig, width="stretch", theme=None, key=key, config={"displayModeBar": False})


def intro(text: str):
    st.markdown(f"<p class='gp-intro'>{text}</p>", unsafe_allow_html=True)


# ---------------------------------------------------------------- theme switch (top of sidebar)
with st.sidebar:
    choice = st.segmented_control("Appearance", list(THEME_CHOICES), format_func=THEME_CHOICES.get,
                                  default="auto", key="theme_choice")
device_theme = st.context.theme.type
theme = active_theme(choice, device_theme)
P = THEMES[theme]
LIGHT_COLORS = P["lights"]
CATEGORY_COLORS = {cat: LIGHT_COLORS[light] for cat, (light, _, _) in CATEGORIES.items()}
QUADRANT_COLORS = {q: LIGHT_COLORS[light] for q, light in QUADRANT_LIGHTS.items()}
st.html(f"<style>{base_css(P)}{forced_css(P, theme) if theme != (device_theme or 'light') else ''}</style>")

# ---------------------------------------------------------------- header + start screen
st.title(":green[:material/eco:] GreenProof")
st.markdown("<p class='gp-sub'>Talk vs. evidence: which green claims hold up?</p>", unsafe_allow_html=True)

results: list[ReportResult] = st.session_state.get("results", [])
st.session_state.setdefault("use_demo", False)
if not results:
    st.markdown("""
    <div class="gp-steps">
      <div class="gp-step"><div class="gp-num">1</div><b>Add reports</b>
        <span>Upload sustainability reports as PDF, or use the three fictional demo reports.</span></div>
      <div class="gp-step"><div class="gp-num">2</div><b>Choose a mode</b>
        <span>Rules work offline. ClimateBERT and the AI modes are optional.</span></div>
      <div class="gp-step"><div class="gp-num">3</div><b>Screen</b>
        <span>See which claims hold up against EU 2024/825 and GRI 305 / GRI 102.</span></div>
    </div>""", unsafe_allow_html=True)
    if st.button("Try with demo reports", type="primary", icon=":material/play_arrow:", key="demo_btn"):
        st.session_state["use_demo"] = True
        st.session_state["autorun"] = True

# ---------------------------------------------------------------- input
inputs = (st.expander("Reports and screening mode", icon=":material/upload_file:") if results
          else st.container(border=True))
with inputs:
    up_col, set_col = st.columns([3, 2], gap="large")
    uploads = up_col.file_uploader("Upload sustainability reports (PDF, one per company)", type="pdf",
                                   accept_multiple_files=True)
    mode = set_col.selectbox("Screening mode", ["rules", "climatebert", "ai", "nvidia"], format_func=MODES.get,
                             key="mode")
    set_col.toggle("Add the 3 fictional demo reports", key="use_demo")

with st.sidebar:
    api_key, model = None, None
    if mode == "ai":
        api_key = st.text_input("Anthropic API key", type="password", value=os.environ.get("ANTHROPIC_API_KEY", ""),
                                help="Only kept in this browser session, never stored.")
        model = st.text_input("Model", value=os.environ.get("GREENPROOF_MODEL", "claude-sonnet-5-5"))
    if mode == "nvidia":
        api_key = st.text_input("NVIDIA API key (nvapi-…)", type="password", value=os.environ.get("NVIDIA_API_KEY", ""),
                                help="Create one at build.nvidia.com → API keys. Only kept in this browser session.")
        options, tested = [], {}
        if api_key:
            with st.spinner("Testing which NVIDIA models your key can use (up to 90 s) …"):
                options, tested = nvidia_models(api_key)
        if options:
            model = st.selectbox("Model", options, index=0,
                                 help="Only models that just answered a test request with your key.")
            st.caption(f"{len(options)} working model(s) found.")
        else:
            if api_key:
                if any(r == "HTTP 401" for r in tested.values()):
                    st.error("NVIDIA rejected the key (401). Create a new one at build.nvidia.com → API keys.")
                else:
                    slow = [m for m, r in tested.items() if r == "timeout"]
                    st.warning("No model answered within 90 s. NVIDIA's free models are sometimes busy – "
                               "try again in a few minutes" + (f", or type one of the slow ones below, e.g. `{slow[0]}`."
                                                               if slow else "."))
            model = st.text_input("Model", value=llm.NVIDIA_DEFAULT_MODEL,
                                  help="Any chat model ID from build.nvidia.com/models")
        if tested:
            with st.expander("Model test details"):
                st.write({m: ("✅ works" if r == "ok" else f"❌ {r}") for m, r in tested.items()})
    st.caption("GreenProof rates claims against the EU green-claims rules applying from 27 Sep 2026 "
               "(Directive (EU) 2024/825) and checks GHG disclosure along GRI 305 / GRI 102. "
               "It flags greenwashing *risk*, it is not a legal opinion.")

with inputs:
    if mode == "climatebert" and not climatebert.available():
        st.warning("ClimateBERT needs `pip install transformers torch`. Falling back to rules.")
        mode = "rules"
    needs_key = mode in ("ai", "nvidia") and not api_key
    if needs_key:
        st.info("Enter your API key in the sidebar to use this mode (on phones: the arrow at the top left).",
                icon=":material/key:")

    files: list[tuple[str, bytes]] = [(u.name, u.getvalue()) for u in uploads or []]
    if st.session_state["use_demo"]:
        files += [(p.name, p.read_bytes()) for p in sorted(DEMO_DIR.glob("*.pdf"))]

    autorun = st.session_state.pop("autorun", False)
    if files:
        names = pd.DataFrame({"file": [f for f, _ in files], "company": [company_from_filename(f) for f, _ in files]})
        names = st.data_editor(names, disabled=["file"], hide_index=True, width="stretch",
                               key="names_" + "_".join(f for f, _ in files))
        clicked = st.button("Screen reports", type="primary", icon=":material/search:", disabled=needs_key)
        if clicked or autorun:
            run_mode = "rules" if needs_key else mode          # the one-click demo always works offline
            screened, notes = [], []
            bar = st.progress(0.0, text="Starting …")
            for i, ((fname, data), company) in enumerate(zip(files, names["company"])):
                bar.progress(i / len(files), text=f"Screening {company} …")
                started = time.time()

                def show(fraction: float, i=i, company=company, started=started) -> None:
                    text = f"Screening {company} … {fraction:.0%}"
                    if run_mode in ("ai", "nvidia") and 0 < fraction < 1:
                        left = (time.time() - started) / fraction * (1 - fraction)
                        text += f" · about {max(1, round(left / 60))} min left"
                    bar.progress(min((i + fraction) / len(files), 1.0), text=text)

                try:
                    res = run_screening(data, company, run_mode, api_key, model, progress=show)
                    if res.sentences == 0:
                        notes.append(f"{fname}: no readable text – is it a scanned PDF?")
                    screened.append(res)
                except Exception as exc:  # show the problem but keep the other reports
                    notes.append(f"{fname}: {exc}")
            st.session_state["results"] = screened
            st.session_state["screen_notes"] = notes
            st.session_state.pop("validation_key", None)
            st.rerun()

for note in st.session_state.get("screen_notes", []):
    st.warning(note)
if not results:
    st.stop()

claims = pd.concat([r.claims for r in results], ignore_index=True)
evidence = pd.concat([r.evidence_table() for r in results], ignore_index=True)
summary = company_summary(claims, {r.company: r.evidence_score for r in results})
if summary.empty:
    st.warning("No environmental claims found in the uploaded reports.")
    st.stop()

# segmented control instead of st.tabs: keeps the selected view when a widget triggers a rerun
view = st.segmented_control("View", list(VIEWS), format_func=VIEWS.get, default="Ranking", key="view",
                            label_visibility="collapsed") or "Ranking"

# ================================================================ ranking
if view == "Ranking":
    intro("How credible each company's green talk is compared with the climate data it actually discloses.")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Companies", len(summary), border=True)
    c2.metric("Claims found", int(summary["claims"].sum()), border=True)
    c3.metric("Red flags", int(summary["red"].sum()), border=True)
    c4.metric("Greenwashing risk", int((summary["quadrant"] == "Greenwashing risk").sum()), border=True)

    left, right = st.columns([1.15, 1], gap="large")
    fig = px.scatter(summary, x="evidence", y="score", text="company", size="claims", color="quadrant",
                     color_discrete_map=QUADRANT_COLORS, size_max=36, range_x=[-18, 118], range_y=[-15, 118],
                     labels={"evidence": "Evidence Score (GHG disclosure, 0–100)",
                             "score": "Claim Quality Score (talk, 0–100)"})
    fig.add_hline(y=50, line_dash="dot", line_color=LIGHT_COLORS["grey"])
    fig.add_vline(x=50, line_dash="dot", line_color=LIGHT_COLORS["grey"])
    for xp, yp, txt in [(0.99, 0.99, "Credible"), (0.01, 0.99, "Careful claims, thin data"),
                        (0.99, 0.01, "Good data, weak claims"), (0.01, 0.01, "Greenwashing risk")]:
        fig.add_annotation(x=xp, y=yp, xref="paper", yref="paper", text=f"<b>{txt}</b>", showarrow=False,
                           font=dict(color=P["muted"], size=11), xanchor="right" if xp > 0.5 else "left",
                           yanchor="top" if yp > 0.5 else "bottom")
    fig.update_traces(textposition="bottom center", cliponaxis=False, textfont_color=P["text"],
                      marker=dict(line=dict(width=0), opacity=0.9))
    style_fig(fig, P, 470).update_layout(showlegend=False, margin=dict(t=12))
    with left:
        chart(fig, "Talk vs. evidence")

    long = summary.melt(id_vars="company", value_vars=["score", "evidence", "overall"], var_name="measure",
                        value_name="points")
    fig2 = px.bar(long, x="company", y="points", color="measure", barmode="group", range_y=[0, 100],
                  color_discrete_map=P["measures"], labels={"points": "points (0–100)"})
    style_fig(fig2, P, 470).update_layout(xaxis_title=None, bargap=0.3)
    with right:
        chart(fig2, "Scores per company")

    with st.expander("Score table", icon=":material/table_rows:"):
        st.dataframe(summary[["company", "overall", "score", "evidence", "quadrant", "claims", "green", "yellow",
                              "red", "grey", "red_share_%"]], width="stretch")
    st.caption("Overall = average of Claim Quality Score (how claims are worded, EU 2024/825) and Evidence Score "
               "(which GHG data is disclosed, GRI 305 / GRI 102). Quadrant cut-off: 50 points.")

# ================================================================ company detail
elif view == "Company detail":
    intro("All claims of one company with their traffic light, and which GHG data its report discloses.")
    company = st.selectbox("Company", summary["company"].tolist())
    sub = claims[claims["company"] == company]
    ev = evidence[evidence["company"] == company]
    row = summary[summary["company"] == company].iloc[0]
    light = LIGHT_COLORS[QUADRANT_LIGHTS.get(row["quadrant"], "grey")]
    st.markdown(f"<span class='gp-badge' style='color:{light};border-color:{light}'>{row['quadrant']}</span>",
                unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Overall", f"{row['overall']:.0f}", border=True)
    c2.metric("Claim quality", f"{row['score']:.0f}" if pd.notna(row["score"]) else "–", border=True)
    c3.metric("Evidence", f"{row['evidence']:.0f}", border=True)
    c4.metric("Red claims", int(row["red"]), border=True)

    left, right = st.columns(2, gap="large")
    with left:
        counts = category_counts(sub).T.reset_index()
        counts.columns = ["category", "claims"]
        fig3 = px.bar(counts, x="claims", y="category", orientation="h", color="category",
                      color_discrete_map=CATEGORY_COLORS)
        style_fig(fig3, P, 360).update_layout(showlegend=False, yaxis_title=None, margin=dict(t=12))
        fig3.update_layout(margin=dict(l=9 * int(counts["category"].str.len().max()) + 16))
        chart(fig3, "Claims per category")
    with right:
        st.markdown("<p class='gp-chart-title'>Evidence checklist (GRI 305 / GRI 102)</p>", unsafe_allow_html=True)
        st.dataframe(ev.assign(page=ev["page"].map(lambda p: "–" if pd.isna(p) else str(int(p))))
                     [["found", "item", "reference", "page"]],
                     hide_index=True, width="stretch", height=380,
                     column_config={"found": st.column_config.CheckboxColumn("Found", width="small")})

    lights = st.multiselect("Show claims", ["red", "yellow", "green", "grey"], default=["red", "yellow"])
    table = sub[sub["light"].isin(lights)][["light_icon", "page", "category", "claim", "why", "explanation"]]
    st.dataframe(table, hide_index=True, width="stretch",
                 column_config={"light_icon": st.column_config.TextColumn("", width="small"),
                                "claim": st.column_config.TextColumn("Claim", width="large")})
    with st.expander("Where was the evidence found?", icon=":material/plagiarism:"):
        st.dataframe(ev[ev["found"]][["item", "page", "where"]], hide_index=True, width="stretch")

# ================================================================ validation
elif view == "Validate":
    intro("How often the tool agrees with a human: label a random sample yourself, then compare.")
    st.markdown("Label the claims *without looking at the tool's rating*, then switch the rating on. "
                "This shows how reliable the screener is – a key result for the report.")
    n_max = len(claims)
    n = st.slider("Sample size", 1, n_max, min(50, n_max)) if n_max > 1 else 1
    key = (n_max, n)
    if st.session_state.get("validation_key") != key:
        sample = claims.sample(n=n, random_state=42)[["company", "page", "claim", "category"]].copy()
        sample.insert(0, "hand_label", None)
        st.session_state["validation_sample"] = sample.reset_index(drop=True)
        st.session_state["validation_key"] = key
    sample = st.session_state["validation_sample"]
    reveal = st.toggle("Show the tool's rating (switch on only after labelling)", value=False)
    cols = ["hand_label", "company", "page", "claim"] + (["category"] if reveal else [])
    edited = st.data_editor(
        sample[cols], hide_index=True, width="stretch", key=f"labels_{key}",
        disabled=[c for c in cols if c != "hand_label"],
        column_config={"hand_label": st.column_config.SelectboxColumn("Your label", options=list(CATEGORIES), width="medium"),
                       "claim": st.column_config.TextColumn("Claim", width="large")})
    labelled = sample.assign(hand_label=edited["hand_label"].values)
    done = int(labelled["hand_label"].notna().sum())
    st.progress(done / len(labelled), text=f"{done} of {len(labelled)} labelled")
    result = agreement(labelled.dropna(subset=["hand_label"])) if done >= 5 else None
    if result:
        c1, c2, c3 = st.columns(3)
        c1.metric("Category accuracy", f"{result.accuracy:.0%}", border=True)
        c2.metric("Cohen's kappa", f"{result.kappa:.2f}", border=True,
                  help=f"{kappa_label(result.kappa)} agreement (Landis & Koch, 1977)")
        c3.metric("Traffic-light accuracy", f"{result.light_accuracy:.0%}", border=True)
        fig4 = px.imshow(result.confusion, text_auto=True, aspect="auto",
                         color_continuous_scale=[[0, P["bg2"]], [1, P["primary"]]],
                         labels=dict(x="Tool", y="Human", color="claims"))
        style_fig(fig4, P, 420).update_layout(margin=dict(t=12))
        fig4.update_coloraxes(colorbar=dict(tickfont=dict(color=P["muted"]), title_font=dict(color=P["muted"])))
        chart(fig4, "Confusion matrix")
    else:
        st.info("Label at least 5 claims to see the agreement.", icon=":material/info:")
    st.download_button("Download labelled sample (CSV)", labelled.to_csv(index=False).encode("utf-8-sig"),
                       file_name="greenproof_validation.csv", mime="text/csv", icon=":material/download:")

# ================================================================ data
elif view == "Data":
    intro("Every claim the screener found, with its rating, ready to download for your own analysis.")
    st.dataframe(claims.drop(columns=["light_icon"]), hide_index=True, width="stretch")
    c1, c2, c3 = st.columns(3)
    c1.download_button("Claims (CSV)", claims.drop(columns=["light_icon"]).to_csv(index=False).encode("utf-8-sig"),
                       file_name="greenproof_claims.csv", mime="text/csv", icon=":material/download:")
    c2.download_button("Evidence checklist (CSV)", evidence.to_csv(index=False).encode("utf-8-sig"),
                       file_name="greenproof_evidence.csv", mime="text/csv", icon=":material/download:")
    c3.download_button("Company scores (CSV)", summary.to_csv().encode("utf-8-sig"),
                       file_name="greenproof_scores.csv", mime="text/csv", icon=":material/download:")

# ================================================================ method
else:
    intro("The scoring rubric behind the traffic lights and both scores.")
    st.markdown((ROOT / "rubric.md").read_text(encoding="utf-8"))
