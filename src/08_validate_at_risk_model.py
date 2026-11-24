"""
Validate the at-risk flag against an independent, manual ground-truth label.

Reads:
  data/processed/student_risk_scores.csv
  data/external/manual_at_risk_labels.csv

Expected manual_at_risk_labels.csv columns:
  student_id,at_risk_manual

The manual column must contain 0 or 1. Students missing a manual label are
excluded from validation; they are not treated as not at risk.

Writes:
  outputs/week12/manual_ground_truth_validation.txt
  outputs/week12/manual_ground_truth_validation.csv
"""
from pathlib import Path

import pandas as pd
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from sklearn.metrics import confusion_matrix, roc_auc_score


ROOT = Path(__file__).resolve().parent.parent
scores_path = ROOT / "data/processed/student_risk_scores.csv"
labels_path = ROOT / "data/external/manual_at_risk_labels.csv"
output_dir = ROOT / "outputs/week12"


scores = pd.read_csv(scores_path)
if not labels_path.exists():
    print(f"Manual ground-truth validation not run: missing {labels_path.relative_to(ROOT)}")
    raise SystemExit(0)

labels = pd.read_csv(labels_path)
required = {"student_id", "at_risk_manual"}
missing = required.difference(labels.columns)
if missing:
    raise ValueError(f"Manual labels are missing required columns: {sorted(missing)}")

labels = labels[list(required)].drop_duplicates("student_id")
if not labels["at_risk_manual"].dropna().isin([0, 1]).all():
    raise ValueError("at_risk_manual must contain only 0 or 1")

validation = scores.merge(labels, on="student_id", how="inner")
validation = validation.dropna(subset=["at_risk_manual"])
if validation.empty:
    raise ValueError("No student IDs in the scores match the manual ground-truth labels")

y_true = validation["at_risk_manual"].astype(int)
y_pred = validation["flagged"].astype(int)

metrics = pd.DataFrame([{
    "labeled_students": len(validation),
    "accuracy": accuracy_score(y_true, y_pred),
    "precision": precision_score(y_true, y_pred, zero_division=0),
    "recall": recall_score(y_true, y_pred, zero_division=0),
    "f1": f1_score(y_true, y_pred, zero_division=0),
    "roc_auc": roc_auc_score(y_true, validation["risk_probability"]),
}])

tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
lines = [
    f"Manual ground-truth validation: {len(validation)} labeled students",
    f"Accuracy: {metrics.iloc[0]['accuracy']*100:.1f}% ",
    f"Precision: {metrics.iloc[0]['precision']*100:.1f}% ",
    f"Recall: {metrics.iloc[0]['recall']*100:.1f}% ",
    f"F1: {metrics.iloc[0]['f1']*100:.1f}% ",
    f"ROC AUC: {metrics.iloc[0]['roc_auc']:.3f}",
    f"Confusion matrix: TN={tn}, FP={fp}, FN={fn}, TP={tp}",
]

output_dir.mkdir(parents=True, exist_ok=True)
(output_dir / "manual_ground_truth_validation.txt").write_text("\n".join(lines) + "\n")
metrics.to_csv(output_dir / "manual_ground_truth_validation.csv", index=False)
validation.to_csv(output_dir / "manual_ground_truth_predictions.csv", index=False)
print("\n".join(lines))
