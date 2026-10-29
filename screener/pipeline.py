"""Glue code: PDF -> sentences -> claims -> ratings -> company scores (talk + evidence)."""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from .classify import CATEGORIES, LIGHT_EMOJI, Rating, classify, is_environmental_claim, rate_sentence
from .evidence import EvidenceHit, check_evidence, evidence_score
from .extract import extract_pages, sentences_from_pages

MODES = {
    "rules": "Rules (transparent, free, offline)",
    "climatebert": "ClimateBERT detection + rules",
    "ai": "AI (Claude API) – detection and rating",
    "nvidia": "AI (NVIDIA API, open models) – detection and rating",
}
CLAIM_COLUMNS = ["company", "page", "claim", "category", "light", "light_icon", "points",
                 "why", "explanation", "method", "hand_label"]


@dataclass
class ReportResult:
    company: str
    claims: pd.DataFrame
    evidence: list[EvidenceHit] = field(default_factory=list)
    pages: int = 0
    sentences: int = 0

    @property
    def evidence_score(self) -> float:
        return evidence_score(self.evidence)

    def evidence_table(self) -> pd.DataFrame:
        return pd.DataFrame([{"company": self.company, "item": h.label, "reference": h.reference,
                              "found": h.found, "page": h.page, "where": h.snippet} for h in self.evidence])


def _rate(texts: list[str], mode: str, api_key: str | None, model: str | None, progress,
          ai_scope: str = "claims") -> list[Rating]:
    if mode in ("ai", "nvidia"):
        from . import llm
        from . import rules
        provider = "nvidia" if mode == "nvidia" else "anthropic"
        # Which sentences go to the AI (it still decides "claim or not" and the category):
        #   "claims": sentences the rules detect as claims – fast, the AI acts as a second rater
        #   "all":    every sentence with an environmental keyword – thorough, about 3x slower
        if ai_scope == "all":
            idx = [i for i, t in enumerate(texts)
                   if rules.ENVIRONMENT.search(t) or rules.GENERIC.search(t) or rules.NEUTRALITY.search(t)]
        else:
            idx = [i for i, t in enumerate(texts) if is_environmental_claim(t)]
        ratings = [Rating(False, source="ai-nvidia" if provider == "nvidia" else "ai")] * len(texts)
        if idx:
            rated = llm.rate_sentences([texts[i] for i in idx], api_key=api_key, model=model,
                                       progress=progress, provider=provider)
            for i, r in zip(idx, rated):
                ratings[i] = r
        elif progress:
            progress(1.0)
        return ratings
    if mode == "climatebert":
        from . import climatebert
        flags = climatebert.detect_claims(texts, progress=progress)
        return [classify(t) if f else Rating(False) for t, f in zip(texts, flags)]
    if progress:
        progress(1.0)
    return [rate_sentence(t) for t in texts]


def screen(pdf_bytes: bytes, company: str, mode: str = "rules", api_key: str | None = None,
           model: str | None = None, progress=None, ai_scope: str = "claims") -> ReportResult:
    pages = extract_pages(pdf_bytes)
    sentences = sentences_from_pages(pages)
    ratings = _rate([s.text for s in sentences], mode, api_key, model, progress, ai_scope)

    rows = []
    for s, r in zip(sentences, ratings):
        if not r.is_claim:
            continue
        rows.append({
            "company": company, "page": s.page, "claim": s.text, "category": r.category,
            "light": r.light, "light_icon": LIGHT_EMOJI[r.light], "points": r.points,
            "why": "; ".join(e for e in r.evidence if e), "explanation": r.explanation,
            "method": "climatebert+rules" if mode == "climatebert" else r.source, "hand_label": "",
        })
    claims = pd.DataFrame(rows, columns=CLAIM_COLUMNS)
    return ReportResult(company, claims, check_evidence(pages), pages=len(pages), sentences=len(sentences))


def screen_report(pdf_bytes: bytes, company: str, **kwargs) -> pd.DataFrame:
    """Backwards-compatible helper: claims only."""
    result = screen(pdf_bytes, company, **kwargs)
    result.claims.attrs["sentences_total"] = result.sentences
    return result.claims


def company_summary(claims: pd.DataFrame, evidence: dict[str, float] | None = None) -> pd.DataFrame:
    """One row per company: Claim Quality Score (talk), Evidence Score and traffic-light counts."""
    if claims.empty:
        return pd.DataFrame()
    rated = claims[claims["points"].notna()]
    out = claims.groupby("company").agg(claims=("claim", "size")).reset_index()
    score = rated.groupby("company")["points"].mean().round(1).rename("score")
    lights = claims.pivot_table(index="company", columns="light", values="claim", aggfunc="count", fill_value=0)
    for col in ["green", "yellow", "red", "grey"]:
        if col not in lights:
            lights[col] = 0
    out = out.merge(score, on="company", how="left").merge(lights[["green", "yellow", "red", "grey"]], on="company")
    rated_n = (out["green"] + out["yellow"] + out["red"]).replace(0, pd.NA)
    out["red_share_%"] = (out["red"] / rated_n * 100).astype(float).round(1)
    if evidence is not None:
        out["evidence"] = out["company"].map(evidence)
        out["overall"] = out[["score", "evidence"]].mean(axis=1).round(1)
        out["quadrant"] = [quadrant(s, e) for s, e in zip(out["score"], out["evidence"])]
        out = out.sort_values("overall", ascending=False)
    else:
        out = out.sort_values("score", ascending=False)
    out = out.reset_index(drop=True)
    out.index = out.index + 1
    out.index.name = "rank"
    return out


def quadrant(talk: float, evidence: float, cut: float = 50) -> str:
    if pd.isna(talk) or pd.isna(evidence):
        return "–"
    if talk >= cut and evidence >= cut:
        return "Credible"
    if talk < cut and evidence < cut:
        return "Greenwashing risk"
    if talk < cut:
        return "Good data, weak claims"
    return "Careful claims, thin data"


def category_counts(claims: pd.DataFrame) -> pd.DataFrame:
    order = list(CATEGORIES)
    table = claims.pivot_table(index="company", columns="category", values="claim", aggfunc="count", fill_value=0)
    return table.reindex(columns=[c for c in order if c in table.columns])
