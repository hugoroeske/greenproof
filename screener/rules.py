"""Word lists and patterns behind the rule-based screener.

Every pattern is a regular expression (case-insensitive). Keeping them in one file makes the
method transparent: anyone in the group can read and adjust what the tool looks for.
"""
import re


def _rx(*patterns: str) -> re.Pattern:
    return re.compile("|".join(patterns), re.IGNORECASE)


# --- Step 2: is the sentence about the environment at all? -----------------------------------
ENVIRONMENT = _rx(
    r"\bemission", r"\bemit", r"\btco2", r"\bco2e?\b", r"\bco₂", r"\bcarbon\b", r"\bclimat", r"\bgreenhouse", r"\bghg\b",
    r"\bscope [123]\b", r"\brenewabl", r"\bsolar\b", r"\bwind (?:power|energy)", r"\benergy[- ]efficien",
    r"\brecycl", r"\bsustainab", r"\bgreen(?:er)?\b", r"\beco[- ]?friendly", r"\beco\b", r"\benvironment",
    r"\bplanet\b", r"\bbiodiversity", r"\bdeforestation", r"\bwater (?:use|consumption|usage|intensity|management|stewardship|recycling)",
    r"\belectrifi", r"\bresponsibl[ey] (?:made|sourced|produced)",
    r"\bwaste\b", r"\blandfill", r"\bplastic", r"\bpackaging", r"\bcircular", r"\bnet[- ]zero",
    r"\bdecarboni", r"\bfossil", r"\bpollut", r"\bnature\b", r"\bconscious collection", r"\bclimate[- ]positive",
)

# Signals that the company speaks about itself or its products (a claim, not a general fact)
SELF_REFERENCE = _rx(
    r"\bwe\b", r"\bour\b", r"\bus\b", r"\bthe (?:company|group)\b", r"\bproducts?\b", r"\bcollection\b",
    r"\bfactor(?:y|ies)\b", r"\boperations\b", r"\bstores?\b", r"\bsuppliers?\b", r"\bbrand\b",
)

# Risk descriptions / general context – usually not a claim about own performance
CONTEXT_ONLY = _rx(
    r"\bmay (?:increase|affect|lead|result|impact)", r"\bcould (?:increase|affect|lead|result|impact)",
    r"\brisks? (?:related|associated|of)\b", r"\bregulation\b", r"\bdirective\b", r"\blaw requires\b",
    r"\bscientists\b", r"\bglobal temperatures?\b", r"\bIPCC\b",
)

# --- Step 3: categories -------------------------------------------------------------------------
NEUTRALITY = _rx(
    r"\b(?:carbon|climate|co2|co₂|ghg)[- ]neutral", r"\bnet[- ]zero\b", r"\bclimate[- ]positive",
    r"\bcarbon[- ]negative", r"\bcarbon[- ]free\b", r"\bzero[- ]carbon\b", r"\bcompensated\b",
    r"\bco2zero\b",
)
OFFSETTING = _rx(
    r"\boffset", r"\bcompensat", r"\bcarbon credits?", r"\bcredits?\b", r"\bcarbon removal projects?",
    r"\b(?:forestry|reforestation|afforestation) projects?", r"\btree[- ]planting",
)
# "We do not use offsets", "without offsetting" – offsets mentioned, but explicitly not used
NEGATED_OFFSET = _rx(
    r"\b(?:do|does|did|will) not (?:use|rely on|purchase|buy|count) (?:any )?(?:carbon )?(?:offsets?|credits?)",
    r"\bwithout (?:using |relying on |the use of |any )?(?:carbon )?(?:offsets?|credits?|offsetting|compensation)",
    r"\bno (?:carbon )?(?:offsets?|credits?)\b", r"\bnot (?:through|via|by) (?:offsetting|compensation|carbon credits?)",
    r"\bexcluding (?:carbon )?(?:offsets?|credits?)",
)
PRESENT_TENSE_STATE = _rx(r"\b(?:is|are|has been|have been|became|become|made|makes|making)\b")

GENERIC = _rx(
    r"\beco[- ]?friendly", r"\benvironment(?:ally)?[- ]friendly", r"\bclimate[- ]friendly",
    r"\bplanet[- ]friendly", r"\bnature[- ]friendly", r"\bgreen(?:er)? (?:products?|future|choice|solutions?|alternative|collection)",
    r"\bsustainable (?:products?|choice|collection|materials?|solutions?|fashion|future|brand)",
    r"\bconscious (?:choice|collection)", r"\bresponsibly made", r"\bkind to the planet",
    r"\bgood for the planet", r"\bearth[- ]friendly",
    # "green" on its own – but not technical terms like green electricity or green bonds
    r"\bgreen\b(?!\s?(?:house|electricity|energy|power|bonds?|hydrogen|steel|building|tariff|financ|loans?|certificates?))",
)

OVERSTATED = _rx(
    r"\b100 ?% (?:sustainable|green|eco|clean|natural|climate)", r"\bzero (?:environmental )?impact",
    r"\bno (?:environmental )?impact", r"\bfully (?:sustainable|green|circular|eco)",
    r"\bcompletely (?:sustainable|green|circular|eco)", r"\bentirely (?:sustainable|green|circular)",
    r"\ball (?:of )?our products\b", r"\bentire (?:product|range|portfolio)",
)

FUTURE = _rx(
    r"\bby 20[2-9]\d\b", r"\bwe (?:aim|plan|intend|strive|aspire|pledge|commit)", r"\bwe will\b",
    r"\bwe are committed to (?:reach|achiev|becom|reduc|cut)", r"\bour (?:ambition|goal|target|aim) is",
    r"\btarget(?:s|ing)? (?:to|of)\b", r"\bwill (?:be|become|reach|achieve|reduce|cut)",
)
PLAN_EVIDENCE = _rx(
    r"\b(?:vs\.?|versus|compared (?:with|to)|from a|against a|relative to) (?:a )?(?:20[0-2]\d|baseline)",
    r"\bbaseline\b", r"\binterim\b", r"\bmilestones?\b", r"\bsbti\b", r"\bscience[- ]based targets? initiative",
    r"\bvalidated\b", r"\broadmap\b", r"\btransition plan\b", r"\binvest(?:ing|ment)? (?:of )?(?:usd|eur|€|\$|\d)",
    r"\bindependent(?:ly)? (?:verif|assur|audit)", r"\bthird[- ]party (?:verif|assur|audit)",
)

NUMBER_WITH_UNIT = _rx(
    r"\d[\d,.]*\s?(?:%|percent\b|per cent\b)", r"(?:eur|usd|€|\$)\s?\d[\d,.]*",
    r"\d[\d,.]*\s?(?:(?:thousand|million|billion|mn|bn|m)\s)?(?:metric\s)?(?:t|tonnes?|tons?|kt|mt|tco2e?|tco₂e?|kg|mwh|gwh|twh|kwh|litres?|liters?|m3|m³|hectares?|ha)\b",
)

VAGUE = _rx(
    r"\bcommitted to (?:protecting|the environment|sustainab|a greener|reducing our|responsible)",
    r"\bat the (?:heart|core) of\b", r"\bwe care\b", r"\bdedicated to\b", r"\bpassionate about\b",
    r"\bstrive to\b", r"\bdoing our part\b", r"\bmaking a difference\b", r"\bresponsible business\b",
    r"\bwe believe\b", r"\bwe support\b", r"\bwe promote\b", r"\bwe encourage\b",
)


def matches(pattern: re.Pattern, text: str) -> list[str]:
    """Return the distinct matched phrases, widened to whole words (shows *why* a sentence was flagged)."""
    found: list[str] = []
    for m in pattern.finditer(text):
        start, end = m.start(), m.end()
        while start > 0 and text[start - 1].isalnum():
            start -= 1
        while end < len(text) and (text[end].isalnum() or text[end] in "₂"):
            end += 1
        phrase = text[start:end].strip(" .,;:")
        if phrase and phrase.lower() not in (f.lower() for f in found):
            found.append(phrase)
    return found


# Independent verification of reported data counts as evidence of a measurable claim
VERIFIED = _rx(r"\bindependent(?:ly)? (?:verified|assured|audited)", r"\bthird[- ]party (?:verif|assur|audit)",
               r"\blimited assurance\b", r"\breasonable assurance\b", r"\bcertified (?:to|under|by)\b")
