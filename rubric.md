# Rating rubric – GreenProof greenwashing screener

The screener rates every **environmental claim** in a sustainability report.
A claim is a statement in which a company says or suggests something positive about its own
environmental impact, products or plans (e.g. "Our packaging is 100% recyclable").

The categories follow the EU rules on green claims that apply from **27 September 2026**
(Directive (EU) 2024/825, "Empowering Consumers for the Green Transition", amending the
Unfair Commercial Practices Directive 2005/29/EC).

> Important: these rules target consumer-facing marketing. A sustainability report is not
> advertising, so the screener measures **claim quality and greenwashing risk**, not legal
> compliance. A red flag means "would be problematic under the new EU standard", not "illegal".

## Traffic lights and score

| Light | Points | Meaning |
|---|---|---|
| 🟢 Green | 100 | Specific, measurable, verifiable |
| 🟡 Yellow | 50 | Needs more evidence or a plan |
| 🔴 Red | 0 | Typical greenwashing pattern under the new EU rules |
| ⚪ Grey | – | Environmental statement that is not rated (context, risk description) |

**Claim Quality Score (0–100)** = average points of all rated (non-grey) claims of a company.

## Categories (checked in this order – the first match wins)

### 1. 🔴 OFFSET_NEUTRALITY – neutrality based on offsetting
Claim that a product or the company is climate/carbon/CO₂ neutral, compensated or climate positive,
**based on carbon credits or offset projects**. Banned for products under the new rules.
- 🔴 "This watch is carbon neutral thanks to high-quality carbon credits."
- 🔴 "We offset all remaining emissions, making our shipping climate neutral."

### 2. 🔴 GENERIC – generic environmental claim without proof
Vague praise words such as *green, eco-friendly, environmentally friendly, climate-friendly,
sustainable, planet-friendly, conscious, responsible* **without a number or evidence in the same sentence**.
- 🔴 "Our new collection is eco-friendly and kind to the planet."
- 🔴 "We offer sustainable products for a greener future."

### 3. 🟡 OVERSTATED – absolute or whole-product claim
Absolute words that overstate the benefit: *100% sustainable, zero impact, no impact, fully green,
completely sustainable, entire product, all our products*.
- 🟡 "All our products have zero environmental impact."
- 🟡 "The store is fully sustainable."

### 4. 🟡 NEUTRALITY_UNSUPPORTED – neutrality claim, basis unclear
Present-tense neutrality claim ("is carbon neutral", "net zero today") without saying how.
- 🟡 "Our offices are carbon neutral."

### 5. 🟡 FUTURE_NO_PLAN – future target without a plan
Future promise (*by 2030, we aim, we commit, we will, our ambition, pledge*) **without** plan
evidence such as a baseline year, interim target, validation (e.g. SBTi), roadmap, investment
or independent verification.
- 🟡 "We aim to become net zero by 2040."
- 🟡 "We will make our packaging more sustainable."

### 6. 🟢 FUTURE_WITH_PLAN – future target with a plan
Future target **with** at least one plan element (baseline, interim target, SBTi validation,
roadmap, budget, independent verification).
- 🟢 "We will cut Scope 1 and 2 emissions by 50% by 2030 versus 2019, a target validated by the SBTi."

### 7. 🟢 SPECIFIC – measurable claim
Statement with a concrete figure and unit (%, tonnes, tCO₂e, MWh, litres …).
- 🟢 "In 2025, 78% of the electricity used in our factories came from renewable sources."
- 🟢 "We reduced water use per product by 12% compared with 2022."

### 8. 🟡 VAGUE – environmental commitment without substance
Commitment or aspiration without numbers and without generic praise words.
- 🟡 "We are committed to protecting the environment."
- 🟡 "Sustainability is at the heart of everything we do."

### 9. ⚪ OTHER – not rated
Environmental statement that is not a claim about the company's own performance
(e.g. risk description, regulation, general facts).
- ⚪ "Climate change may increase the frequency of extreme weather events."

## Evidence Score (0–100) – does the company back up its claims?

The Claim Quality Score measures **talk** (how claims are worded). The Evidence Score measures
whether the report **discloses the climate data** that would back those claims up. Each item found
= 10 points. The app shows the page where each item was found.

| # | Item | Reference |
|---|---|---|
| 1 | Scope 1 emissions reported (with an amount) | GRI 305-1 |
| 2 | Scope 2 emissions reported (with an amount) | GRI 305-2 |
| 3 | Scope 3 emissions reported (with an amount) | GRI 305-3 |
| 4 | Emission intensity reported | GRI 305-4 |
| 5 | Base year for reductions | GRI 305-5 |
| 6 | Science-based / validated target | GRI 102 · SBTi |
| 7 | Climate transition plan | GRI 102 · EU 2024/825 |
| 8 | Carbon credits disclosed separately (amount, or "not used") | GRI 102 |
| 9 | External assurance of GHG data | EU 2024/825 · GRI 2-5 |
| 10 | GRI content index / GRI 305 reference | GRI 1 |

GRI 305: Emissions (2016) is replaced by GRI 102: Climate Change (2025) for reporting periods from
1 January 2027; items 6–8 already reflect the new standard. The check looks for *disclosure*, it does
not verify whether the numbers are correct.

**Overall score** = average of Claim Quality Score and Evidence Score.

**Talk vs. evidence matrix** (cut-off 50 points on each axis):

| | Evidence < 50 | Evidence ≥ 50 |
|---|---|---|
| **Claim quality ≥ 50** | Careful claims, thin data | ✅ Credible |
| **Claim quality < 50** | 🚩 Greenwashing risk | Good data, weak claims |

## Hand validation (for the report)

1. Open the **Validate** view in the app (or export the claims as CSV).
2. Each team member labels the same random sample of 50–100 claims using the category names above –
   **without looking at the tool's label** (keep "Show the tool's rating" switched off).
3. The app shows accuracy, Cohen's kappa and the confusion matrix immediately. For a CSV, run
   `python validate.py claims.csv`.
4. Interpret kappa with Landis & Koch (1977): 0.41–0.60 moderate, 0.61–0.80 substantial, above 0.80 almost perfect.

## Sources
- Directive (EU) 2024/825 of the European Parliament and of the Council of 28 February 2024 amending
  Directives 2005/29/EC and 2011/83/EU as regards empowering consumers for the green transition
  through better protection against unfair practices and through better information.
- Global Reporting Initiative (2016). GRI 305: Emissions 2016.
- Global Reporting Initiative (2025). GRI 102: Climate Change 2025.
- Landis, J. R., & Koch, G. G. (1977). The measurement of observer agreement for categorical data. *Biometrics, 33*(1), 159–174.
