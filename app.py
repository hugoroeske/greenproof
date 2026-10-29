"""GreenProof – Greenwashing Screener (Streamlit app).

Start with:  streamlit run app.py
"""
from __future__ import annotations

import os
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
LIGHT_COLORS = {"green": "#2E7D32", "yellow": "#F9A825", "red": "#C62828", "grey": "#9E9E9E"}
CATEGORY_COLORS = {cat: LIGHT_COLORS[light] for cat, (light, _, _) in CATEGORIES.items()}
QUADRANT_COLORS = {"Credible": "#2E7D32", "Careful claims, thin data": "#F9A825",
                   "Good data, weak claims": "#F9A825", "Greenwashing risk": "#C62828", "–": "#9E9E9E"}

st.set_page_config(page_title="GreenProof – Greenwashing Screener", page_icon="🌿", layout="wide")


@st.cache_data(ttl=900, show_spinner=False)
def nvidia_models(api_key: str) -> tuple[list[str], dict[str, str]]:
    return llm.nvidia_working_models(api_key)


@st.cache_data(show_spinner=False)
def run_screening(pdf_bytes: bytes, company: str, mode: str, api_key: str | None, model: str | None) -> ReportResult:
    return screen(pdf_bytes, company, mode=mode, api_key=api_key, model=model)


# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.header("⚙️ Settings")
    mode = st.radio("Screening mode", ["rules", "climatebert", "ai", "nvidia"], format_func=lambda m: MODES[m])
    api_key, model = None, None
    if mode == "climatebert" and not climatebert.available():
        st.warning("ClimateBERT needs `pip install transformers torch`. Falling back to rules.")
        mode = "rules"
    if mode == "ai":
        api_key = st.text_input("Anthropic API key", type="password", value=os.environ.get("ANTHROPIC_API_KEY", ""),
                                help="Only kept in this browser session, never stored.")
        model = st.text_input("Model", value=os.environ.get("GREENPROOF_MODEL", "claude-sonnet-5-5"))
        if not api_key:
            st.info("Enter an API key to use the AI mode.")
    if mode == "nvidia":
        api_key = st.text_input("NVIDIA API key (nvapi-…)", type="password", value=os.environ.get("NVIDIA_API_KEY", ""),
                                help="Create one at build.nvidia.com → API keys. Only kept in this browser session.")
        options, tested = [], {}
        if api_key:
            with st.spinner("Testing which NVIDIA models your key can use …"):
                options, tested = nvidia_models(api_key)
        if options:
            model = st.selectbox("Model", options, index=0,
                                 help="Only models that just answered a test request with your key.")
            st.caption(f"✅ {len(options)} working model(s) found.")
        else:
            if api_key:
                if any(r == "HTTP 401" for r in tested.values()):
                    st.error("NVIDIA rejected the key (401). Create a new one at build.nvidia.com → API keys.")
                else:
                    st.warning("None of the tested models answered. Copy a model ID from build.nvidia.com/models "
                               "(page 'Try API') and paste it below.")
            model = st.text_input("Model", value=llm.NVIDIA_DEFAULT_MODEL,
                                  help="Any chat model ID from build.nvidia.com/models")
        if tested:
            with st.expander("Model test details"):
                st.write({m: ("✅ works" if r == "ok" else f"❌ {r}") for m, r in tested.items()})
        if not api_key:
            st.info("Enter an NVIDIA API key to use this mode.")
    st.divider()
    use_demo = st.checkbox("Use the 3 fictional demo reports", value=False)
    st.caption("GreenProof rates claims against the EU green-claims rules applying from 27 Sep 2026 "
               "(Directive (EU) 2024/825) and checks GHG disclosure along GRI 305 / GRI 102. "
               "It flags greenwashing *risk*, it is not a legal opinion.")

# ---------------------------------------------------------------- input
st.title("🌿 GreenProof")
st.subheader("Talk vs. evidence: which green claims hold up?")

uploads = st.file_uploader("Upload sustainability reports (PDF, one per company)", type="pdf", accept_multiple_files=True)
files: list[tuple[str, bytes]] = [(u.name, u.getvalue()) for u in uploads or []]
if use_demo:
    files += [(p.name, p.read_bytes()) for p in sorted(DEMO_DIR.glob("*.pdf"))]

if files:
    names = pd.DataFrame({"file": [f for f, _ in files], "company": [company_from_filename(f) for f, _ in files]})
    names = st.data_editor(names, disabled=["file"], hide_index=True, width="stretch",
                           key="names_" + "_".join(f for f, _ in files))
    if st.button("🔍 Screen reports", type="primary", disabled=(mode in ("ai", "nvidia") and not api_key)):
        results, bar = [], st.progress(0.0, text="Starting …")
        for i, ((fname, data), company) in enumerate(zip(files, names["company"])):
            bar.progress(i / len(files), text=f"Screening {company} …")
            try:
                res = run_screening(data, company, mode, api_key, model)
                if res.sentences == 0:
                    st.warning(f"{fname}: no readable text – is it a scanned PDF?")
                results.append(res)
            except Exception as exc:  # show the problem but keep the other reports
                st.error(f"{fname}: {exc}")
        bar.progress(1.0, text="Done")
        st.session_state["results"] = results
        st.session_state.pop("validation_key", None)
else:
    st.info("Upload one or more PDF reports – or tick **Use the 3 fictional demo reports** in the sidebar.")

results: list[ReportResult] = st.session_state.get("results", [])
if not results:
    st.stop()

claims = pd.concat([r.claims for r in results], ignore_index=True)
evidence = pd.concat([r.evidence_table() for r in results], ignore_index=True)
summary = company_summary(claims, {r.company: r.evidence_score for r in results})
if summary.empty:
    st.warning("No environmental claims found in the uploaded reports.")
    st.stop()

# a radio instead of st.tabs: keeps the selected view when a widget triggers a rerun
VIEWS = ["🏆 Ranking", "🔎 Company detail", "✅ Validate", "📋 Data", "📖 Method"]
view = st.radio("View", VIEWS, horizontal=True, key="view", label_visibility="collapsed")
st.divider()

# ================================================================ ranking
if view == VIEWS[0]:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Companies", len(summary))
    c2.metric("Claims found", int(summary["claims"].sum()))
    c3.metric("Red flags", int(summary["red"].sum()))
    c4.metric("Greenwashing-risk companies", int((summary["quadrant"] == "Greenwashing risk").sum()))

    left, right = st.columns([1.15, 1])
    fig = px.scatter(summary, x="evidence", y="score", text="company", size="claims", color="quadrant",
                     color_discrete_map=QUADRANT_COLORS, size_max=36, range_x=[-18, 118], range_y=[-15, 118],
                     labels={"evidence": "Evidence Score (GHG disclosure, 0–100)",
                             "score": "Claim Quality Score (talk, 0–100)"},
                     title="Talk vs. evidence")
    fig.add_hline(y=50, line_dash="dot", line_color="#9E9E9E")
    fig.add_vline(x=50, line_dash="dot", line_color="#9E9E9E")
    for xp, yp, txt in [(0.99, 0.99, "Credible"), (0.01, 0.99, "Careful claims, thin data"),
                        (0.99, 0.01, "Good data, weak claims"), (0.01, 0.01, "Greenwashing risk")]:
        fig.add_annotation(x=xp, y=yp, xref="paper", yref="paper", text=f"<b>{txt}</b>", showarrow=False,
                           font=dict(color="#5B6766", size=11), xanchor="right" if xp > 0.5 else "left",
                           yanchor="top" if yp > 0.5 else "bottom")
    fig.update_traces(textposition="bottom center", cliponaxis=False)
    fig.update_layout(showlegend=False, height=470)
    left.plotly_chart(fig, width="stretch")

    long = summary.melt(id_vars="company", value_vars=["score", "evidence", "overall"], var_name="measure",
                        value_name="points")
    fig2 = px.bar(long, x="company", y="points", color="measure", barmode="group", range_y=[0, 100],
                  color_discrete_map={"score": "#7E9C99", "evidence": "#1F5E3B", "overall": "#C9A227"},
                  title="Scores per company", labels={"points": "points (0–100)"})
    fig2.update_layout(xaxis_title=None, legend_title=None, height=470)
    right.plotly_chart(fig2, width="stretch")

    st.dataframe(summary[["company", "overall", "score", "evidence", "quadrant", "claims", "green", "yellow", "red",
                          "grey", "red_share_%"]], width="stretch")
    st.caption("Overall = average of Claim Quality Score (how claims are worded, EU 2024/825) and Evidence Score "
               "(which GHG data is disclosed, GRI 305 / GRI 102). Quadrant cut-off: 50 points.")

# ================================================================ company detail
elif view == VIEWS[1]:
    company = st.selectbox("Company", summary["company"].tolist())
    sub = claims[claims["company"] == company]
    ev = evidence[evidence["company"] == company]
    row = summary[summary["company"] == company].iloc[0]
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Overall", f"{row['overall']:.0f}")
    c2.metric("Claim quality", f"{row['score']:.0f}" if pd.notna(row["score"]) else "–")
    c3.metric("Evidence", f"{row['evidence']:.0f}")
    c4.metric("🔴 Red claims", int(row["red"]))
    c5.metric("Quadrant", row["quadrant"])

    left, right = st.columns(2)
    with left:
        st.markdown("**Claims per category**")
        counts = category_counts(sub).T.reset_index()
        counts.columns = ["category", "claims"]
        fig3 = px.bar(counts, x="claims", y="category", orientation="h", color="category",
                      color_discrete_map=CATEGORY_COLORS)
        fig3.update_layout(showlegend=False, yaxis_title=None, height=360, margin=dict(t=10))
        st.plotly_chart(fig3, width="stretch")
    with right:
        st.markdown("**Evidence checklist (GRI 305 / GRI 102)**")
        st.dataframe(ev.assign(found=ev["found"].map({True: "✅", False: "❌"}),
                               page=ev["page"].map(lambda p: "–" if pd.isna(p) else str(int(p))))[["found", "item", "reference", "page"]],
                     hide_index=True, width="stretch", height=380)

    lights = st.multiselect("Show claims", ["red", "yellow", "green", "grey"], default=["red", "yellow"])
    table = sub[sub["light"].isin(lights)][["light_icon", "page", "category", "claim", "why", "explanation"]]
    st.dataframe(table, hide_index=True, width="stretch",
                 column_config={"light_icon": st.column_config.TextColumn("", width="small"),
                                "claim": st.column_config.TextColumn("Claim", width="large")})
    with st.expander("Where was the evidence found?"):
        st.dataframe(ev[ev["found"]][["item", "page", "where"]], hide_index=True, width="stretch")

# ================================================================ validation
elif view == VIEWS[2]:
    st.markdown("**Hand validation.** Label a random sample *without looking at the tool's rating*, then compare. "
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
        c1.metric("Category accuracy", f"{result.accuracy:.0%}")
        c2.metric("Cohen's kappa", f"{result.kappa:.2f}",
                  help=f"{kappa_label(result.kappa)} agreement (Landis & Koch, 1977)")
        c3.metric("Traffic-light accuracy", f"{result.light_accuracy:.0%}")
        fig4 = px.imshow(result.confusion, text_auto=True, color_continuous_scale="Greens", aspect="auto",
                         labels=dict(x="Tool", y="Human", color="claims"), title="Confusion matrix")
        st.plotly_chart(fig4, width="stretch")
    else:
        st.info("Label at least 5 claims to see the agreement.")
    st.download_button("⬇️ Download labelled sample (CSV)", labelled.to_csv(index=False).encode("utf-8-sig"),
                       file_name="greenproof_validation.csv", mime="text/csv")

# ================================================================ data
elif view == VIEWS[3]:
    st.markdown("**All claims**")
    st.dataframe(claims.drop(columns=["light_icon"]), hide_index=True, width="stretch")
    c1, c2, c3 = st.columns(3)
    c1.download_button("⬇️ Claims (CSV)", claims.drop(columns=["light_icon"]).to_csv(index=False).encode("utf-8-sig"),
                       file_name="greenproof_claims.csv", mime="text/csv")
    c2.download_button("⬇️ Evidence checklist (CSV)", evidence.to_csv(index=False).encode("utf-8-sig"),
                       file_name="greenproof_evidence.csv", mime="text/csv")
    c3.download_button("⬇️ Company scores (CSV)", summary.to_csv().encode("utf-8-sig"),
                       file_name="greenproof_scores.csv", mime="text/csv")

# ================================================================ method
else:
    st.markdown((ROOT / "rubric.md").read_text(encoding="utf-8"))
