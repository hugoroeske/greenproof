"""Steps 2 + 3: detect environmental claims and rate them with transparent rules."""
from __future__ import annotations

from dataclasses import dataclass, field

from . import rules

# category -> (traffic light, points, short explanation shown in the app)
CATEGORIES: dict[str, tuple[str, int | None, str]] = {
    "OFFSET_NEUTRALITY":      ("red",    0,    "Neutrality claim based on offsets or credits – banned for products under the new EU rules"),
    "GENERIC":                ("red",    0,    "Generic green wording without a number or proof"),
    "OVERSTATED":             ("yellow", 50,   "Absolute or whole-product claim that may overstate the benefit"),
    "NEUTRALITY_UNSUPPORTED": ("yellow", 50,   "Neutrality claim without saying how it is achieved"),
    "FUTURE_NO_PLAN":         ("yellow", 50,   "Future target without baseline, interim target or verification"),
    "FUTURE_WITH_PLAN":       ("green",  100,  "Future target backed by a plan element (baseline, SBTi, roadmap, verification)"),
    "SPECIFIC":               ("green",  100,  "Measurable claim with a concrete figure"),
    "VAGUE":                  ("yellow", 50,   "Commitment without substance or figures"),
    "OTHER":                  ("grey",   None, "Environmental statement, not rated (context or description)"),
}
LIGHT_EMOJI = {"red": "🔴", "yellow": "🟡", "green": "🟢", "grey": "⚪"}


@dataclass
class Rating:
    is_claim: bool
    category: str = "OTHER"
    evidence: list[str] = field(default_factory=list)   # matched phrases = the "why"
    source: str = "rules"

    @property
    def light(self) -> str:
        return CATEGORIES[self.category][0]

    @property
    def points(self) -> int | None:
        return CATEGORIES[self.category][1]

    @property
    def explanation(self) -> str:
        return CATEGORIES[self.category][2]


def is_environmental_claim(text: str) -> bool:
    """Rule-based claim detection: environmental topic + the company talks about itself."""
    if not (rules.ENVIRONMENT.search(text) or rules.GENERIC.search(text)):
        return False
    if text.rstrip().endswith("?"):
        return False
    if rules.CONTEXT_ONLY.search(text) and not rules.SELF_REFERENCE.search(text):
        return False
    # claim-shaped wording counts even without "we/our" (e.g. "This watch is carbon neutral")
    if rules.NEUTRALITY.search(text) or rules.GENERIC.search(text) or rules.OVERSTATED.search(text):
        return True
    return bool(rules.SELF_REFERENCE.search(text))


def classify(text: str) -> Rating:
    """Assign exactly one category. Order matters: the first rule that fires wins."""
    m = rules.matches
    has_number = bool(rules.NUMBER_WITH_UNIT.search(text))

    neutral = m(rules.NEUTRALITY, text)
    offset = m(rules.OFFSETTING, text)
    future = m(rules.FUTURE, text)

    # 1. Neutrality achieved through offsets (unless the text says offsets are NOT used)
    if neutral and offset and not rules.NEGATED_OFFSET.search(text):
        return Rating(True, "OFFSET_NEUTRALITY", neutral + offset)

    # 2. Generic praise words without any figure
    generic = m(rules.GENERIC, text)
    if generic and not has_number:
        return Rating(True, "GENERIC", generic)

    # 3. Absolute claims
    overstated = m(rules.OVERSTATED, text)
    if overstated:
        return Rating(True, "OVERSTATED", overstated)

    # 4./5./6. Neutrality and future targets
    if future:
        plan = m(rules.PLAN_EVIDENCE, text)
        if plan:
            return Rating(True, "FUTURE_WITH_PLAN", future + plan)
        return Rating(True, "FUTURE_NO_PLAN", future + neutral)
    if neutral and rules.PRESENT_TENSE_STATE.search(text):
        return Rating(True, "NEUTRALITY_UNSUPPORTED", neutral)

    # 7. Measurable or independently verified claim
    if has_number or rules.VERIFIED.search(text):
        return Rating(True, "SPECIFIC", m(rules.NUMBER_WITH_UNIT, text) + m(rules.VERIFIED, text))

    # 8. Empty commitment
    vague = m(rules.VAGUE, text)
    if vague:
        return Rating(True, "VAGUE", vague)

    # 9. Not rated
    return Rating(True, "OTHER", m(rules.ENVIRONMENT, text)[:3])


def rate_sentence(text: str) -> Rating:
    if not is_environmental_claim(text):
        return Rating(False)
    return classify(text)
