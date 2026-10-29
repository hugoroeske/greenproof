"""Batch run for the midterm sample: screen every PDF in a folder with the rule mode (no Streamlit).

Usage:
    python run_sample.py                       # reads reports/, writes results/
    python run_sample.py --reports my_pdfs --review 15

Writes:
    results/claims.csv   company, page, sentence, category, colour, trigger_words
    results/scores.csv   company, n_sentences, n_claims, score, share_red, share_yellow, share_green, share_grey
    results/review_sample.csv   stratified random claims for a manual rule check (fixed seed)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from screener.naming import company_from_filename
from screener.pipeline import screen

SEED = 42


def company_name(pdf: Path) -> str:
    """'asus_2025.pdf' -> 'asus'; '2024_Acer_Sustainability_Report.pdf' -> 'Acer'."""
    return company_from_filename(pdf)


def run(reports: Path, out: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    pdfs = sorted(reports.glob("*.pdf"))
    if not pdfs:
        sys.exit(f"No PDFs found in {reports.resolve()}")
    claim_rows, score_rows = [], []
    for pdf in pdfs:
        company = company_name(pdf)
        res = screen(pdf.read_bytes(), company, mode="rules")
        c = res.claims
        claim_rows.append(pd.DataFrame({
            "company": c["company"], "page": c["page"], "sentence": c["claim"], "category": c["category"],
            "colour": c["light"], "trigger_words": c["why"],
        }))
        n = len(c)
        rated = c[c["points"].notna()]
        share = lambda col: round(100 * (c["light"] == col).sum() / n, 1) if n else 0.0
        score_rows.append({
            "company": company, "n_sentences": res.sentences, "n_claims": n,
            "score": round(rated["points"].mean(), 1) if len(rated) else None,
            "share_red": share("red"), "share_yellow": share("yellow"),
            "share_green": share("green"), "share_grey": share("grey"),
        })
        print(f"  {pdf.name}: {res.pages} pages, {res.sentences} sentences, {n} claims")
    claims = pd.concat(claim_rows, ignore_index=True)
    scores = pd.DataFrame(score_rows).sort_values("score", ascending=False, na_position="last")
    out.mkdir(parents=True, exist_ok=True)
    claims.to_csv(out / "claims.csv", index=False, encoding="utf-8-sig")
    scores.to_csv(out / "scores.csv", index=False, encoding="utf-8-sig")
    return claims, scores


def review_sample(claims: pd.DataFrame, n: int = 15) -> pd.DataFrame:
    """Stratified sample: spread n claims as evenly as possible over the categories (fixed seed)."""
    groups = [g.sample(frac=1, random_state=SEED) for _, g in claims.groupby("category")]
    picked, i = [], 0
    while len(picked) < min(n, len(claims)):
        for g in groups:
            if i < len(g) and len(picked) < n:
                picked.append(g.iloc[i])
        i += 1
    return pd.DataFrame(picked).reset_index(drop=True)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--reports", default="reports", type=Path)
    ap.add_argument("--out", default="results", type=Path)
    ap.add_argument("--review", default=15, type=int, help="number of claims for the manual rule check")
    args = ap.parse_args()

    print(f"Screening PDFs in {args.reports} …")
    claims, scores = run(args.reports, args.out)
    pd.set_option("display.width", 200, "display.max_colwidth", 110)
    print("\nScores (Claim Quality Score: green 100, yellow 50, red 0; shares in % of claims)")
    print(scores.to_string(index=False))

    sample = review_sample(claims, args.review)
    sample.to_csv(args.out / "review_sample.csv", index=False, encoding="utf-8-sig")
    print(f"\n{len(sample)} claims for the manual rule check (seed {SEED}):")
    for k, r in sample.iterrows():
        print(f"\n[{k + 1}] {r['company']} p.{r['page']} | {r['category']} ({r['colour']}) | trigger: {r['trigger_words']}")
        print(f"    {r['sentence']}")
    print(f"\nFiles written to {args.out.resolve()}")


if __name__ == "__main__":
    main()
