import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pandas as pd

from screener import llm
from screener.classify import Rating
from screener.pipeline import company_summary, screen_report

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "demo"


def _demo_claims():
    if not any(DEMO.glob("*.pdf")):
        subprocess.run([sys.executable, str(DEMO / "make_demo_reports.py")], check=True)
    return pd.concat([screen_report(p.read_bytes(), p.stem.split("_")[0]) for p in sorted(DEMO.glob("*.pdf"))])


def test_demo_ranking_order():
    summary = company_summary(_demo_claims())
    assert summary["company"].tolist() == ["Vireo", "Lumen", "Northpeak"]


def test_validate_script(tmp_path):
    claims = _demo_claims()
    claims["hand_label"] = claims["category"]          # perfect agreement
    path = tmp_path / "claims.csv"
    claims.to_csv(path, index=False)
    out = subprocess.run([sys.executable, str(ROOT / "validate.py"), str(path)], capture_output=True, text=True, cwd=ROOT)
    assert "Category accuracy:      100.0%" in out.stdout


def test_ai_mode_with_fake_client(monkeypatch):
    answer = [{"id": 0, "is_claim": True, "category": "GENERIC", "reason": "eco-friendly"},
              {"id": 1, "is_claim": False, "category": None, "reason": "risk"}]

    class FakeClient:
        def __init__(self, api_key):
            self.messages = SimpleNamespace(create=lambda **kw: SimpleNamespace(
                content=[SimpleNamespace(type="text", text="Here you go:\n" + json.dumps(answer))]))

    import anthropic
    monkeypatch.setattr(anthropic, "Anthropic", FakeClient)
    ratings = llm.rate_sentences(["Our shoes are eco-friendly.", "Climate change may hurt sales."], api_key="x")
    assert ratings[0].category == "GENERIC" and ratings[0].light == "red"
    assert not ratings[1].is_claim


def _fake_nvidia(monkeypatch, content, fail_first_with=None):
    import io
    import urllib.error
    import urllib.request
    calls = []

    def fake_urlopen(request, timeout=None):
        calls.append(json.loads(request.data))
        if fail_first_with and len(calls) == 1:
            raise urllib.error.HTTPError(request.full_url, fail_first_with, "err", {"Retry-After": "0"}, io.BytesIO(b"{}"))
        body = json.dumps({"choices": [{"message": {"content": content}}]}).encode()
        return SimpleNamespace(read=lambda: body, __enter__=None)

    class Resp:
        def __init__(self, r): self.r = r
        def __enter__(self): return self.r
        def __exit__(self, *a): return False

    monkeypatch.setattr(urllib.request, "urlopen", lambda req, timeout=None: Resp(fake_urlopen(req, timeout)))
    return calls


def test_nvidia_mode_with_fake_api(monkeypatch):
    answer = [{"id": 0, "is_claim": True, "category": "GENERIC", "reason": "eco-friendly"},
              {"id": 1, "is_claim": False, "category": None, "reason": "risk"}]
    content = "<think>[maybe] let me check</think>\n```json\n" + json.dumps(answer) + "\n```"
    calls = _fake_nvidia(monkeypatch, content, fail_first_with=429)
    ratings = llm.rate_sentences(["Our shoes are eco-friendly.", "Climate change may hurt sales."],
                                 api_key="nvapi-x", provider="nvidia")
    assert ratings[0].category == "GENERIC" and ratings[0].source == "ai-nvidia"
    assert not ratings[1].is_claim
    assert len(calls) == 2  # retried once after the 429
    assert calls[-1]["model"] == llm.NVIDIA_DEFAULT_MODEL and calls[-1]["temperature"] == 0


def test_nvidia_bad_key_gives_clear_error(monkeypatch):
    import pytest
    _fake_nvidia(monkeypatch, "[]", fail_first_with=401)
    with pytest.raises(RuntimeError, match=r"401 \(API key invalid\)"):
        llm.rate_sentences(["Our shoes are eco-friendly."], api_key="bad", provider="nvidia")


def test_nvidia_model_list_prefers_recommended(monkeypatch):
    import urllib.request
    catalog = {"data": [{"id": i} for i in ["nvidia/nv-embedqa-e5-v5", "zeta/some-chat-model",
                                             "deepseek-ai/deepseek-v4-flash", "meta/llama-guard-4-12b",
                                             "meta/llama-3.3-70b-instruct"]]}

    class Resp:
        def __enter__(self): return SimpleNamespace(read=lambda: json.dumps(catalog).encode())
        def __exit__(self, *a): return False

    monkeypatch.setattr(urllib.request, "urlopen", lambda req, timeout=None: Resp())
    assert llm.nvidia_chat_models("k") == ["deepseek-ai/deepseek-v4-flash", "meta/llama-3.3-70b-instruct",
                                           "zeta/some-chat-model"]


def test_company_from_filename():
    from screener.naming import company_from_filename as c
    assert c("2024_Acer_Sustainability_Report.pdf") == "Acer"
    assert c("ASUS_Detailed_2025_EN.pdf") == "ASUS"
    assert c("GBEN_Apple_Environmental_Progress_Report_2025.pdf") == "Apple"
    assert c("Lumen_Devices_2025.pdf") == "Lumen Devices"


def test_nvidia_working_models_skips_unavailable(monkeypatch):
    monkeypatch.setattr(llm, "nvidia_chat_models", lambda key: ["deepseek-ai/deepseek-v4.1-flash", "openai/gpt-oss-120b",
                                                                "01-ai/yi-large", "zeta/glm-5-chat"])
    reasons = {"openai/gpt-oss-120b": "ok", "zeta/glm-5-chat": "ok", "deepseek-ai/deepseek-v4.1-flash": "timeout"}
    monkeypatch.setattr(llm, "nvidia_model_works", lambda key, m: (reasons[m] == "ok", reasons[m]))
    working, tested = llm.nvidia_working_models("k")
    assert working == ["openai/gpt-oss-120b", "zeta/glm-5-chat"]
    assert tested["deepseek-ai/deepseek-v4.1-flash"] == "timeout" and "01-ai/yi-large" not in tested


def test_ai_mode_only_sends_environmental_sentences(monkeypatch):
    from screener import pipeline
    sent = []

    def fake_rate(texts, **kw):
        sent.extend(texts)
        return [Rating(True, "SPECIFIC", ["x"], source="ai-nvidia") for _ in texts]

    monkeypatch.setattr(llm, "rate_sentences", fake_rate)
    texts = ["Revenue grew by 8% in 2025.", "We cut Scope 1 emissions by 20% versus 2019.", "Our board met six times."]
    ratings = pipeline._rate(texts, "nvidia", "k", None, None)
    assert sent == ["We cut Scope 1 emissions by 20% versus 2019."]
    assert [r.is_claim for r in ratings] == [False, True, False]


def test_ai_batch_with_broken_json_falls_back_to_rules(monkeypatch):
    monkeypatch.setattr(llm, "_ask_nvidia", lambda payload, key, model: "Sorry, I cannot do that.")
    with __import__("pytest").raises(RuntimeError, match="JSON"):
        llm.rate_sentences(["Our shoes are eco-friendly."], api_key="k", provider="nvidia")
    calls = {"n": 0}

    def flaky(payload, key, model):
        calls["n"] += 1
        return "no json" if "eco-friendly" in payload else '[{"id": 0, "is_claim": true, "category": "SPECIFIC"}]'

    monkeypatch.setattr(llm, "_ask_nvidia", flaky)
    texts = ["Our shoes are eco-friendly."] + ["We cut emissions by 20% versus 2019."] * llm.BATCH_SIZE
    ratings = llm.rate_sentences(texts, api_key="k", provider="nvidia")
    assert ratings[0].source == "rules-fallback" and ratings[0].category == "GENERIC"
    assert ratings[-1].source == "ai-nvidia"


def test_progress_reaches_one(monkeypatch):
    monkeypatch.setattr(llm, "_ask_nvidia", lambda payload, key, model: "[]")
    seen = []
    llm.rate_sentences(["We cut emissions."] * (llm.BATCH_SIZE * 3), api_key="k", provider="nvidia", progress=seen.append)
    assert len(seen) == 3 and seen[-1] == 1.0


def test_compact_answer_format_lists_only_claims(monkeypatch):
    monkeypatch.setattr(llm, "_ask_nvidia", lambda payload, key, model: '[{"id": 1, "c": "vague", "r": "committed to"}]')
    ratings = llm.rate_sentences(["Revenue grew.", "We are committed to the planet."], api_key="k", provider="nvidia")
    assert not ratings[0].is_claim
    assert ratings[1].is_claim and ratings[1].category == "VAGUE" and ratings[1].evidence == ["committed to"]


def test_nvidia_drops_no_thinking_switch_when_model_refuses(monkeypatch):
    import io
    import urllib.error
    bodies = []

    def fake_post(body, api_key, timeout=180):
        bodies.append(body)
        if "chat_template_kwargs" in body:
            raise urllib.error.HTTPError("u", 400, "bad", {}, io.BytesIO(b"unknown field"))
        return {"choices": [{"message": {"content": "[]"}}]}

    monkeypatch.setattr(llm, "_nvidia_post", fake_post)
    llm._no_thinking_refused.discard("x/strict-model")
    assert llm._ask_nvidia("Rate these sentences:\n0: hi", "k", "x/strict-model") == "[]"
    assert "chat_template_kwargs" in bodies[0] and "chat_template_kwargs" not in bodies[1]
