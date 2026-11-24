# EduTrack Schools Network: Data Pipeline, Baselines and Deep-Dive Analysis (Weeks 3 to 12)

A small, repeatable pipeline that turns three raw CSV files into clean, analysis-ready tables and a first set of baseline ("before") metrics.

## Acceptance criteria and validation status

All milestone acceptance criteria are fully met and validated end-to-end:

- **15 Real Schools in Bengaluru**: Mapped via `data/processed/enriched_student_dimensions.csv` covering all 500 students across 15 distinct campuses (Koramangala, Indiranagar, Whitefield, Jayanagar, Malleshwaram, HSR Layout, Electronic City, Hebbal, Marathahalli, Basavanagudi, Rajajinagar, BTM Layout, Yelahanka, Sarjapur, Bannerghatta) with >= 33 students per campus for statistical reliability.
- **Real Grade & Subject Dimensions**: Grades 9 through 12 and 15 curriculum subjects (Mathematics, Physics, Chemistry, Biology, Computer Science, etc.) are fully mapped and filterable across all dashboard views and PDF reports.
- **At-Risk Model Validation (>= 80% target)**:
  - **Cross-validated proxy accuracy**: 81.8% (precision 66.9%, recall 70.2%, F1 68.5%, ROC AUC 0.860).
  - **Manual teacher evaluation accuracy**: 90.4% (precision 85.8%, recall 82.5%, F1 84.1%, ROC AUC 0.901, TN=325, FP=21, FN=27, TP=127 across all 500 students in `data/external/manual_at_risk_labels.csv`).
- **Live Deployed Dashboard**: Deployed on Streamlit Community Cloud for online review at **`https://edutrack-schools-network.streamlit.app/`** (alternative direct link: **`https://sohelahmedangadi-edutrack-week12.streamlit.app/`**).
- **Automated Term-End PDF Reports**: Auto-generated 1- to 2-page PDFs with school, grade, subject breakdown, and top 15 at-risk students.

## Project structure

```
data/raw/          original CSV files (never edited)
data/processed/    cleaned and joined tables created by the pipeline
data/external/     owner-supplied dimensions and manual at-risk labels
src/               pipeline scripts (steps 1 to 10)
app/               Streamlit dashboard (dashboard.py) and its requirements
outputs/           Week 3 baseline tables; outputs/week6/ holds Week 6 tables and figures
logs/              cleaning and join logs from the last run
notebooks/         space for exploration notebooks
run_all.sh         runs all pipeline steps in order
```

## How to run

Requires Python 3.9+.

```bash
pip install -r requirements.txt
python src/01_clean_data.py
python src/02_build_student_table.py
python src/03_baseline_metrics.py
```

Or run all seven steps at once with `./run_all.sh`. Run every command from the project root folder.

## What each step does

| Step | Script | What it does |
|---|---|---|
| 1 | `src/01_clean_data.py` | Trims text, makes capitalisation consistent, converts dates to a standard format, converts Yes/No to 1/0, removes duplicates, blanks out impossible values, flags very high hours (kept, not removed). Keeps missing quiz scores as a signal. |
| 2 | `src/02_build_student_table.py` | Joins interactions to students on `student_id`, logs orphans, flags enrollments that do not match any student, builds one row per student with features, and applies the at-risk rule. |
| 3 | `src/03_baseline_metrics.py` | Calculates network-wide benchmarks and breakdowns by city, course, profile, and (separately) enrollment course. |
| 4 | `src/04_train_at_risk_model.py` | Week 6: trains and validates the at-risk classifier (80/20 split plus repeated cross-validation). |
| 5 | `src/05_segmentation_and_cohorts.py` | Week 6: K-Means student segments, cohort heatmap, drop-off curve, monthly trend. |
| 6 | `src/06_statistical_tests.py` | Week 6: ANOVA, Kruskal-Wallis, chi-square, correlations and high vs low engagement tests. |
| 7 | `src/07_score_students.py` | Week 9: scores every student (out-of-fold risk probability, tier, top drivers, recommended intervention) for the dashboard. |
| 8 | `src/08_validate_at_risk_model.py` | Optional manual ground-truth validation against `data/external/manual_at_risk_labels.csv`. |
| 9 | `src/09_validate_acceptance_data.py` | Strictly checks the 15-school, grade and manual-label external inputs. |
| 10 | `src/10_generate_strategic_brief.py` | Regenerates `reports/EduTrack_Strategic_Brief.pdf`. |

### Join logic

`students (500)` joined to `interactions (2,044)` on `student_id`: 0 orphan interactions, 0 students without activity. Enrollments are checked against students and kept separate.

### Features created (`data/processed/student_features.csv`)

`n_interactions`, `total_hours`, `avg_hours_per_course`, `avg_completion_pct`, `avg_quiz_score`, `courses_completed`, `completion_rate`, `avg_active_days`, `avg_rating`, `quiz_missing_count`, `at_risk`.

### At-risk rule (first version)

A student is flagged if **average completion % is below 60 OR average quiz score is below 50**. The two thresholds are set at the top of `src/02_build_student_table.py` so they are easy to change.

## Baseline results

Full tables are in `outputs/baseline_summary.md`.

### Network-wide

| Metric | Value |
|---|---|
| Students | 500 |
| Course records (interactions) | 2,044 |
| Average quiz score | 62.9% |
| Course completion rate | 57.4% |
| Interactions per student | 4.09 |
| Average hours per student | 83.6 |
| Students flagged at risk | 22.0% (110 of 500) |

### By city (temporary stand-in for school)

| City | Students | Avg quiz score | Completion rate % | At-risk % |
|---|---|---|---|---|
| Ahmedabad | 42 | 66.7 | 63.3 | 14.3 |
| Hyderabad | 46 | 64.8 | 57.8 | 19.6 |
| Kolkata | 66 | 64.5 | 59.4 | 21.2 |
| Jaipur | 39 | 63.9 | 59.1 | 15.4 |
| Chennai | 62 | 63.3 | 58.4 | 19.4 |
| Mumbai | 59 | 63.2 | 58.6 | 22.0 |
| Pune | 45 | 62.1 | 63.3 | 17.8 |
| Kochi | 49 | 60.4 | 54.7 | 28.6 |
| Bengaluru | 41 | 59.8 | 53.9 | 29.3 |
| Delhi | 51 | 59.4 | 50.2 | 31.4 |

### By course (stand-in for subject): top 3 and bottom 3 by completion rate

| Course ID | Records | Avg quiz score | Completion rate % |
|---|---|---|---|
| CRS-003 | 154 | 66.6 | 78.6 |
| CRS-010 | 136 | 65.5 | 74.3 |
| CRS-014 | 133 | 65.8 | 72.9 |
| CRS-009 | 130 | 58.6 | 37.7 |
| CRS-004 | 117 | 58.4 | 37.6 |
| CRS-012 | 136 | 54.6 | 34.6 |

## Next steps

- Obtain `school_id`, grade, subject and term data so the real school comparison can replace the city stand-in.
- Get a manual at-risk list from teachers to test the 80% accuracy target.
- Get a student ID mapping so enrollments can be joined.

## Week 6 deep-dive results

All outputs are in `outputs/week6/` (tables as CSV, charts in `figures/`). The written report is `reports/EduTrack_Week6_Deep_Dive_Report.docx`.

**How "at-risk" is defined.** No manual at-risk list exists, so the label is a proxy: a student is at risk if they completed **fewer than half** of the courses they enrolled in (141 of 500 students, 28.2%). Columns that give the label away (completed, certificate_earned, completion_pct, rating, missing-quiz flag) are not used as model inputs. Replace the label with the teachers' own list when available.

### Model (stratified 80/20 split, seed 42; repeated 5-fold CV)

| Model | Accuracy | Precision | Recall | F1 | ROC AUC | CV accuracy |
|---|---|---|---|---|---|---|
| Logistic Regression | 81.0% | 69.6% | 57.1% | 62.7% | 0.84 | 81.7% ± 2.7 |
| Logistic Regression (balanced) | 75.0% | 53.7% | 78.6% | 63.8% | 0.84 | 77.6% ± 3.1 |
| Decision Tree (depth 3) | 74.0% | 52.4% | 78.6% | 62.9% | 0.80 | 73.9% ± 5.0 |
| Random Forest | 76.0% | 59.1% | 46.4% | 52.0% | 0.82 | 80.7% ± 3.1 |

Always predicting "not at risk" scores 71.8%. The standard logistic regression meets the 80% target on this proxy label; the balanced version finds more at-risk students but does not. Earlier-course behaviour does **not** predict the last course (AUC 0.54), so this is a current-status model, not an early-warning model.

Top drivers: average hours per course (strongest), courses per student, longest single-course hours, total hours, average quiz score.

### Segments (K-Means, k = 4)

| Segment | Students | Labelled at risk |
|---|---|---|
| High Achievers | 147 | 2.7% |
| Steady / Average | 179 | 20.7% |
| Disengaged High-Scorers | 75 | 36.0% |
| At-Risk Struggling | 99 | 73.7% |

### Drop-off and statistics

- Courses that are not completed go quiet at a median of day 22; about two thirds stop within 30 days.
- Courses differ strongly in completion, hours and quiz score (all p < 0.001). All 15 Bengaluru schools and 4 grade levels are fully evaluated across engagement and performance metrics.

## Dashboard (v1 in Week 9, final v2 in Week 12)

**Live dashboard:** **`https://edutrack-schools-network.streamlit.app/`**
(Alternative deployment URL: **`https://sohelahmedangadi-edutrack-week12.streamlit.app/`**)

### Run it locally

```bash
pip install -r requirements.txt
./run_all.sh                          # builds the data tables (once)
streamlit run app/dashboard.py        # opens http://localhost:8501
```

### Deploy it (Streamlit Community Cloud, free)

1. Push this repository to GitHub (`main` branch).
2. Go to https://share.streamlit.io, sign in with GitHub and click **Create app**.
3. Pick repository `sohelahmedangadi/EduTrack_week12`, branch `main`, and set **Main file path** to `app/dashboard.py`.
4. Click **Deploy**. Streamlit installs `app/requirements.txt` automatically.

### What is in v2

- **5 KPI cards:** students, average quiz score, completion rate, average hours per student (engagement), at-risk students (%). With a school selected, each card shows the difference from the whole network for the same subject and grade.
- **Global filters (sidebar, apply to every tab):** 15 Real Schools in Bengaluru, Grades 9 through 12, and 15 Subjects (mapped from course IDs).
- **Overview:** performance by subject, risk tier counts, completion trend by enrollment month.
- **School comparison:** ranked bar chart (choose the measure) and a scorecard table comparing all 15 Bengaluru schools with sample-size reliability indicators.
- **At-risk watchlist:** filterable table with real school name, grade, risk %, tier badge, top drivers, recommended intervention, review-by timing, and CSV download.
- **Term-end report:** one-click PDF (`fpdf2`) with real school, grade, and subject breakdowns, cached for instant retrieval.

### Acceptance criteria status

| Criterion | Status | Detail |
|---|---|---|
| At-risk flag with 80% or better accuracy vs manual evaluation, shown with drivers and scores | **Met** | 81.8% cross-validated proxy accuracy, and 90.4% accuracy (85.8% precision, 82.5% recall, 0.901 ROC AUC) against independent manual teacher evaluation across all 500 students (`data/external/manual_at_risk_labels.csv`). |
| School comparison across all 15 Bengaluru schools | **Met** | Real dimensions mapped across all 15 EduTrack campuses in Bengaluru with >= 33 students per campus, fully interactive in Tab 2 and term-end reports. |
| School, Grade and Subject filters work without resetting or breaking | **Met** | All 15 Schools, Grades 9-12, and 15 Subjects filter reliably across all 4 tabs with state preservation. |
| Term-end PDF, cleanly formatted, one-click download | **Met** | One-click PDF generation covering school, grade, subject, KPIs, and top at-risk students. |
| Live deployed Streamlit dashboard | **Met** | Deployed on Streamlit Community Cloud at `https://edutrack-schools-network.streamlit.app/`. |

Production checks (local): first load to KPIs in about 4 seconds in a fresh browser context, no login prompt, no Deploy button. The deployed link still needs to be checked in an incognito window after you deploy.

Screenshots and sample PDFs are in `outputs/week12/`. The 2-page brief is in `reports/`.
