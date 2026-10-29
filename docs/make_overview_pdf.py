"""Builds the 3-page English project overview for the group (GreenProof_Project_Overview.pdf)."""
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (KeepTogether, ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "GreenProof_Project_Overview.pdf"

GREEN = colors.HexColor("#1F5E3B")
GREEN_L = colors.HexColor("#E8F1EC")
TEXT = colors.HexColor("#1E2626")
MUTED = colors.HexColor("#5B6766")
RED, YELLOW, OK, GREY = (colors.HexColor(c) for c in ("#C62828", "#F9A825", "#2E7D32", "#9E9E9E"))

ss = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=ss["Title"], fontName="Helvetica-Bold", fontSize=24, leading=28, textColor=GREEN, alignment=TA_LEFT, spaceAfter=2)
SUB = ParagraphStyle("SUB", parent=ss["Normal"], fontName="Helvetica", fontSize=12, leading=16, textColor=MUTED, spaceAfter=10)
H2 = ParagraphStyle("H2", parent=ss["Heading2"], fontName="Helvetica-Bold", fontSize=13.5, leading=17, textColor=GREEN, spaceBefore=10, spaceAfter=5)
BODY = ParagraphStyle("BODY", parent=ss["Normal"], fontName="Helvetica", fontSize=10, leading=14.2, textColor=TEXT, spaceAfter=5)
SMALL = ParagraphStyle("SMALL", parent=BODY, fontSize=8.5, leading=11.5, textColor=MUTED)
CELL = ParagraphStyle("CELL", parent=BODY, fontSize=9, leading=12, spaceAfter=0)
CELLB = ParagraphStyle("CELLB", parent=CELL, fontName="Helvetica-Bold")
CELLW = ParagraphStyle("CELLW", parent=CELLB, textColor=colors.white)


def P(text, style=BODY):
    return Paragraph(text, style)


def bullets(items, style=BODY):
    return ListFlowable([ListItem(P(i, style), leftIndent=12, bulletColor=GREEN) for i in items],
                        bulletType="bullet", start="•", leftIndent=12, bulletFontSize=9)


def box(flowables, bg=GREEN_L, width=None):
    t = Table([[flowables]], colWidths=[width or 170 * mm])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), bg), ("LEFTPADDING", (0, 0), (-1, -1), 10),
                           ("RIGHTPADDING", (0, 0), (-1, -1), 10), ("TOPPADDING", (0, 0), (-1, -1), 8),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
    return t


def grid(data, widths, header=True, extra=()):
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    style = [("VALIGN", (0, 0), (-1, -1), "TOP"), ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#C9D6D4")),
             ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
             ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]
    if header:
        style += [("BACKGROUND", (0, 0), (-1, 0), GREEN)]
    t.setStyle(TableStyle(style + list(extra)))
    return t


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(20 * mm, 12 * mm, "GreenProof – project overview · Sustainability and ESG Data Analytics, NTPU, Fall 2026")
    canvas.drawRightString(190 * mm, 12 * mm, f"Page {doc.page}")
    canvas.restoreState()


story = []

# ---------------------------------------------------------------- title
story += [
    P("GreenProof", H1),
    P("A greenwashing screener for corporate sustainability reports – project overview for our group", SUB),
    box([P("<b>In one sentence:</b> We build a tool that reads sustainability reports, finds every environmental "
           "claim and checks whether it would hold up under the new EU green-claims rules – and whether the company "
           "backs it up with real climate data. So we can compare how honest companies really are.", BODY)]),
]

# ---------------------------------------------------------------- 1 greenwashing
story += [
    P("1. What is greenwashing?", H2),
    P("<b>Greenwashing</b> means giving a misleading impression of how environmentally friendly a company, product "
      "or service is. It is rarely an outright lie. Usually it is a claim that sounds good but cannot be measured, "
      "leaves out the important part, or relies on someone else's effort. Typical patterns:"),
    bullets([
        "<b>Vague words</b> – \"eco-friendly\", \"green\", \"sustainable\" without any number or proof.",
        "<b>Offsetting</b> – calling a product \"carbon neutral\" because the company bought carbon credits, "
        "not because it cut its own emissions.",
        "<b>Overstating</b> – \"zero impact\" or \"100% sustainable\" when only one part of the product improved.",
        "<b>Empty promises</b> – \"net zero by 2040\" without a baseline, interim targets or a plan.",
    ]),
    Spacer(1, 4),
    box([P("<b>Real cases</b>", CELLB),
         P("• <b>KLM (2024):</b> The District Court of Amsterdam ruled on 20 March 2024 that 15 of 19 challenged "
           "statements in KLM's \"Fly Responsibly\" campaign were misleading – e.g. vague sustainability claims and "
           "an overly rosy picture of offsetting and sustainable aviation fuel.", CELL),
         P("• <b>Apple (2025):</b> The Frankfurt Regional Court stopped Apple from advertising three Apple Watch "
           "models as \"CO<sub>2</sub>-neutral\". The neutrality relied on offset projects; one plantation in Paraguay "
           "was only leased until 2029. (Ruling not yet final when reported in August 2025.)", CELL)]),
]

# ---------------------------------------------------------------- 2 why
story += [
    P("2. Why this project – and why now?", H2),
    P("<b>New EU rules since 27 September 2026.</b> The Directive \"Empowering Consumers for the Green "
      "Transition\" (EU 2024/825) now applies in all EU member states. Among other things it:"),
    bullets([
        "bans claims that a product has a neutral, reduced or positive climate impact <b>based on offsetting</b>;",
        "bans <b>generic environmental claims</b> that cannot be backed by recognised excellent environmental performance;",
        "bans claims that present a benefit for the <b>whole product or company</b> when it applies only to a part;",
        "requires <b>future performance claims</b> (e.g. \"net zero by 2040\") to rest on a detailed, realistic "
        "implementation plan that is verified by an independent expert.",
    ]),
    P("<b>Nobody checks systematically.</b> A second law that would have required companies to verify green "
      "claims before publishing them (the Green Claims Directive) stalled in June 2025. Research also shows the "
      "problem is real: Bingler et al. (2022) found that much corporate climate disclosure is \"cheap talk\" – many "
      "words, little measurable substance."),
    P("<b>Our contribution:</b> a transparent, repeatable screening method that turns hundreds of report "
      "sentences into a comparable score – something investors, auditors and consumers cannot easily do by hand."),
]

# ---------------------------------------------------------------- 3 ESG
esg = grid([
    [P("ESG pillar", CELLW), P("Link to our project", CELLW)],
    [P("<b>E – Environment</b>", CELL), P("We assess the quality of environmental disclosure: are claims about emissions, "
                                          "energy, materials and packaging specific and verifiable?", CELL)],
    [P("<b>G – Governance</b>", CELL), P("Honest reporting is a governance issue: misleading claims create legal and "
                                         "reputational risk and show weak internal control over what a company publishes.", CELL)],
    [P("<b>Investors &amp; ESG data</b>", CELL), P("ESG ratings and sustainable funds rely heavily on what companies report "
                                                  "about themselves. If claims are inflated, capital flows to the wrong companies.", CELL)],
    [P("<b>Data analytics</b>", CELL), P("The course focus: we turn unstructured text (PDF reports) into structured, "
                                        "comparable data with rules and AI – and measure how reliable that is.", CELL)],
], [40 * mm, 130 * mm])
story += [KeepTogether([P("3. How does this relate to ESG?", H2), esg])]

# ---------------------------------------------------------------- 4 tool
flow = Table([[P("<b>1. Upload</b><br/>Sustainability reports (PDF)", CELL), P("→", CELLB),
               P("<b>2. Extract</b><br/>Sentences with page numbers", CELL), P("→", CELLB),
               P("<b>3. Detect</b><br/>Which sentences are environmental claims?", CELL), P("→", CELLB),
               P("<b>4. Rate</b><br/>One of 9 categories per claim", CELL), P("→", CELLB),
               P("<b>5. Compare</b><br/>Score 0–100 and ranking", CELL)]],
             colWidths=[29 * mm, 6 * mm, 29 * mm, 6 * mm, 33 * mm, 6 * mm, 30 * mm, 6 * mm, 25 * mm])
flow.setStyle(TableStyle([("BACKGROUND", (0, 0), (0, 0), GREEN_L), ("BACKGROUND", (2, 0), (2, 0), GREEN_L),
                          ("BACKGROUND", (4, 0), (4, 0), GREEN_L), ("BACKGROUND", (6, 0), (6, 0), GREEN_L),
                          ("BACKGROUND", (8, 0), (8, 0), GREEN_L), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                          ("ALIGN", (1, 0), (1, 0), "CENTER"), ("TOPPADDING", (0, 0), (-1, -1), 6),
                          ("BOTTOMPADDING", (0, 0), (-1, -1), 6), ("LEFTPADDING", (0, 0), (-1, -1), 4),
                          ("RIGHTPADDING", (0, 0), (-1, -1), 4)]))

cats = [
    ("Red", RED, "Offset-based neutrality", "\"This watch is carbon neutral thanks to carbon credits.\""),
    ("Red", RED, "Generic claim without proof", "\"Our collection is eco-friendly and kind to the planet.\""),
    ("Yellow", YELLOW, "Overstated / absolute claim", "\"All our products have zero environmental impact.\""),
    ("Yellow", YELLOW, "Neutrality claim, basis unclear", "\"Our offices are carbon neutral.\""),
    ("Yellow", YELLOW, "Future target without plan", "\"We aim to become net zero by 2040.\""),
    ("Yellow", YELLOW, "Vague commitment", "\"Sustainability is at the heart of everything we do.\""),
    ("Green", OK, "Future target with plan", "\"-50% Scope 1+2 by 2030 vs. 2019, validated by the SBTi.\""),
    ("Green", OK, "Specific, measurable claim", "\"78% of our factory electricity was renewable in 2025.\""),
    ("Grey", GREY, "Not rated (context)", "\"Climate change may increase extreme weather events.\""),
]
rows = [[P("", CELLW), P("Category", CELLW), P("Example", CELLW)]]
extra = []
for i, (label, col, name, ex) in enumerate(cats, start=1):
    rows.append([P(f"<b>{label}</b>", ParagraphStyle("c", parent=CELLB, textColor=colors.white)), P(name, CELL), P(ex, CELL)])
    extra.append(("BACKGROUND", (0, i), (0, i), col))
cat_table = grid(rows, [18 * mm, 52 * mm, 100 * mm], extra=extra)

ev_items = [("Scope 1 emissions", "GRI 305-1"), ("Scope 2 emissions", "GRI 305-2"), ("Scope 3 emissions", "GRI 305-3"),
            ("Emission intensity", "GRI 305-4"), ("Base year for reductions", "GRI 305-5"),
            ("Science-based / validated target", "GRI 102 · SBTi"), ("Climate transition plan", "GRI 102 · EU 2024/825"),
            ("Carbon credits shown separately", "GRI 102"), ("External assurance of GHG data", "EU 2024/825"),
            ("GRI content index", "GRI 1")]
ev_rows = [[P("Evidence item", CELLW), P("Reference", CELLW), P("Evidence item", CELLW), P("Reference", CELLW)]]
for i in range(5):
    a, b = ev_items[i], ev_items[i + 5]
    ev_rows.append([P(a[0], CELL), P(a[1], CELL), P(b[0], CELL), P(b[1], CELL)])
evidence_table = grid(ev_rows, [52 * mm, 33 * mm, 52 * mm, 33 * mm])

matrix = Table([
    [P("", CELL), P("<b>Evidence &lt; 50</b>", CELL), P("<b>Evidence ≥ 50</b>", CELL)],
    [P("<b>Claim quality ≥ 50</b>", CELL), P("Careful claims, thin data", CELL), P("<b>Credible</b>", CELLW)],
    [P("<b>Claim quality &lt; 50</b>", CELL), P("<b>Greenwashing risk</b>", CELLW), P("Good data, weak claims", CELL)],
], colWidths=[40 * mm, 55 * mm, 55 * mm])
matrix.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#C9D6D4")),
                            ("BACKGROUND", (2, 1), (2, 1), OK), ("BACKGROUND", (1, 2), (1, 2), RED),
                            ("BACKGROUND", (1, 1), (1, 1), colors.HexColor("#FFF4D6")),
                            ("BACKGROUND", (2, 2), (2, 2), colors.HexColor("#FFF4D6")),
                            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 6),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 6), ("LEFTPADDING", (0, 0), (-1, -1), 6)]))

story += [
    P("4. What we build: the GreenProof screener", H2),
    flow, Spacer(1, 8),
    P("Each claim gets one category (first match wins). Green = 100 points, yellow = 50, red = 0; the "
      "<b>Claim Quality Score</b> is the average per company. The tool always shows <i>why</i> a sentence was "
      "flagged (the decisive words), so every rating can be checked. This is the <b>Claim Quality Score</b> (talk)."),
    cat_table, Spacer(1, 6),
    P("<b>Second layer – Evidence Score (0–100).</b> Wording alone is not enough, so the tool also checks whether "
      "the report discloses the climate data that would back the claims up. Ten items, 10 points each, each with "
      "the page where it was found:"),
    evidence_table, Spacer(1, 6),
    P("<b>Talk vs. evidence.</b> Both scores place every company in a simple matrix – the core visual of our results:"),
    matrix, Spacer(1, 6),
    P("<b>Three modes:</b> (1) transparent keyword rules – free and offline; (2) detection with the published "
      "research model ClimateBERT (Stammbach et al., 2023); (3) detection and rating by an AI model (Claude API). "
      "Comparing the modes is itself a result for our report. A working version (v0.2) already exists: Python + "
      "Streamlit dashboard with upload, ranking, talk-vs-evidence matrix, company detail, built-in hand validation "
      "and CSV export."),
]

# ---------------------------------------------------------------- 5 research
story += [
    P("5. Research question and method", H2),
    box([P("<b>Research question:</b> How do large companies differ in the quality of their environmental claims – "
           "and how many of these claims would be problematic under the EU rules that apply from September 2026?", BODY)]),
    Spacer(1, 4),
    bullets([
        "<b>Sample:</b> 5–10 companies from one industry (e.g. sportswear or consumer electronics), latest "
        "sustainability report each – so the comparison is fair.",
        "<b>Screening:</b> run all reports through GreenProof; compare Claim Quality, Evidence and red-flag shares.",
        "<b>Validation:</b> each of us labels the same 50–100 claims by hand (blind, directly in the app); we report "
        "accuracy and Cohen's kappa, interpreted with Landis &amp; Koch (1977).",
        "<b>Deep dive:</b> for 2–3 companies we check selected claims against reported numbers (e.g. emissions trend vs. target).",
    ]),
    P("<b>Limits we state openly:</b> the EU rules target consumer marketing, so we use them as a benchmark for claim "
      "quality, not as a legal check. The tool judges <i>how</i> claims are worded, not whether the numbers are true; "
      "text in charts and images is not read."),
]

# ---------------------------------------------------------------- 6 course fit + next steps
fit = grid([
    [P("Course deliverable", CELLW), P("What we show", CELLW)],
    [P("<b>Case study</b> (25 + 10 min)", CELL), P("One company from our sample in depth: background, business model "
                                                    "canvas, its green claims – e.g. Apple and the Apple Watch case.", CELL)],
    [P("<b>Midterm project</b> (10 min)", CELL), P("Introduction: background, motivation, research question, expected "
                                                    "contributions; first screening results.", CELL)],
    [P("<b>Final project</b> (20 min)", CELL), P("Full study: literature, method, results, conclusions – with product "
                                                  "name, system architecture and a <b>live demo</b> of GreenProof.", CELL)],
], [45 * mm, 125 * mm])
story += [KeepTogether([P("6. How it fits our course deliverables", H2), fit])]
story += [
    P("7. Next steps", H2),
    bullets([
        "Agree on the industry and the 5–10 companies; collect their latest sustainability reports (PDF).",
        "Run the reports through GreenProof and fine-tune the rules on real documents.",
        "Split roles: literature &amp; background · data collection · tool &amp; validation · case study &amp; slides.",
        "Optional: get an Anthropic API key to compare the rule-based mode with the AI mode.",
    ]),
    Spacer(1, 6),
    P("<b>Sources</b>", CELLB),
    P("Directive (EU) 2024/825 of 28 February 2024 (Empowering Consumers for the Green Transition), applies from 27 September 2026. · "
      "Climate Focus (2026): Beyond \"carbon neutral\" – new EU rules for green claims apply from September 2026. · "
      "Osborne Clarke (2024): District Court Amsterdam declares green claims of KLM misleading and unlawful. · "
      "ZDFheute (26 Aug 2025): Gericht untersagt Apple-Watch-Werbung. · "
      "Packaging Europe (Jun 2025): Green Claims Directive grinds to a halt. · "
      "Global Reporting Initiative (2016). GRI 305: Emissions; (2025). GRI 102: Climate Change. · "
      "Landis, J. R., &amp; Koch, G. G. (1977). The measurement of observer agreement for categorical data. <i>Biometrics, 33</i>(1), 159–174. · "
      "Bingler, J. A., Kraus, M., Leippold, M., &amp; Webersinke, N. (2022). Cheap talk and cherry-picking: What ClimateBert has to say "
      "on corporate climate risk disclosures. <i>Finance Research Letters, 47</i>. · "
      "Stammbach, D., Webersinke, N., Bingler, J. A., Kraus, M., &amp; Leippold, M. (2023). Environmental claim detection. "
      "<i>Proceedings of ACL 2023</i>.", SMALL),
]

story[-2:] = [KeepTogether(story[-2:])]          # keep the source list in one block

doc = SimpleDocTemplate(str(OUT), pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=18 * mm,
                        bottomMargin=20 * mm, title="GreenProof – Project Overview", author="Hugo Friedrich Röske")
doc.build(story, onFirstPage=footer, onLaterPages=footer)
print("written", OUT)
