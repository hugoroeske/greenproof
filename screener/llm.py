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
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib.error
import urllib.request

from .classify import CATEGORIES, Rating, rate_sentence

DEFAULT_MODEL = os.environ.get("GREENPROOF_MODEL", "claude-sonnet-5-5")
NVIDIA_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
NVIDIA_MODELS_URL = "https://integrate.api.nvidia.com/v1/models"
# NVIDIA retires models regularly and its catalog also lists models an account cannot call.
# So the app tests candidates with a tiny request and only offers models that answer.
NVIDIA_PREFERRED = [
    "deepseek-ai/deepseek-v4.1-flash",
    "openai/gpt-oss-120b",
    "google/gemma-4-31b-it",
    "openai/gpt-oss-20b",
    "nvidia/nemotron-3-super-120b-a12b",
    "qwen/qwen3-next-80b-a3b-instruct",
    "moonshotai/kimi-k2-instruct",
    "meta/llama-4-maverick-17b-128e-instruct",
    "mistralai/mistral-medium-3-instruct",
    "deepseek-ai/deepseek-v4-flash",
]
NVIDIA_DEFAULT_MODEL = os.environ.get("GREENPROOF_NVIDIA_MODEL", NVIDIA_PREFERRED[0])
_NOT_CHAT = re.compile(r"embed|rerank|guard|safety|reward|vision|vlm|clip|parse|ocr|retriever|whisper|asr|tts|"
                       r"speech|audio|image|video|diffusion|flux|sdxl|cosmos|detector|pii|nemoretriever|-vl\b|"
                       r"coder|code|math|fuyu|kosmos|deplot|paligemma|neva|translate", re.I)
# Only test current model families; the catalog still lists many retired ones (HTTP 404).
_MODERN = re.compile(r"deepseek-v4|deepseek-v3\.[1-9]|gemma-4|gpt-oss|nemotron-3|qwen3|llama-4|kimi-k2|glm-[45]|"
                     r"mistral-(?:medium|large)-3|magistral|phi-4", re.I)
NVIDIA_TEST_TIMEOUT = 90   # free models often need a while to wake up


def _nvidia_post(body: dict, api_key: str, timeout: int = 180) -> dict:
    request = urllib.request.Request(NVIDIA_URL, data=json.dumps(body).encode(), method="POST", headers={
        "Authorization": f"Bearer {api_key}", "Content-Type": "application/json", "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read())


def nvidia_chat_models(api_key: str | None = None) -> list[str]:
    """Chat models in the NVIDIA catalog, preferred models first (not yet tested)."""
    headers = {"Accept": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    request = urllib.request.Request(NVIDIA_MODELS_URL, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        ids = [m["id"] for m in json.loads(response.read()).get("data", [])]
    chat = sorted({i for i in ids if not _NOT_CHAT.search(i)})
    preferred = [m for m in NVIDIA_PREFERRED if m in chat]
    return preferred + [m for m in chat if m not in preferred]


def nvidia_model_works(api_key: str, model: str) -> tuple[bool, str]:
    """Send a tiny request. Returns (works, reason): 'ok', 'timeout' or 'HTTP <code>'."""
    messages = [{"role": "user", "content": "Say OK"}]
    for _ in range(2):
        try:
            _nvidia_post(_nvidia_body(model, messages, 5), api_key, timeout=NVIDIA_TEST_TIMEOUT)
            return True, "ok"
        except urllib.error.HTTPError as err:
            if err.code == 400 and model not in _no_thinking_refused:
                _no_thinking_refused.add(model)
                continue
            return False, f"HTTP {err.code}"
        except Exception as err:  # timeout, cold start, network
            return False, "timeout" if "timed out" in str(err).lower() or isinstance(err, TimeoutError) \
                else type(err).__name__
    return False, "HTTP 400"


def nvidia_working_models(api_key: str, max_tests: int = 8) -> tuple[list[str], dict[str, str]]:
    """Test current catalog models in parallel. Returns (working models, fastest first; model -> result)."""
    try:
        catalog = nvidia_chat_models(api_key)
    except Exception:
        catalog = []
    candidates = [m for m in NVIDIA_PREFERRED if m in catalog or not catalog]
    candidates += [m for m in catalog if m not in candidates and _MODERN.search(m)]
    candidates = candidates[:max_tests]

    def timed(model: str) -> tuple[bool, str, float]:
        t0 = time.time()
        ok, reason = nvidia_model_works(api_key, model)
        return ok, reason, time.time() - t0

    results: dict[str, tuple[bool, str, float]] = {}
    with ThreadPoolExecutor(max_workers=len(candidates) or 1) as pool:
        futures = {pool.submit(timed, m): m for m in candidates}
        for future in as_completed(futures):
            results[futures[future]] = future.result()
    working = sorted((m for m in candidates if results[m][0]),
                     key=lambda m: (round(results[m][2] * 2) / 2, candidates.index(m)))
    tested = {m: (f"ok ({results[m][2]:.1f} s)" if results[m][0] else results[m][1]) for m in candidates}
    return working, tested


BATCH_SIZE = 40   # sentences per request

SYSTEM_PROMPT = """You are an expert on EU green-claims rules (Directive (EU) 2024/825, applying from 27 September 2026).
You rate numbered sentences from corporate sustainability reports. Answer fast and briefly, do not explain.

A sentence is a CLAIM if the company says or suggests something positive about its OWN environmental
impact, products, performance or plans. Risk descriptions, regulation and general facts are not claims.

For every CLAIM pick the first category that applies, in this order:
OFFSET_NEUTRALITY: called climate/carbon neutral, compensated or climate positive based on offsets or credits.
GENERIC: generic praise (green, eco-friendly, sustainable, climate-friendly, kind to the planet) without a figure or proof.
OVERSTATED: absolute or whole-product claim (100% sustainable, zero impact, all our products ...).
NEUTRALITY_UNSUPPORTED: present-tense neutrality claim without saying how it is achieved.
FUTURE_NO_PLAN: future target without baseline, interim target, validation (e.g. SBTi), roadmap, budget or verification.
FUTURE_WITH_PLAN: future target with at least one of those plan elements.
SPECIFIC: measurable claim with a concrete figure and unit.
VAGUE: commitment or aspiration without figures and without generic praise words.
OTHER: environmental statement about the company that fits none of the above.

Answer ONLY with a JSON array that lists the CLAIMS (leave out every sentence that is not a claim):
[{"id": <int>, "c": "<CATEGORY>", "r": "<decisive phrase, max 6 words>"}]
If no sentence is a claim, answer []."""


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


NO_THINKING = {"chat_template_kwargs": {"thinking": False, "enable_thinking": False}}
_no_thinking_refused: set[str] = set()   # models that reject the switch (HTTP 400)


def _nvidia_body(model: str, messages: list[dict], max_tokens: int) -> dict:
    body = {"model": model, "messages": messages, "temperature": 0, "max_tokens": max_tokens}
    if model not in _no_thinking_refused:
        body.update(NO_THINKING)          # reasoning models answer much faster without "thinking"
    return body


def _ask_nvidia(payload: str, api_key: str, model: str, retries: int = 4) -> str:
    messages = [{"role": "system", "content": "/no_think\n" + SYSTEM_PROMPT}, {"role": "user", "content": payload}]
    for attempt in range(retries + 1):
        try:
            data = _nvidia_post(_nvidia_body(model, messages, 3000), api_key, timeout=300)
            return data["choices"][0]["message"]["content"] or ""
        except urllib.error.HTTPError as err:
            if err.code == 400 and model not in _no_thinking_refused:   # model does not know the switch
                _no_thinking_refused.add(model)
                continue
            if err.code == 429 and attempt < retries:   # rate limit: wait and try again
                time.sleep(float(err.headers.get("Retry-After") or 15))
                continue
            detail = err.read().decode(errors="ignore")[:300]
            hint = {401: "API key invalid", 402: "NVIDIA credits used up",
                    404: "model not available for your account, pick another model",
                    410: "model retired by NVIDIA, pick another model"}.get(err.code, "")
            raise RuntimeError(f"NVIDIA API error {err.code} ({hint}): {detail}") from err
    raise RuntimeError("NVIDIA API: rate limit, try again in a minute")


def rate_sentences(sentences: list[str], api_key: str, model: str | None = None, progress=None,
                   provider: str = "anthropic") -> list[Rating]:
    ask = _ask_nvidia if provider == "nvidia" else _ask_anthropic
    model = model or (NVIDIA_DEFAULT_MODEL if provider == "nvidia" else DEFAULT_MODEL)
    source = "ai-nvidia" if provider == "nvidia" else "ai"
    ratings: list[Rating] = [Rating(False, source=source)] * len(sentences)
    starts = list(range(0, len(sentences), BATCH_SIZE))

    def run(start: int) -> tuple[int, list[dict] | None]:
        payload = "Rate these sentences:\n" + "\n".join(
            f"{i}: {s}" for i, s in enumerate(sentences[start:start + BATCH_SIZE]))
        for _ in range(2):                      # one retry if the answer is not valid JSON
            try:
                return start, _parse(ask(payload, api_key, model))
            except (ValueError, json.JSONDecodeError):
                continue
        return start, None                      # give up on this batch, rules take over below

    done, failed = 0, 0
    workers = 8 if provider == "nvidia" else 4  # requests run in parallel, well below the rate limits
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for future in as_completed([pool.submit(run, st) for st in starts]):
            start, items = future.result()
            size = min(BATCH_SIZE, len(sentences) - start)
            if items is None:
                failed += 1
                for idx in range(start, start + size):
                    r = rate_sentence(sentences[idx])
                    ratings[idx] = Rating(r.is_claim, r.category, r.evidence, source="rules-fallback")
                items = []
            for item in items:
                if not isinstance(item, dict):
                    continue
                try:
                    idx = start + int(item["id"])
                except (KeyError, TypeError, ValueError):
                    continue
                if not start <= idx < start + size:
                    continue
                category = str(item.get("c") or item.get("category") or "OTHER").upper()
                if category not in CATEGORIES:
                    category = "OTHER"
                reason = str(item.get("r") or item.get("reason") or "")
                ratings[idx] = Rating(bool(item.get("is_claim", True)), category, [reason], source=source)
            done += 1
            if progress:
                progress(done / len(starts))
    if failed == len(starts) and starts:
        raise RuntimeError(f"The model {model} never answered in the expected JSON format – pick another model.")
    return ratings
