"""Create three FICTIONAL demo sustainability reports (PDF) to test the screener.

All companies and figures are invented. Run:  python demo/make_demo_reports.py
"""
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table

OUT = Path(__file__).parent

REPORTS = {
    "Northpeak_Apparel_2025.pdf": ("Northpeak Apparel – Sustainability Report 2025", [
        ("Our approach", [
            "Sustainability is at the heart of everything we do at Northpeak.",
            "Our new Earth collection is eco-friendly and kind to the planet.",
            "We offer sustainable products for a greener future.",
            "All our products have zero environmental impact thanks to our innovative design.",
            "We are committed to protecting the environment for future generations.",
        ]),
        ("Climate", [
            "Our hoodies are carbon neutral because we offset all production emissions through certified forestry projects.",
            "Our online shop is climate neutral thanks to carbon credits purchased from a partner in Brazil.",
            "We aim to become net zero by 2040.",
            "We will make our packaging more sustainable in the coming years.",
            "Climate change may increase the frequency of extreme weather events in our sourcing regions.",
            "In 2025, 22% of the electricity used in our offices came from renewable sources.",
        ]),
        ("Materials", [
            "Our flagship store in Berlin is fully sustainable.",
            "We believe that responsibly made fashion is the future of our industry.",
            "We use recycled polyester in selected products.",
        ]),
    ]),
    "Lumen_Devices_2025.pdf": ("Lumen Devices – Environmental Report 2025", [
        ("Overview", [
            "Lumen Devices designs smartphones and wearables for customers in 40 countries.",
            "We reduced our total Scope 1 and 2 emissions by 31% compared with 2019.",
            "Our smartwatch is carbon neutral.",
            "We will cut Scope 3 emissions by 40% by 2030 versus 2019, a target validated by the SBTi.",
            "We aim to use 100% renewable electricity across our supply chain by 2030.",
        ]),
        ("Products", [
            "Our new phone uses 25% recycled aluminium in the enclosure.",
            "We offset remaining emissions from business travel, making our corporate travel climate neutral.",
            "Our devices are designed to be environmentally friendly.",
            "We recovered 4,800 tonnes of electronic waste through our take-back programme in 2025.",
            "We are dedicated to building a circular economy.",
        ]),
        ("Supply chain", [
            "Our suppliers consumed 1.9 million MWh of renewable electricity for Lumen production in 2025.",
            "We will publish a transition plan with interim milestones for 2027 and 2030.",
            "Regulation on electronic waste is expected to tighten in the European Union.",
        ]),
    ]),
    "Vireo_Footwear_2025.pdf": ("Vireo Footwear – Sustainability Report 2025", [
        ("Climate performance", [
            "Our Scope 1 and 2 emissions fell to 41,200 tCO2e in 2025, down 46% from our 2019 baseline.",
            "We will reduce absolute Scope 3 emissions by 42% by 2030 compared with 2019, as validated by the Science Based Targets initiative.",
            "In 2025, 91% of the electricity in our tier 1 factories came from renewable sources.",
            "Our emissions data for 2025 was independently verified by a third-party assurance provider.",
        ]),
        ("Materials and water", [
            "Recycled materials accounted for 58% of the polyester used in our shoes in 2025.",
            "We reduced water use per pair by 18% compared with 2022.",
            "We aim to eliminate virgin plastic from our consumer packaging by 2027, with an interim target of 60% in 2026.",
            "We are committed to responsible water management in our supplier factories.",
        ]),
        ("Outlook", [
            "Our roadmap foresees an investment of EUR 120 million in factory electrification until 2030.",
            "Rising carbon prices could increase costs for our suppliers in Asia.",
        ]),
    ]),
}


KPI_TABLES = {
    "Vireo_Footwear_2025.pdf": [
        ["GHG emissions (GRI 305)", "Unit", "2019 (base year)", "2025"],
        ["Scope 1 emissions", "tCO2e", "31,500", "18,400"],
        ["Scope 2 emissions (market-based)", "tCO2e", "45,100", "22,800"],
        ["Scope 3 emissions", "tCO2e", "1,610,000", "1,240,000"],
        ["Emission intensity", "tCO2e per EUR million revenue", "21.7", "12.4"],
    ],
    "Lumen_Devices_2025.pdf": [
        ["Indicator", "2024", "2025"],
        ["Employees", "12,400", "12,950"],
        ["Revenue (EUR m)", "3,210", "3,480"],
    ],
    "Northpeak_Apparel_2025.pdf": [
        ["Indicator", "2024", "2025"],
        ["Stores", "310", "342"],
        ["Revenue (EUR m)", "1,150", "1,260"],
    ],
}

EXTRA_SECTIONS = {
    "Vireo_Footwear_2025.pdf": ("Governance of climate data", [
        "Our decarbonisation roadmap sets out interim milestones for 2027 and 2030 and is reviewed annually by the board.",
        "We do not use carbon credits to meet our reduction targets.",
        "Our Scope 1, 2 and 3 data received limited assurance from an independent auditor under ISAE 3410.",
        "This report has been prepared in accordance with the GRI Standards; the GRI content index is on page 4.",
    ]),
    "Lumen_Devices_2025.pdf": ("Reporting", [
        "Our Scope 1 and 2 emissions amounted to 182,000 tCO2e in 2025.",
        "This report references the GRI Standards, including GRI 305-1 and 305-2.",
    ]),
}


def build(filename: str, title: str, sections):
    styles = getSampleStyleSheet()
    story = [Paragraph(title, styles["Title"]),
             Paragraph("FICTIONAL DEMO REPORT – company and all figures are invented for testing.", styles["Italic"]),
             Spacer(1, 12)]
    for i, (heading, sentences) in enumerate(sections):
        story.append(Paragraph(heading, styles["Heading2"]))
        story.append(Paragraph(" ".join(sentences), styles["BodyText"]))
        story.append(Spacer(1, 10))
        if i == 0:
            story.append(Table(KPI_TABLES[filename]))
        if i < len(sections) - 1:
            story.append(PageBreak())
    SimpleDocTemplate(str(OUT / filename), pagesize=A4).build(story)


if __name__ == "__main__":
    for name, (title, sections) in REPORTS.items():
        if name in EXTRA_SECTIONS:
            sections = sections + [EXTRA_SECTIONS[name]]
        build(name, title, sections)
        print("created", OUT / name)
