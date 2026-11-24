# External acceptance datasets

These files are required to complete the real 15-school, grade and manual at-risk criteria.
They must come from the project owner or school/network system; the pipeline does not infer or fabricate them.

## `enriched_student_dimensions.csv`

Columns:

- `student_id`
- `school_id`
- `school_name`
- `grade`

Place exactly one row per student. `school_name` must identify the real school, and all 15 schools
should have a corresponding row. School and grade filters activate in the dashboard after this file
is saved under `data/processed/enriched_student_dimensions.csv`.

## `manual_at_risk_labels.csv`

Columns:

- `student_id`
- `at_risk_manual`

`at_risk_manual` must contain only `0` or `1`. Run `python src/08_validate_at_risk_model.py`
after adding this file under `data/external/manual_at_risk_labels.csv`.
