"""Optional AI mode: let a language model detect and rate claims with the same rubric.

Two providers:
- "anthropic": Claude via an Anthropic API key (https://console.anthropic.com)
- "nvidia":    open models (Llama, DeepSeek, ...) via an NVIDIA API key from https://build.nvidia.com
               (OpenAI-compatible endpoint, free developer credits)
Without a key the screener simply uses the rule-based mode.
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request

from .classify import CATEGORIES, Rating

DEFAULT_MODEL = os.environ.get("GREENPROOF_MODEL", "claude-sonnet-5-5")
NVIDIA_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
NVIDIA_MODELS_URL = "https://integrate.api.nvidia.com/v1/models"
# NVIDIA retires models regularly, so the app asks the live catalog and picks the first of these that still exists.
NVIDIA_PREFERRED = [
    "meta/llama-3.3-70b-instruct",
    "deepseek-ai/deepseek-v4-flash",
    "openai/gpt-oss-120b",
    "nvidia/nemotron-3-super-120b-a12b",
    "deepseek-ai/deepseek-v4-pro",
]
NVIDIA_DEFAULT_MODEL = os.environ.get("GREENPROOF_NVIDIA_MODEL", NVIDIA_PREFERRED[0])
_NOT_CHAT = re.compile(r"embed|rerank|guard|safety|reward|vision|vlm|clip|parse|ocr|retriever|whisper|asr|tts|"
                       r"speech|audio|image|video|diffusion|flux|sdxl|cosmos|detector|pii|nemoretriever|-vl\b", re.I)


def nvidia_chat_models(api_key: str | None = None) -> list[str]:
    """Live list of chat models in the NVIDIA catalog, preferred models first."""
    headers = {"Accept": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    request = urllib.request.Request(NVIDIA_MODELS_URL, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        ids = [m["id"] for m in json.loads(response.read()).get("data", [])]
    chat = sorted({i for i in ids if not _NOT_CHAT.search(i)})
    preferred = [m for m in NVIDIA_PREFERRED if m in chat]
    return preferred + [m for m in chat if m not in preferred]
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
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)  # reasoning models think out loud first
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if not match:
        raise ValueError("No JSON array in model answer")
    return json.loads(match.group(0))


def _ask_anthropic(payload: str, api_key: str, model: str) -> str:
    import anthropic  # imported here so the rule-based mode works without the package

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=model,
        max_tokens=4000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": payload}],
    )
    return "".join(block.text for block in response.content if getattr(block, "type", "") == "text")


def _ask_nvidia(payload: str, api_key: str, model: str, retries: int = 4) -> str:
    body = json.dumps({
        "model": model,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": payload}],
        "temperature": 0,          # same input -> (almost) same answer
        "max_tokens": 8000,     # reasoning models need room to think
    }).encode()
    request = urllib.request.Request(NVIDIA_URL, data=body, method="POST", headers={
        "Authorization": f"Bearer {api_key}", "Content-Type": "application/json", "Accept": "application/json"})
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                data = json.loads(response.read())
            return data["choices"][0]["message"]["content"] or ""
        except urllib.error.HTTPError as err:
            if err.code == 429 and attempt < retries:   # rate limit: wait and try again
                time.sleep(float(err.headers.get("Retry-After") or 15))
                continue
            detail = err.read().decode(errors="ignore")[:300]
            hint = {401: "API key invalid", 402: "NVIDIA credits used up", 404: "model name not found",
                    410: "model retired by NVIDIA, pick another model"}.get(err.code, "")
            raise RuntimeError(f"NVIDIA API error {err.code} {hint}: {detail}") from err
    raise RuntimeError("NVIDIA API: rate limit, try again in a minute")


def rate_sentences(sentences: list[str], api_key: str, model: str | None = None, progress=None,
                   provider: str = "anthropic") -> list[Rating]:
    ask = _ask_nvidia if provider == "nvidia" else _ask_anthropic
    model = model or (NVIDIA_DEFAULT_MODEL if provider == "nvidia" else DEFAULT_MODEL)
    source = "ai-nvidia" if provider == "nvidia" else "ai"
    ratings: list[Rating] = [Rating(False, source=source)] * len(sentences)
    for start in range(0, len(sentences), BATCH_SIZE):
        batch = sentences[start:start + BATCH_SIZE]
        payload = "Rate these sentences:\n" + "\n".join(f"{i}: {s}" for i, s in enumerate(batch))
        for item in _parse(ask(payload, api_key, model)):
            try:
                idx = start + int(item["id"])
            except (KeyError, TypeError, ValueError):
                continue
            if not start <= idx < start + len(batch):
                continue
            category = item.get("category") or "OTHER"
            if category not in CATEGORIES:
                category = "OTHER"
            ratings[idx] = Rating(bool(item.get("is_claim")), category, [str(item.get("reason", ""))], source=source)
        if progress:
            progress(min(start + BATCH_SIZE, len(sentences)) / len(sentences))
    return ratings
