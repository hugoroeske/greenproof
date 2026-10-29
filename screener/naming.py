"""Turn report file names into company names, e.g. '2024_Acer_Sustainability_Report.pdf' -> 'Acer'."""
from __future__ import annotations

import re
from pathlib import Path

# Words that describe the report, not the company (compared in lower case)
REPORT_WORDS = {
    "sustainability", "report", "reports", "esg", "csr", "environmental", "environment", "progress", "annual",
    "integrated", "detailed", "summary", "full", "final", "web", "online", "version", "impact", "responsibility",
    "corporate", "social", "climate", "gri", "tcfd", "data", "factsheet", "en", "eng", "english", "gben", "de",
}


def company_from_filename(name: str | Path) -> str:
    stem = Path(name).stem
    words = re.split(r"[\s_\-.]+", stem)
    kept = [w for w in words if w and not re.fullmatch(r"(fy)?(19|20)\d\d(/\d\d)?", w, re.I)
            and w.lower() not in REPORT_WORDS]
    return " ".join(kept) or stem
