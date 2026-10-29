"""Agreement between the tool and human labels (used by validate.py and the app)."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, cohen_kappa_score, confusion_matrix

from .classify import CATEGORIES

LIGHT = {cat: light for cat, (light, _, _) in CATEGORIES.items()}


@dataclass
class Agreement:
    n: int
    accuracy: float
    kappa: float
    light_accuracy: float
    labels: list[str]
    confusion: pd.DataFrame
    report: str


def agreement(df: pd.DataFrame, human_col: str = "hand_label", tool_col: str = "category") -> Agreement | None:
    data = df[[human_col, tool_col]].copy()
    data[human_col] = data[human_col].astype(str).str.strip().str.upper()
    data = data[data[human_col].isin(CATEGORIES)]
    if data.empty:
        return None
    y_true, y_pred = data[human_col], data[tool_col]
    labels = [c for c in CATEGORIES if c in set(y_true) | set(y_pred)]
    kappa = cohen_kappa_score(y_true, y_pred) if len(set(y_true) | set(y_pred)) > 1 else 1.0
    return Agreement(
        n=len(data),
        accuracy=accuracy_score(y_true, y_pred),
        kappa=float(kappa),
        light_accuracy=accuracy_score(y_true.map(LIGHT), y_pred.map(LIGHT)),
        labels=labels,
        confusion=pd.DataFrame(confusion_matrix(y_true, y_pred, labels=labels), index=labels, columns=labels),
        report=classification_report(y_true, y_pred, labels=labels, zero_division=0),
    )


def kappa_label(kappa: float) -> str:
    """Landis & Koch (1977) benchmarks for interpreting Cohen's kappa."""
    for limit, text in [(0.0, "poor"), (0.2, "slight"), (0.4, "fair"), (0.6, "moderate"), (0.8, "substantial")]:
        if kappa <= limit:
            return text
    return "almost perfect"
