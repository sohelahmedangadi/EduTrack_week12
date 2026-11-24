"""
Step 2: Validate the joins and build the student-level feature table.

Run from the project root:   python src/02_build_student_table.py
Reads : data/processed/*_clean.csv
Writes: data/processed/interactions_joined.csv   (one row per student + course)
        data/processed/student_features.csv      (one row per student)
        data/processed/enrollments_checked.csv   (enrollments + student_found flag)
        logs/02_join_log.txt
"""
from pathlib import Path
import pandas as pd

# --- Rule settings for the first at-risk flag (change these to experiment) ---
LOW_COMPLETION = 60   # average completion % below this  -> at risk
LOW_QUIZ = 50         # average quiz score below this    -> at risk

log = []


def note(text):
    print(text)
    log.append(text)


COURSE_SUBJECT_MAP = {
    "CRS-001": "Mathematics",
    "CRS-002": "Physics",
    "CRS-003": "Chemistry",
    "CRS-004": "Biology",
    "CRS-005": "English Language",
    "CRS-006": "English Literature",
    "CRS-007": "Computer Science",
    "CRS-008": "History & Civics",
    "CRS-009": "Geography",
    "CRS-010": "Economics",
    "CRS-011": "Environmental Science",
    "CRS-012": "Mathematics Advanced",
    "CRS-013": "Data Science & AI",
    "CRS-014": "Physical Education",
    "CRS-015": "Art & Design",
}

students = pd.read_csv("data/processed/students_clean.csv")
inter = pd.read_csv("data/processed/interactions_clean.csv")
enr = pd.read_csv("data/processed/enrollments_clean.csv")

# ---------------------------------------------------------------
# 1. Join check: interactions -> students (key: student_id)
# ---------------------------------------------------------------
orphans = ~inter["student_id"].isin(students["student_id"])
note(f"interactions with no matching student (orphans): {orphans.sum()} -> removed")
inter = inter[~orphans]

no_activity = ~students["student_id"].isin(inter["student_id"])
note(f"students with no interactions: {no_activity.sum()}")

joined = inter.merge(students, on="student_id", how="left")
joined["subject"] = joined["course_id"].map(COURSE_SUBJECT_MAP).fillna(joined["course_id"])

# Enriched dimensions (15 real schools and grades)
dim_path = Path("data/processed/enriched_student_dimensions.csv")
if not dim_path.exists():
    dim_path = Path("data/external/enriched_student_dimensions.csv")

dimensions = None
if dim_path.exists():
    dimensions = pd.read_csv(dim_path)[["student_id", "school_id", "school_name", "grade"]].drop_duplicates("student_id")
    joined = joined.merge(dimensions, on="student_id", how="left")
    note(f"enriched dimensions joined: {dimensions['school_name'].nunique()} schools, {dimensions['grade'].nunique()} grades")

note(f"interactions_joined: {len(joined)} rows")

# ---------------------------------------------------------------
# 2. Join check: enrollments -> students
#    Enrollment IDs look like ST-01894, student IDs look like STU-0001.
#    They do not match, so we do NOT force a join. We flag it instead.
# ---------------------------------------------------------------
enr["student_found"] = enr["student_id"].isin(students["student_id"])
note(f"enrollments matching a student: {enr['student_found'].sum()} of {len(enr)}")
note(f"enrollments orphaned (no matching student): {(~enr['student_found']).sum()} -> kept separately, not joined")

# ---------------------------------------------------------------
# 3. Student-level features
# ---------------------------------------------------------------
features = joined.groupby("student_id").agg(
    n_interactions=("interaction_id", "count"),       # courses/records per student
    total_hours=("hours_spent", "sum"),
    avg_hours_per_course=("hours_spent", "mean"),
    avg_completion_pct=("completion_pct", "mean"),
    avg_quiz_score=("quiz_score", "mean"),            # our "assessment score"
    courses_completed=("completed", "sum"),
    avg_active_days=("active_days", "mean"),
    avg_rating=("rating", "mean"),
    quiz_missing_count=("quiz_missing", "sum"),
).reset_index()

# completion rate = courses completed / courses taken
features["completion_rate"] = features["courses_completed"] / features["n_interactions"]

# add student details back (city, profile, joined_date, school, grade)
student_details = students[["student_id", "city", "profile", "joined_date"]]
if dimensions is not None:
    student_details = student_details.merge(dimensions, on="student_id", how="left")

features = features.merge(student_details, on="student_id", how="left")

# ---------------------------------------------------------------
# 4. First rule-based at-risk flag
# ---------------------------------------------------------------
features["low_completion"] = (features["avg_completion_pct"] < LOW_COMPLETION).astype(int)
features["low_quiz"] = (features["avg_quiz_score"] < LOW_QUIZ).astype(int)
features["at_risk"] = ((features["low_completion"] == 1) | (features["low_quiz"] == 1)).astype(int)

note(f"at-risk rule: avg completion < {LOW_COMPLETION} OR avg quiz < {LOW_QUIZ}")
note(f"students flagged at risk: {features['at_risk'].sum()} of {len(features)} ({features['at_risk'].mean()*100:.1f}%)")

# ---------------------------------------------------------------
# 5. Save
# ---------------------------------------------------------------
joined.to_csv("data/processed/interactions_joined.csv", index=False)
features.round(2).to_csv("data/processed/student_features.csv", index=False)
enr.to_csv("data/processed/enrollments_checked.csv", index=False)

with open("logs/02_join_log.txt", "w") as f:
    f.write("\n".join(log) + "\n")
