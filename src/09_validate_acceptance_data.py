"""
Validate external data needed for the 15-school, grade and manual-label criteria.

This script is intentionally strict: it never creates or guesses real school names,
grades or at-risk labels.
"""
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent.parent
dimensions_path = ROOT / "data/processed/enriched_student_dimensions.csv"
labels_path = ROOT / "data/external/manual_at_risk_labels.csv"

passed = []
failed = []

if dimensions_path.exists():
    data = pd.read_csv(dimensions_path)
    required = {"student_id", "school_id", "school_name", "grade"}
    missing = required.difference(data.columns)
    if missing:
        failed.append(f"Enrichment columns missing: {sorted(missing)}")
    else:
        duplicate_count = data["student_id"].duplicated().sum()
        school_count = data["school_name"].dropna().nunique()
        grade_count = data["grade"].dropna().nunique()
        if duplicate_count:
            failed.append(f"Enrichment has {duplicate_count} duplicate student IDs")
        if school_count != 15:
            failed.append(f"Enrichment contains {school_count} named schools; 15 are required")
        if grade_count == 0:
            failed.append("Enrichment contains no grade values")
        if not missing and duplicate_count == 0 and school_count == 15 and grade_count > 0:
            passed.append("15 real schools and grade values are present")
else:
    failed.append("Missing data/processed/enriched_student_dimensions.csv")

if labels_path.exists():
    labels = pd.read_csv(labels_path)
    if "student_id" not in labels.columns or "at_risk_manual" not in labels.columns:
        failed.append("Manual labels must contain student_id and at_risk_manual")
    else:
        values = labels["at_risk_manual"].dropna()
        if not values.isin([0, 1]).all():
            failed.append("at_risk_manual may contain only 0 or 1")
        elif len(labels) == 0:
            failed.append("Manual label file is empty")
        else:
            passed.append(f"{len(labels)} manual at-risk labels are present")
else:
    failed.append("Missing data/external/manual_at_risk_labels.csv")

print("PASSED")
for item in passed:
    print(f"- {item}")
print("FAILED")
for item in failed:
    print(f"- {item}")

raise SystemExit(1 if failed else 0)
