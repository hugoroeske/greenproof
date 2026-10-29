"""Optional AI mode: let a Claude model detect and rate claims with the same rubric.

Needs an Anthropic API key (https://console.anthropic.com). Without a key the screener
simply uses the rule-based mode.
"""
from __future__ import annotations

import json
import os
import re

from .classify import CATEGORIES, Rating

DEFAULT_MODEL = os.environ.get("GREENPROOF_MODEL", "claude-sonnet-5-5")
BATCH_SIZE = 25

SYSTEM_PROMPT = """You are an expert on EU green-claims rules (Directive (EU) 2024/825, applying from 27 September 2026).
You rate sentences from corporate sustainability reports.

For each sentence decide:
1. is_claim: true if the company says or suggests something positive about its OWN environmental
   impact, products, performance or plans. False for risk descriptions, regulation, general facts.
2. category (only if is_claim is true), exactly one of:
   - OFFSET_NEUTRALITY: product or company called climate/carbon neutral, compensated or climate positive based on offsets or credits.
   - GENERIC: generic praise (green, eco-friendly, sustainable, climate-friendly, kind to the planet) without a figure or proof.
   - OVERSTATED: absolute or whole-product claim (100% sustainable, zero impact, all our products ...).
   - NEUTRALITY_UNSUPPORTED: present-tense neutrality claim without saying how it is achieved.
   - FUTURE_NO_PLAN: future target without baseline, interim target, validation (e.g. SBTi), roadmap, budget or independent verification.
   - FUTURE_WITH_PLAN: future target with at least one of those plan elements.
   - SPECIFIC: measurable claim with a concrete figure and unit.
   - VAGUE: commitment or aspiration without figures and without generic praise words.
   - OTHER: environmental statement about the company that fits none of the above.
   Check the categories in this order; the first that applies wins.
3. reason: at most 15 words, quoting the decisive phrase.

Answer ONLY with a JSON array: [{"id": <int>, "is_claim": <bool>, "category": "<CATEGORY or null>", "reason": "<text>"}]"""


def _parse(text: str) -> list[dict]:
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if not match:
        raise ValueError("No JSON array in model answer")
    return json.loads(match.group(0))


def rate_sentences(sentences: list[str], api_key: str, model: str = DEFAULT_MODEL, progress=None) -> list[Rating]:
    import anthropic  # imported here so the rule-based mode works without the package

    client = anthropic.Anthropic(api_key=api_key)
    ratings: list[Rating] = [Rating(False, source="ai")] * len(sentences)
    for start in range(0, len(sentences), BATCH_SIZE):
        batch = sentences[start:start + BATCH_SIZE]
        payload = "\n".join(f"{i}: {s}" for i, s in enumerate(batch))
        response = client.messages.create(
            model=model,
            max_tokens=4000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": f"Rate these sentences:\n{payload}"}],
        )
        answer = "".join(block.text for block in response.content if getattr(block, "type", "") == "text")
        for item in _parse(answer):
            idx = start + int(item["id"])
            if not 0 <= idx < len(sentences):
                continue
            category = item.get("category") or "OTHER"
            if category not in CATEGORIES:
                category = "OTHER"
            ratings[idx] = Rating(bool(item.get("is_claim")), category, [item.get("reason", "")], source="ai")
        if progress:
            progress(min(start + BATCH_SIZE, len(sentences)) / len(sentences))
    return ratings
