"""Compare the tool's categories with your own hand labels.

Usage:  python validate.py greenproof_claims.csv

The CSV comes from the app (view "All claims" or "Validate"). Fill the column `hand_label` with the
category you think is right (same names as in rubric.md). Rows without a hand label are ignored.
"""
import sys

import pandas as pd

from screener.validation import agreement, kappa_label


def main(path: str) -> None:
    result = agreement(pd.read_csv(path))
    if result is None:
        sys.exit("No valid hand labels found. Use the category names from rubric.md.")
    print(f"Labelled claims: {result.n}\n")
    print(f"Category accuracy:      {result.accuracy:.1%}")
    print(f"Cohen's kappa:          {result.kappa:.2f} ({kappa_label(result.kappa)} agreement)")
    print(f"Traffic-light accuracy: {result.light_accuracy:.1%}\n")
    print(result.report)
    print("Confusion matrix (rows = your label, columns = tool):")
    print(result.confusion.to_string())


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
