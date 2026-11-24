"""
Step 3: Baseline ("before") metrics.

Run from the project root:   python src/03_baseline_metrics.py
Reads : data/processed/student_features.csv
        data/processed/interactions_joined.csv
        data/processed/enrollments_checked.csv
Writes: outputs/baseline_network.csv
        outputs/baseline_by_city.csv        (city is a TEMPORARY stand-in for school)
        outputs/baseline_by_course.csv      (course_id is a stand-in for subject)
        outputs/baseline_by_profile.csv
        outputs/baseline_enrollments_by_course.csv
        outputs/baseline_summary.md
"""
import pandas as pd

students = pd.read_csv("data/processed/student_features.csv")
joined = pd.read_csv("data/processed/interactions_joined.csv")
enr = pd.read_csv("data/processed/enrollments_checked.csv")

# ---------------------------------------------------------------
# 1. Network-wide benchmarks
# ---------------------------------------------------------------
network = pd.DataFrame({
    "metric": [
        "Students",
        "Course records (interactions)",
        "Average quiz score (%)",
        "Course completion rate (%)",
        "Interactions per student",
        "Average hours per student",
        "Students flagged at risk (%)",
    ],
    "value": pd.Series([
        len(students),
        len(joined),
        round(joined["quiz_score"].mean(), 1),
        round(joined["completed"].mean() * 100, 1),
        round(students["n_interactions"].mean(), 2),
        round(students["total_hours"].mean(), 1),
        round(students["at_risk"].mean() * 100, 1),
    ], dtype=object),   # object type keeps whole numbers as 500, not 500.0
})
network.to_csv("outputs/baseline_network.csv", index=False)

# ---------------------------------------------------------------
# 2. Breakdowns
# ---------------------------------------------------------------
# By school (15 real schools across the network)
if "school_name" in students.columns:
    by_school = students.groupby("school_name").agg(
        students=("student_id", "count"),
        avg_quiz_score=("avg_quiz_score", "mean"),
        completion_rate_pct=("completion_rate", lambda s: s.mean() * 100),
        interactions_per_student=("n_interactions", "mean"),
        at_risk_pct=("at_risk", lambda s: s.mean() * 100),
    ).round(1).reset_index().sort_values("avg_quiz_score", ascending=False)
    by_school.to_csv("outputs/baseline_by_school.csv", index=False)
else:
    by_school = None

# By grade (real grade dimensions)
if "grade" in students.columns:
    by_grade = students.groupby("grade").agg(
        students=("student_id", "count"),
        avg_quiz_score=("avg_quiz_score", "mean"),
        completion_rate_pct=("completion_rate", lambda s: s.mean() * 100),
        interactions_per_student=("n_interactions", "mean"),
        at_risk_pct=("at_risk", lambda s: s.mean() * 100),
    ).round(1).reset_index().sort_values("grade")
    by_grade.to_csv("outputs/baseline_by_grade.csv", index=False)
else:
    by_grade = None

# By subject (mapped real subjects)
if "subject" in joined.columns:
    by_subject = joined.groupby(["course_id", "subject"]).agg(
        records=("interaction_id", "count"),
        avg_quiz_score=("quiz_score", "mean"),
        completion_rate_pct=("completed", lambda s: s.mean() * 100),
        avg_hours=("hours_spent", "mean"),
    ).round(1).reset_index().sort_values("completion_rate_pct", ascending=False)
    by_subject.to_csv("outputs/baseline_by_subject.csv", index=False)
else:
    by_subject = None

# By city (legacy breakdown)
by_city = students.groupby("city").agg(
    students=("student_id", "count"),
    avg_quiz_score=("avg_quiz_score", "mean"),
    completion_rate_pct=("completion_rate", lambda s: s.mean() * 100),
    interactions_per_student=("n_interactions", "mean"),
    at_risk_pct=("at_risk", lambda s: s.mean() * 100),
).round(1).reset_index().sort_values("avg_quiz_score", ascending=False)
by_city.to_csv("outputs/baseline_by_city.csv", index=False)

# By profile (student segment)
by_profile = students.groupby("profile").agg(
    students=("student_id", "count"),
    avg_quiz_score=("avg_quiz_score", "mean"),
    completion_rate_pct=("completion_rate", lambda s: s.mean() * 100),
    interactions_per_student=("n_interactions", "mean"),
    at_risk_pct=("at_risk", lambda s: s.mean() * 100),
).round(1).reset_index().sort_values("avg_quiz_score", ascending=False)
by_profile.to_csv("outputs/baseline_by_profile.csv", index=False)

# By course_id (stand-in for subject)
by_course = joined.groupby("course_id").agg(
    records=("interaction_id", "count"),
    avg_quiz_score=("quiz_score", "mean"),
    completion_rate_pct=("completed", lambda s: s.mean() * 100),
    avg_hours=("hours_spent", "mean"),
).round(1).reset_index().sort_values("completion_rate_pct", ascending=False)
by_course.to_csv("outputs/baseline_by_course.csv", index=False)

# Enrollments file (kept separate because its student IDs do not join)
enr_course = enr.groupby("course").agg(
    enrollments=("enrol_id", "count"),
    completion_rate_pct=("completed", lambda s: s.mean() * 100),
    avg_score_pct=("score_pct", "mean"),
).round(1).reset_index().sort_values("completion_rate_pct", ascending=False)
enr_course.to_csv("outputs/baseline_enrollments_by_course.csv", index=False)

# ---------------------------------------------------------------
# 3. Short written summary
# ---------------------------------------------------------------
top_city = by_city.iloc[0]
bottom_city = by_city.iloc[-1]
top_course = by_course.iloc[0]
bottom_course = by_course.iloc[-1]

lines = []
lines.append("# Baseline summary\n")
lines.append("## Network-wide\n")
lines.append(network.to_markdown(index=False) + "\n")
if by_school is not None:
    lines.append("## By School (15 Bengaluru Network Schools)\n")
    lines.append(by_school.to_markdown(index=False) + "\n")
if by_grade is not None:
    lines.append("## By Grade\n")
    lines.append(by_grade.to_markdown(index=False) + "\n")
if by_subject is not None:
    lines.append("## By Subject\n")
    lines.append(by_subject.to_markdown(index=False) + "\n")
lines.append("## By course_id, sorted by completion rate\n")
lines.append(by_course.to_markdown(index=False) + "\n")
lines.append("## By student profile\n")
lines.append(by_profile.to_markdown(index=False) + "\n")
lines.append("## Highlights\n")
if by_school is not None:
    top_school = by_school.iloc[0]
    bottom_school = by_school.iloc[-1]
    lines.append(f"- Highest average quiz score by school: {top_school['school_name']} ({top_school['avg_quiz_score']}); lowest: {bottom_school['school_name']} ({bottom_school['avg_quiz_score']}).")
lines.append(f"- Highest average quiz score by city: {top_city['city']} ({top_city['avg_quiz_score']}); lowest: {bottom_city['city']} ({bottom_city['avg_quiz_score']}).")
lines.append(f"- Highest completion rate by course: {top_course['course_id']} ({top_course['completion_rate_pct']}%); lowest: {bottom_course['course_id']} ({bottom_course['completion_rate_pct']}%).\n")

with open("outputs/baseline_summary.md", "w") as f:
    f.write("\n".join(lines))

print(network.to_string(index=False))
print()
print("Top city:", top_city["city"], "| Bottom city:", bottom_city["city"])
print("Top course:", top_course["course_id"], "| Bottom course:", bottom_course["course_id"])
