# 🌿 GreenProof – Greenwashing Screener (v0.2)

GreenProof reads corporate sustainability reports (PDF) and answers two questions per company:

1. **Talk – how honest are the green claims?** Every environmental claim is rated against the EU
   green-claims rules that apply from **27 September 2026** (Directive (EU) 2024/825) → *Claim Quality Score*.
2. **Evidence – does the company back them up?** A 10-item checklist based on **GRI 305: Emissions**
   and **GRI 102: Climate Change** checks which climate data is disclosed → *Evidence Score*.

Both scores (0–100) place each company in a **talk vs. evidence matrix**; "lots of green talk,
little evidence" is flagged as greenwashing risk.

> Course project – Sustainability and ESG Data Analytics, National Taipei University, Fall 2026.
> The tool flags greenwashing **risk**; it is not a legal opinion.

## How it works

```
PDF ─► extract text ─┬─► sentences ─► detect claims ─► rate claims (9 categories) ─► Claim Quality Score ─┐
                     └─► page text ─► GRI 305 / GRI 102 evidence checklist ────────► Evidence Score ──────┴─► matrix & ranking
```

| Step | What happens | File |
|---|---|---|
| Extract | PDF text per page (pypdf, pdfplumber fallback), sentences with page numbers | `screener/extract.py` |
| Detect | A sentence is a claim if it is about the environment **and** the company talks about itself | `screener/classify.py` |
| Rate | One of 9 categories per claim (🔴 offset-based neutrality, 🔴 generic, 🟡 overstated, 🟡 target without plan, 🟢 specific …) | `rubric.md`, `screener/rules.py` |
| Evidence | Scope 1/2/3, intensity, base year, SBTi, transition plan, carbon credits, assurance, GRI index – with page reference | `screener/evidence.py` |
| Score | Claim Quality (🟢 100 · 🟡 50 · 🔴 0), Evidence (10 pts per item), Overall = average | `screener/pipeline.py` |
| Validate | Agreement with hand labels: accuracy, Cohen's kappa, confusion matrix | `screener/validation.py` |

### Three screening modes

| Mode | Claim detection | Claim rating | Needs |
|---|---|---|---|
| **Rules** (default) | Keyword rules | Keyword rules | Nothing – free, offline, fully transparent |
| **ClimateBERT + rules** | `climatebert/environmental-claims` (Stammbach et al., ACL 2023) | Keyword rules | `pip install transformers torch` |
| **AI (Claude API)** | Claude | Claude, same rubric | Anthropic API key |

The Evidence Score is always rule-based, so it is identical in all modes.

## Quick start

```bash
pip install -r requirements.txt
streamlit run app.py
```

Upload PDFs or tick **Use the 3 fictional demo reports** in the sidebar, then click **Screen reports**.

App views: **Ranking** (matrix + scores) · **Company detail** (claims, evidence checklist with pages) ·
**Validate** (blind hand-labelling with live kappa) · **Data** (CSV downloads) · **Method** (rubric).

## Batch run for the sample (midterm)

Put the sample PDFs into `reports/` (named `company_year.pdf`, e.g. `asus_2025.pdf`), then:

```bash
python run_sample.py
```

This screens all reports in rule mode (no UI) and writes `results/claims.csv`
(company, page, sentence, category, colour, trigger_words), `results/scores.csv`
(company, n_sentences, n_claims, score, share_red/yellow/green/grey in % of claims) and
`results/review_sample.csv` (15 stratified claims, seed 42, for the manual rule check).
Rule fixes are logged in `results/rule_changes.md`.

## Validation (for the report)

Open **Validate**, keep "Show the tool's rating" switched off, label the sample, read off accuracy and
Cohen's kappa. Or download the claims CSV, fill `hand_label` and run `python validate.py file.csv`.

## Tests

```bash
python -m pytest -q          # 39 tests: rules, evidence checklist, pipeline, AI mode (mocked), validation
```

## Project structure

```
app.py                  Streamlit dashboard
rubric.md               Rating rubric + evidence checklist
validate.py             CLI: compare tool labels with hand labels
screener/
  extract.py            PDF -> page text -> sentences
  rules.py              All keyword patterns (edit here to tune the screener)
  classify.py           Claim detection + category rules
  evidence.py           GRI 305 / GRI 102 evidence checklist
  pipeline.py           Runs everything, builds company scores and quadrants
  validation.py         Accuracy, Cohen's kappa, confusion matrix
  llm.py                Optional Claude API mode
  climatebert.py        Optional ClimateBERT detection
demo/                   3 fictional demo reports + generator script
docs/                   Project overview PDF for the group
tests/                  Unit tests
```

## Known limitations

- Keyword rules miss unusually phrased claims and can misread irony – hence the hand validation.
- The evidence check finds whether data is **disclosed**, not whether it is **correct**.
- Text in charts and images is not read; complex multi-column layouts can split sentences.
- The EU rules target consumer marketing; applying them to reports is a **benchmark for claim quality**.
- So far tested on fictional demo reports only – real reports are the next step.

## Sources

- Directive (EU) 2024/825 (Empowering Consumers for the Green Transition), applies from 27 September 2026.
- Global Reporting Initiative (2016). *GRI 305: Emissions 2016*; (2025). *GRI 102: Climate Change 2025*.
- Stammbach, D., Webersinke, N., Bingler, J. A., Kraus, M., & Leippold, M. (2023). Environmental claim detection. *Proceedings of ACL 2023 (Short Papers)*.
- Bingler, J. A., Kraus, M., Leippold, M., & Webersinke, N. (2022). Cheap talk and cherry-picking: What ClimateBert has to say on corporate climate risk disclosures. *Finance Research Letters, 47*.
- Landis, J. R., & Koch, G. G. (1977). The measurement of observer agreement for categorical data. *Biometrics, 33*(1), 159–174.
