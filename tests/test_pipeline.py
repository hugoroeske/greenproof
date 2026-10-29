import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pandas as pd

from screener import llm
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
    with pytest.raises(RuntimeError, match="401 API key invalid"):
        llm.rate_sentences(["Our shoes are eco-friendly."], api_key="bad", provider="nvidia")
