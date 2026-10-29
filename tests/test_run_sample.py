import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def test_run_sample_writes_both_tables(tmp_path):
    reports = tmp_path / "reports"
    reports.mkdir()
    for pdf in (ROOT / "demo").glob("*.pdf"):
        shutil.copy(pdf, reports)
    out = tmp_path / "results"
    subprocess.run([sys.executable, str(ROOT / "run_sample.py"), "--reports", str(reports), "--out", str(out)],
                   check=True, cwd=ROOT, capture_output=True)
    claims = pd.read_csv(out / "claims.csv")
    scores = pd.read_csv(out / "scores.csv")
    assert list(claims.columns) == ["company", "page", "sentence", "category", "colour", "trigger_words"]
    assert list(scores.columns) == ["company", "n_sentences", "n_claims", "score", "share_red", "share_yellow",
                                    "share_green", "share_grey"]
    assert len(scores) == 3 and (out / "review_sample.csv").exists()
