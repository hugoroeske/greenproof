"""Evidence Score: does the report actually disclose the data that would back up its climate claims?

The checklist follows GRI 305: Emissions (2016) and the new GRI 102: Climate Change (2025, applies to
reporting periods from 1 Jan 2027), plus the EU requirement that future climate claims rest on a plan
that is independently verified (Directive (EU) 2024/825).

The screener only checks whether an item is *disclosed* (and shows where). It does not check whether
the numbers are correct.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

_UNIT = re.compile(r"t\s?co2e?|tco₂e?|tonnes?|tons?\b|kt\b|mt\b|metric tons?", re.IGNORECASE)
_NUMBER = re.compile(r"\d{1,3}(?:[,.\s]\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?")


def _has_quantity(text: str) -> bool:
    """An emissions amount: a number with a unit, or a large number that is not a year or a percentage."""
    text = re.sub(r"\d+(?:[.,]\d+)?\s?(?:%|percent|per cent)", " ", text)   # targets like "-40%" are not amounts
    if re.search(r"\d[\d,.]*\s?(?:k|m|mn|million|thousand)?\s?(?:t\s?co2e?|tco₂e?|tonnes?|tons?\b|kt\b|mt\b)", text, re.IGNORECASE):
        return True
    if _UNIT.search(text) and re.search(r"\d{1,3}(?:[,.]\d{3})+", text):   # unit in a table header
        return True
    for raw in _NUMBER.findall(text):
        digits = re.sub(r"[^\d.]", "", raw)
        if not digits:
            continue
        if re.fullmatch(r"(19|20)\d\d", digits):        # a year, not an amount
            continue
        if raw.strip() in {"1", "2", "3"}:               # the scope number itself
            continue
        try:
            if float(digits.replace(",", "")) >= 100 or "," in raw or "." in raw:
                return True
        except ValueError:
            continue
    return False


def _rx(*p: str) -> re.Pattern:
    return re.compile("|".join(p), re.IGNORECASE)


@dataclass(frozen=True)
class Check:
    key: str
    label: str
    reference: str
    pattern: re.Pattern
    needs_quantity: bool = False


CHECKS: list[Check] = [
    Check("scope1", "Scope 1 emissions reported", "GRI 305-1", _rx(r"scope\s?1\b", r"direct (?:ghg )?emissions"), True),
    Check("scope2", "Scope 2 emissions reported", "GRI 305-2", _rx(r"scope\s?2\b", r"scope\s?1\s?(?:and|&|\+|,)\s?2\b", r"(?:market|location)[- ]based"), True),
    Check("scope3", "Scope 3 emissions reported", "GRI 305-3", _rx(r"scope\s?3\b", r"value chain emissions"), True),
    Check("intensity", "Emission intensity reported", "GRI 305-4", _rx(
        r"(?:emission|ghg|carbon|co2)s? intensity", r"intensity of (?:ghg|carbon|co2|emissions)",
        r"t\s?co2e? per (?:million|unit|product|pair|€|eur|usd|\$)")),
    Check("base_year", "Base year for reductions", "GRI 305-5", _rx(
        r"base(?:line)? year", r"(?:compared (?:with|to)|vs\.?|versus|from|against) (?:a |our |the )?(?:19|20)\d\d (?:baseline|base year|levels?)",
        r"(?:19|20)\d\d baseline", r"baseline of (?:19|20)\d\d",
        r"(?:emissions?|ghg|co2).{0,60}(?:compared (?:with|to)|vs\.?|versus|relative to) (?:19|20)\d\d\b")),
    Check("sbti", "Science-based / validated target", "GRI 102 · SBTi", _rx(
        r"\bsbti\b", r"science[- ]based targets? initiative", r"science[- ]based target", r"validated by")),
    Check("transition_plan", "Climate transition plan", "GRI 102 · EU 2024/825", _rx(
        r"transition plan", r"decarboni[sz]ation (?:plan|roadmap|pathway|strategy)", r"climate (?:roadmap|action plan)",
        r"net[- ]zero (?:plan|roadmap|pathway)")),
    Check("credits", "Carbon credits disclosed separately", "GRI 102", _rx(
        r"\d[\d,.]*\s?(?:k|m|mn|million|thousand)?\s?(?:t\s?co2e?|tonnes?|tons?)?\s?(?:of )?(?:carbon credits?|offsets?|verified emission reductions)",
        r"(?:carbon credits?|offsets?) (?:of|totall?ing|amounting to|equivalent to|covering) \d",
        r"(?:retired|purchased|cancelled) \d[\d,.]*\s?(?:t\s?co2e?|tonnes?)?\s?(?:of )?(?:carbon )?credits",
        r"(?:do|does|did) not (?:use|rely on|purchase|buy) (?:any )?(?:carbon )?(?:credits?|offsets?)",
        r"without (?:using |relying on )?(?:carbon )?(?:credits?|offsets?|offsetting)")),
    Check("assurance", "External assurance of GHG data", "EU 2024/825 · GRI 2-5", _rx(
        r"limited assurance", r"reasonable assurance", r"independent(?:ly)? (?:verified|assured|audited|assurance)",
        r"third[- ]party (?:verif|assur)", r"isae\s?3(?:000|410)", r"iso\s?14064-?3")),
    Check("gri_index", "GRI content index / GRI 305 reference", "GRI 1", _rx(
        r"gri content index", r"gri\s?305", r"\b305-[1-7]\b", r"gri\s?102", r"in accordance with the gri standards")),
]


@dataclass
class EvidenceHit:
    key: str
    label: str
    reference: str
    found: bool
    page: int | None = None
    snippet: str = ""


def _windows(pages: list[str], span: int = 4):
    """Yield (page, text) for every line plus the next few – table cells often sit on separate lines."""
    for page_no, text in enumerate(pages, start=1):
        lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
        for i in range(len(lines)):
            yield page_no, " ".join(lines[i:i + span])


def check_evidence(pages: list[str]) -> list[EvidenceHit]:
    hits = {c.key: EvidenceHit(c.key, c.label, c.reference, False) for c in CHECKS}
    for page_no, window in _windows(pages):
        for c in CHECKS:
            if hits[c.key].found:
                continue
            m = c.pattern.search(window)
            if not m:
                continue
            if c.needs_quantity and not _has_quantity(window[m.start():m.start() + 160]):
                continue
            start = max(0, m.start() - 40)
            hits[c.key] = EvidenceHit(c.key, c.label, c.reference, True, page_no,
                                      ("…" if start else "") + window[start:start + 160].strip() + "…")
    return [hits[c.key] for c in CHECKS]


def evidence_score(hits: list[EvidenceHit]) -> float:
    return round(100 * sum(h.found for h in hits) / len(hits), 1)
