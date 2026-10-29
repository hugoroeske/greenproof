"""Optional: use the published ClimateBERT model to detect environmental claims.

Model: climatebert/environmental-claims (Stammbach et al., ACL 2023), trained on ~2,600
expert-labelled sentences from sustainability reports, earnings calls and annual reports.
Needs `pip install transformers torch` and internet access to Hugging Face on first use.
The rule-based categories are still used for the rating step.
"""
from __future__ import annotations

MODEL_NAME = "climatebert/environmental-claims"
_pipe = None


def available() -> bool:
    try:
        import transformers  # noqa: F401
        import torch  # noqa: F401
        return True
    except ImportError:
        return False


def detect_claims(sentences: list[str], threshold: float = 0.5, progress=None) -> list[bool]:
    global _pipe
    if _pipe is None:
        from transformers import pipeline
        _pipe = pipeline("text-classification", model=MODEL_NAME, truncation=True, max_length=256)
    flags: list[bool] = []
    step = 32
    for start in range(0, len(sentences), step):
        for out in _pipe(sentences[start:start + step]):
            label = str(out["label"]).lower()
            positive = label in {"yes", "label_1", "1", "claim", "environmental claim"}
            flags.append(positive and out["score"] >= threshold)
        if progress:
            progress(min(start + step, len(sentences)) / len(sentences))
    return flags
