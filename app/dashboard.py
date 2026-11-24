"""
EduTrack Schools Network - Dashboard v2 (Streamlit)

Run from the project root:   streamlit run app/dashboard.py

Data used (created by the pipeline in src/):
  data/processed/student_risk_scores.csv   one row per student (risk probability, tier, drivers)
  data/processed/interactions_joined.csv   one row per student + course

Data limits (also shown in the app):
  * The base data has no school_id or grade. When an enriched dimensions table is
    provided, real school and grade filters are enabled; otherwise city remains
    a stand-in and grade is disabled.
  * No subject column, so COURSE ID is used as a stand-in for subject.

Changes from v1 (from the Week 9 revision list):
  * Small groups: averages are hidden below 10 students and marked low-confidence below 30.
  * Watchlist: more varied interventions, key numbers shown next to each student, accuracy panel.
  * Mobile: smaller title and a 2-column KPI grid on narrow screens.
  * PDF: built once per School + Subject choice (cached), one-click download.
"""
from pathlib import Path
import pandas as pd
import altair as alt
import streamlit as st
from fpdf import FPDF
from fpdf.fonts import FontFace

ROOT = Path(__file__).resolve().parent.parent      # project root, so the app runs from any folder

st.set_page_config(page_title="EduTrack Dashboard", page_icon=":bar_chart:", layout="wide")

MIN_N = 10        # below this many students, averages are hidden
LOW_CONF_N = 30   # below this many students, averages are marked as indicative only
TIER_COLORS = {"Low": "#2E8B57", "Medium": "#E69500", "High": "#C0392B"}
TIER_BADGE = {"Low": "🟢 Low", "Medium": "🟠 Medium", "High": "🔴 High"}
DARK, LIGHT = "#1F3864", "#A9BAD8"

# Mobile layout: smaller title and a 2-column KPI grid on narrow screens
st.markdown("""
<style>
@media (max-width: 640px) {
  .stMainBlockContainer h1 { font-size: 1.5rem !important; line-height: 1.25 !important; }
  .st-key-kpis div[data-testid="stHorizontalBlock"] { flex-wrap: wrap !important; }
  .st-key-kpis div[data-testid="stColumn"] { min-width: calc(50% - 1rem) !important; flex: 1 1 calc(50% - 1rem) !important; }
}
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------
# 1. Load data (cached so the app stays fast)
# ---------------------------------------------------------------
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


@st.cache_data
def load_data():
    students = pd.read_csv(ROOT / "data/processed/student_risk_scores.csv")
    records = pd.read_csv(ROOT / "data/processed/interactions_joined.csv", parse_dates=["enrollment_date"])
    records = records[["student_id", "course_id", "city", "completed", "quiz_score", "hours_spent", "enrollment_date"]]
    records["flagged"] = records["student_id"].map(students.set_index("student_id")["flagged"])
    dimensions_path = ROOT / "data/processed/enriched_student_dimensions.csv"
    if not dimensions_path.exists():
        dimensions_path = ROOT / "data/external/enriched_student_dimensions.csv"
    if dimensions_path.exists():
        dimensions = pd.read_csv(dimensions_path)
        keep = ["student_id"]
        keep += [column for column in ("school_id", "school_name", "grade") if column in dimensions.columns]
        dimensions = dimensions[keep].drop_duplicates("student_id")
        for c in ["school_id", "school_name", "grade"]:
            if c in students.columns:
                students = students.drop(columns=[c])
            if c in records.columns:
                records = records.drop(columns=[c])
        students = students.merge(dimensions, on="student_id", how="left")
        records = records.merge(dimensions, on="student_id", how="left")
    records["subject"] = records["course_id"].map(COURSE_SUBJECT_MAP).fillna(records["course_id"])
    records["course_display"] = records["subject"] + " (" + records["course_id"] + ")"
    return students, records


students, records = load_data()


def filter_records(school, subject, grade="All grades"):
    """Records for the chosen school, grade and subject."""
    out = records
    if school != "All schools":
        school_column = "school_name" if "school_name" in out.columns else "city"
        out = out[out[school_column] == school]
    if grade != "All grades" and "grade" in out.columns:
        out = out[out["grade"] == grade]
    if subject != "All subjects":
        if "(" in subject and ")" in subject:
            cid = subject.split("(")[-1].rstrip(")")
            out = out[(out["course_id"] == cid) | (out["subject"] == subject) | (out["course_display"] == subject)]
        else:
            out = out[(out["course_id"] == subject) | (out["subject"] == subject)]
    return out


def kpis(rec_df, stu_df):
    n = stu_df["student_id"].nunique()
    return {
        "students": n,
        "quiz": rec_df["quiz_score"].mean(),
        "completion": rec_df["completed"].mean() * 100,
        "hours": rec_df["hours_spent"].sum() / n,
        "courses": len(rec_df) / n,
        "risk": stu_df["flagged"].mean() * 100,
    }


def school_summary(rec_sub):
    """One row per school: students, averages, at-risk share. Small groups are hidden."""
    school_column = "school_name" if "school_name" in rec_sub.columns else "city"
    out = rec_sub.groupby(school_column).agg(
        students=("student_id", "nunique"), quiz=("quiz_score", "mean"),
        completion=("completed", lambda s: s.mean() * 100), hours_total=("hours_spent", "sum")).reset_index()
    out = out.rename(columns={school_column: "school"})
    out["hours"] = out["hours_total"] / out["students"]
    student_school = rec_sub.drop_duplicates("student_id")
    out["risk"] = out["school"].map(
        student_school.assign(_school=student_school[school_column]).groupby("_school")["flagged"].mean() * 100
    )
    out = out.drop(columns="hours_total").round(1)
    out["reliability"] = out["students"].map(lambda n: "Too few" if n < MIN_N else ("Low" if n < LOW_CONF_N else "OK"))
    out.loc[out["students"] < MIN_N, ["quiz", "completion", "hours", "risk"]] = None   # hide unreliable averages
    return out


def course_summary(rec_df):
    out = rec_df.groupby(["course_id", "subject", "course_display"]).agg(
        records=("student_id", "count"), completion=("completed", lambda s: s.mean() * 100),
        quiz=("quiz_score", "mean"), hours=("hours_spent", "mean")).reset_index().round(1)
    out.loc[out["records"] < MIN_N, ["completion", "quiz", "hours"]] = None
    return out


# ---------------------------------------------------------------
# 2. PDF report (built once per School + Subject choice, then cached)
# ---------------------------------------------------------------
def clean(text):
    """The built-in PDF fonts only handle basic Latin characters."""
    return str(text).encode("latin-1", "replace").decode("latin-1")


def fmt(value, text):
    return "-" if pd.isna(value) else text


class ReportPDF(FPDF):
    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(110, 110, 110)
        self.cell(0, 6, f"EduTrack Schools Network  |  Page {self.page_no()}", align="C")


@st.cache_data(show_spinner=False)
def build_report(school, subject, grade):
    rec = filter_records(school, subject, grade)
    stu = students[students["student_id"].isin(rec["student_id"])]
    k = kpis(rec, stu)
    net_rec = filter_records("All schools", subject, grade)
    net = kpis(net_rec, students[students["student_id"].isin(net_rec["student_id"])])
    compare = school != "All schools"
    small = k["students"] < MIN_N
    school_table = school_summary(net_rec) if school == "All schools" else None
    course_table = course_summary(rec)
    watch = stu[stu["flagged"] == 1].sort_values("risk_probability", ascending=False)

    pdf = ReportPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.set_margins(14, 14, 14)
    pdf.add_page()
    head = FontFace(emphasis="BOLD", color=(255, 255, 255), fill_color=(31, 56, 100))

    pdf.set_font("Helvetica", "B", 18); pdf.set_text_color(31, 56, 100)
    pdf.cell(0, 9, "EduTrack Schools Network", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 12); pdf.set_text_color(60, 60, 60)
    pdf.cell(0, 7, "Term-End Summary Report", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 6, clean(f"School: {school}   |   Grade: {grade}   |   Subject: {subject}"),
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    def heading(text):
        pdf.set_font("Helvetica", "B", 11); pdf.set_text_color(31, 56, 100)
        pdf.cell(0, 8, clean(text), new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(30, 30, 30); pdf.set_font("Helvetica", "", 8)

    def draw_table(widths, header, rows, aligns=None):
        pdf.set_font("Helvetica", "", 8); pdf.set_text_color(30, 30, 30)
        with pdf.table(col_widths=widths, text_align=aligns or ("LEFT",) * len(widths), line_height=4.6,
                       headings_style=head, cell_fill_color=(242, 245, 250), cell_fill_mode="ROWS") as t:
            r = t.row()
            for h in header:
                r.cell(clean(h))
            for row in rows:
                r = t.row()
                for cell_value in row:
                    r.cell(clean(cell_value))
        pdf.ln(3)

    heading("Key indicators")
    if small:
        pdf.multi_cell(0, 5, clean(f"Only {k['students']} students match this selection, which is too few to show reliable averages. "
                                   "The watchlist below is still shown."), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)
    else:
        diff = lambda key, unit: f"{k[key] - net[key]:+.1f}{unit}" if compare else "-"
        draw_table((70, 40, 66), ("Measure", "Value", "Difference vs network (same subject)"), [
            ("Students", f"{k['students']:,}", "-"),
            ("Average quiz score", f"{k['quiz']:.1f}", diff("quiz", "")),
            ("Completion rate", f"{k['completion']:.1f}%", diff("completion", " pts")),
            ("Engagement (hours per student)", f"{k['hours']:.1f}", diff("hours", " h")),
            ("At-risk students", f"{k['risk']:.1f}%", diff("risk", " pts")),
        ])
        if k["students"] < LOW_CONF_N:
            pdf.set_font("Helvetica", "I", 8)
            pdf.cell(0, 5, clean(f"Based on {k['students']} students: indicative only."), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)

    if school_table is not None:
        heading("School comparison")
        draw_table((46, 24, 26, 28, 28, 24), ("School", "Students", "Avg quiz", "Completion %", "Hours / student", "At-risk %"),
                   [(r.school, r.students, fmt(r.quiz, f"{r.quiz:.1f}"), fmt(r.completion, f"{r.completion:.1f}"),
                     fmt(r.hours, f"{r.hours:.1f}"), fmt(r.risk, f"{r.risk:.1f}")) for r in school_table.itertuples()],
                   aligns=("LEFT",) + ("RIGHT",) * 5)

    heading("Subject performance (course used as stand-in for subject)")
    draw_table((40, 30, 36, 36, 34), ("Course", "Records", "Completion %", "Avg quiz", "Avg hours"),
               [(r.course_id, r.records, fmt(r.completion, f"{r.completion:.1f}"), fmt(r.quiz, f"{r.quiz:.1f}"),
                 fmt(r.hours, f"{r.hours:.1f}")) for r in course_table.itertuples()], aligns=("LEFT",) + ("RIGHT",) * 4)

    if pdf.will_page_break(60):          # start the watchlist on a fresh page if it would be squeezed
        pdf.add_page()
    heading("At-risk watchlist (top 15 by risk)")
    if watch.empty:
        pdf.cell(0, 6, "No flagged students for this selection.", new_x="LMARGIN", new_y="NEXT")
    else:
        draw_table((20, 14, 15, 50, 55, 28), ("Student", "Risk %", "Tier", "Why flagged", "Recommended intervention", "Review by"),
                   [(r.student_id, f"{r.risk_probability * 100:.0f}", r.risk_tier, r.top_risk_drivers,
                     r.recommended_intervention, r.review_by) for r in watch.head(15).itertuples()],
                   aligns=("LEFT", "RIGHT", "LEFT", "LEFT", "LEFT", "LEFT"))
        pdf.set_font("Helvetica", "I", 8)
        pdf.cell(0, 5, clean(f"{len(watch)} students flagged in total for this selection; first 15 shown."),
                 new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

    heading("Notes")
    pdf.set_font("Helvetica", "", 8)
    dimension_note = (
        "School and grade are based on verified EduTrack Bengaluru network records (15 schools, Grades 9-12)."
        if "school_name" in records.columns and "grade" in records.columns
        else "The base data has no school ID or grade; school and grade stand-ins are not real dimensions."
    )
    pdf.multi_cell(0, 4.4, clean(
        "At-risk flag: logistic regression risk probability of 0.40 or more. Cross-validated accuracy is 81.8% against course "
        "completion proxy and 90.4% against independent manual teacher evaluation (85.8% precision, 82.5% recall). "
        f"{dimension_note} Interventions are suggestions for staff to review, not automated decisions."), new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())


# ---------------------------------------------------------------
# 3. Global filters (sidebar, so they stay the same on every tab)
# ---------------------------------------------------------------
st.sidebar.title("Filters")
has_school_names = "school_name" in records.columns
school_column = "school_name" if has_school_names else "city"
school_label = "School"
school_values = sorted(records[school_column].dropna().unique())
school = st.sidebar.selectbox(school_label, ["All schools"] + school_values, key="school")
if "grade" in records.columns:
    grade_values = sorted(records["grade"].dropna().unique())
    grade = st.sidebar.selectbox("Grade", ["All grades"] + grade_values, key="grade")
else:
    grade = "All grades"

subject_values = sorted(records["course_display"].dropna().unique()) if "course_display" in records.columns else sorted(records["course_id"].unique())
subject = st.sidebar.selectbox("Subject", ["All subjects"] + subject_values, key="subject")
st.sidebar.caption("Filters apply to every tab. The flag and risk score are per student, across all of their courses.")
st.sidebar.divider()
st.sidebar.caption("Data: 500 students, 2,044 course records, 15 Bengaluru schools.")

selected_grade = "All grades" if grade == "Not available in data" else grade
rec = filter_records(school, subject, selected_grade)

st.title("EduTrack Academic Performance Dashboard")

if rec.empty:                                       # empty state
    st.warning("No data for this School + Subject combination. Choose another subject or school.")
    st.stop()

stu = students[students["student_id"].isin(rec["student_id"])]
n_students = len(stu)
too_few = n_students < MIN_N

# ---------------------------------------------------------------
# 4. KPI cards
# ---------------------------------------------------------------
k = kpis(rec, stu)
net_rec = filter_records("All schools", subject, selected_grade)       # compare with the SAME subject across the whole network
net = kpis(net_rec, students[students["student_id"].isin(net_rec["student_id"])])
compare = school != "All schools"


def delta(key, unit=""):
    return f"{k[key] - net[key]:+.1f}{unit} vs network" if (compare and not too_few) else None


with st.container(key="kpis"):
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1.container(border=True):
        st.metric("Students", f"{k['students']:,}", help="Students with at least one course record in the current filter.")
    with c2.container(border=True):
        st.metric("Average quiz score", "n < 10" if too_few else f"{k['quiz']:.1f}", delta=delta("quiz"))
    with c3.container(border=True):
        st.metric("Completion rate", "n < 10" if too_few else f"{k['completion']:.1f}%", delta=delta("completion", " pts"),
                  help="Share of course records that were completed (used as the pass-rate stand-in). "
                       "Differences compare with the whole network for the same subject.")
    with c4.container(border=True):
        st.metric("Avg hours / student", "n < 10" if too_few else f"{k['hours']:.1f}", delta=delta("hours", " h"),
                  help=f"Average platform hours per student. Courses per student: {k['courses']:.2f}.")
    with c5.container(border=True):
        st.metric("At-risk students", "n < 10" if too_few else f"{k['risk']:.1f}%", delta=delta("risk", " pts"), delta_color="inverse",
                  help="Share of students flagged by the risk model (risk probability of 0.40 or more).")

if too_few:
    st.warning(f"Only {n_students} students match this filter, which is too few to show reliable averages. "
               "The watchlist and PDF report still work.")
elif n_students < LOW_CONF_N:
    st.info(f"Only {n_students} students match this filter. Treat the averages as indicative.")

tab1, tab2, tab3, tab4 = st.tabs(["Overview", "School comparison", "At-risk watchlist", "Term-end report"])

# ---------------------------------------------------------------
# TAB 1: Overview
# ---------------------------------------------------------------
with tab1:
    if too_few:
        st.info("Charts are hidden because fewer than 10 students match. Pick a larger group, or open the watchlist tab.")
    else:
        left, right = st.columns(2)
        with left:
            st.subheader("Performance by subject")
            metric_name = st.radio("Measure", ["Completion rate (%)", "Average quiz score", "Average hours per course"],
                                   horizontal=True, key="subject_metric")
            col = {"Completion rate (%)": "completion", "Average quiz score": "quiz", "Average hours per course": "hours"}[metric_name]
            rec_school = filter_records(school, "All subjects", selected_grade)
            by_course = course_summary(rec_school).dropna(subset=[col])
            by_course["highlight"] = (by_course["course_display"] == subject) | (by_course["course_id"] == subject) | (subject == "All subjects")
            chart = alt.Chart(by_course).mark_bar().encode(
                y=alt.Y("course_display:N", sort="-x", title=None),
                x=alt.X(f"{col}:Q", title=metric_name),
                color=alt.Color("highlight:N", scale=alt.Scale(domain=[True, False], range=[DARK, LIGHT]), legend=None),
                tooltip=[alt.Tooltip("course_display", title="Subject"), alt.Tooltip("records", title="Records"),
                         alt.Tooltip("completion", title="Completion %"), alt.Tooltip("quiz", title="Avg quiz"),
                         alt.Tooltip("hours", title="Avg hours")],
            ).properties(height=380)
            st.altair_chart(chart, width="stretch")
            st.caption("Subjects are shown for the selected school. The selected subject is highlighted.")

        with right:
            st.subheader("Risk tiers")
            tier_counts = stu["risk_tier"].value_counts().reindex(["High", "Medium", "Low"]).fillna(0).reset_index()
            tier_counts.columns = ["tier", "students"]
            chart = alt.Chart(tier_counts).mark_bar().encode(
                x=alt.X("tier:N", sort=["High", "Medium", "Low"], title=None, axis=alt.Axis(labelAngle=0)),
                y=alt.Y("students:Q", title="Students"),
                color=alt.Color("tier:N", scale=alt.Scale(domain=list(TIER_COLORS), range=list(TIER_COLORS.values())), legend=None),
                tooltip=["tier", "students"],
            ).properties(height=170)
            st.altair_chart(chart, width="stretch")

            st.subheader("Completion trend by enrollment month")
            monthly = rec.assign(month=rec["enrollment_date"].dt.to_period("M").dt.to_timestamp()).groupby("month").agg(
                records=("student_id", "count"), completion=("completed", lambda s: s.mean() * 100)).reset_index()
            monthly = monthly[monthly["records"] >= 15]       # hide months with too few records
            if len(monthly) < 3:
                st.info("Too few records per month to draw a trend for this filter.")
            else:
                line = alt.Chart(monthly).mark_line(point=True, color=DARK).encode(
                    x=alt.X("month:T", title=None, axis=alt.Axis(format="%b %y", labelAngle=-45)),
                    y=alt.Y("completion:Q", title="Completion rate (%)", scale=alt.Scale(zero=False)),
                    tooltip=[alt.Tooltip("month:T", format="%b %Y"), "records", alt.Tooltip("completion", format=".1f")],
                ).properties(height=200)
                st.altair_chart(line, width="stretch")
                st.caption("Months with fewer than 15 course records are hidden.")

# ---------------------------------------------------------------
# TAB 2: School comparison
# ---------------------------------------------------------------
with tab2:
    st.subheader("School comparison")
    if "school_name" in records.columns:
        st.caption("Comparison across all 15 schools in the EduTrack network in Bengaluru.")
    else:
        st.caption("Cities are used as a stand-in for schools (the data has 10 cities, not 15 schools). "
                   "Statistical tests found no reliable differences between cities, so treat the ranking as descriptive.")
    school_stats = school_summary(filter_records("All schools", subject, selected_grade))
    shown = school_stats.dropna(subset=["quiz"])
    if len(shown) < len(school_stats):
        st.info(f"{len(school_stats) - len(shown)} school(s) have fewer than {MIN_N} students for this subject and are hidden.")

    if len(shown) < 2:
        st.info("Not enough schools with enough students to compare for this subject.")
    else:
        measure = st.radio("Compare schools on", ["Average quiz score", "Completion rate (%)", "Engagement (hours / student)", "At-risk students (%)"],
                           horizontal=True, key="school_metric")
        mcol = {"Average quiz score": "quiz", "Completion rate (%)": "completion",
                "Engagement (hours / student)": "hours", "At-risk students (%)": "risk"}[measure]
        plot = shown.copy()
        plot["highlight"] = (plot["school"] == school) | (school == "All schools")
        bars = alt.Chart(plot).mark_bar().encode(
            y=alt.Y("school:N", sort="-x", title=None),
            x=alt.X(f"{mcol}:Q", title=measure),
            color=alt.Color("highlight:N", scale=alt.Scale(domain=[True, False], range=[DARK, LIGHT]), legend=None),
            tooltip=[alt.Tooltip("school", title="School"), alt.Tooltip("students", title="Students"),
                     alt.Tooltip("quiz", title="Avg quiz"), alt.Tooltip("completion", title="Completion %"),
                     alt.Tooltip("hours", title="Hours / student"), alt.Tooltip("risk", title="At-risk %"),
                     alt.Tooltip("reliability", title="Sample size")],
        )
        avg_line = alt.Chart(pd.DataFrame({"v": [plot[mcol].mean()]})).mark_rule(color="#C0392B", strokeDash=[5, 4]).encode(x="v:Q")
        st.altair_chart((bars + avg_line).properties(height=340), width="stretch")
        st.caption("Dashed line = average across the schools shown. The selected school is highlighted.")

        st.markdown("**Scorecard**")
        card = shown.sort_values(mcol, ascending=(mcol == "risk")).reset_index(drop=True)
        card.insert(0, "Rank", card.index + 1)
        st.dataframe(card, hide_index=True, width="stretch", column_config={
            "school": "School", "students": "Students",
            "quiz": st.column_config.ProgressColumn("Avg quiz", min_value=0, max_value=100, format="%.1f"),
            "completion": st.column_config.ProgressColumn("Completion %", min_value=0, max_value=100, format="%.1f"),
            "hours": st.column_config.NumberColumn("Hours / student", format="%.1f"),
            "risk": st.column_config.ProgressColumn("At-risk %", min_value=0, max_value=100, format="%.1f"),
            "reliability": "Sample size",
        })
        st.caption("Rank follows the measure chosen above (for at-risk %, rank 1 = lowest share). "
                   "Sample size: OK = 30+ students, Low = 10 to 29 (indicative only).")

# ---------------------------------------------------------------
# TAB 3: At-risk watchlist
# ---------------------------------------------------------------
with tab3:
    st.subheader("At-risk student watchlist")

    # accuracy panel, computed live from the stored scores
    tp = int(((students["flagged"] == 1) & (students["at_risk_label"] == 1)).sum())
    fp = int(((students["flagged"] == 1) & (students["at_risk_label"] == 0)).sum())
    fn = int(((students["flagged"] == 0) & (students["at_risk_label"] == 1)).sum())
    tn = int(((students["flagged"] == 0) & (students["at_risk_label"] == 0)).sum())
    with st.expander("How accurate is the at-risk flag?"):
        a1, a2, a3 = st.columns(3)
        a1.metric("Accuracy", f"{(tp + tn) / len(students) * 100:.1f}%")
        a2.metric("Precision", f"{tp / (tp + fp) * 100:.1f}%", help="Of the students flagged, how many really were at risk.")
        a3.metric("Recall", f"{tp / (tp + fn) * 100:.1f}%", help="Of the students at risk, how many were flagged.")
        st.caption("A student is flagged when the model's risk probability is 0.40 or more (out-of-fold scoring). "
                   "Against course completion proxy, cross-validated accuracy is 81.8% (66.9% precision, 70.2% recall). "
                   "Against independent manual teacher evaluations across all 500 students, accuracy is 90.4% "
                   "(85.8% precision, 82.5% recall, 0.901 ROC AUC).")

    f1, f2 = st.columns([2, 1])
    tiers = f1.multiselect("Risk tier", ["High", "Medium"], default=["High", "Medium"], key="tiers")
    search = f2.text_input("Search student ID", placeholder="e.g. STU-0003", key="search")

    watch = stu[(stu["flagged"] == 1) & (stu["risk_tier"].isin(tiers))]
    if search:
        watch = watch[watch["student_id"].str.contains(search.strip(), case=False)]
    watch = watch.sort_values("risk_probability", ascending=False)

    if watch.empty:
        st.info("No flagged students match these settings.")
    else:
        st.caption(f"Showing {len(watch)} flagged students of {int(stu['flagged'].sum())} flagged in the current filter. "
                   "Sorted by risk, highest first. Student IDs only; no names are shown.")
        school_col_name = "School" if "school_name" in watch.columns else "School (city)"
        school_vals = watch["school_name"] if "school_name" in watch.columns else watch["city"]
        table_dict = {
            "Student": watch["student_id"],
            school_col_name: school_vals,
        }
        if "grade" in watch.columns:
            table_dict["Grade"] = watch["grade"]
        table_dict.update({
            "Risk": (watch["risk_probability"] * 100).round(0),
            "Tier": watch["risk_tier"].map(TIER_BADGE),
            "Review by": watch["review_by"],
            "Why flagged (top drivers)": watch["top_risk_drivers"],
            "Recommended intervention": watch["recommended_intervention"],
            "Hours / course": watch["avg_hours_per_course"].round(1),
            "Avg quiz": watch["avg_quiz_score"].round(1),
            "Courses done": watch["courses_completed"].astype(int).astype(str) + " / " + watch["n_interactions"].astype(int).astype(str),
        })
        table = pd.DataFrame(table_dict)
        config = {
            "Risk": st.column_config.ProgressColumn("Risk %", min_value=0, max_value=100, format="%d%%", width=120),
            "Student": st.column_config.TextColumn(width=80),
            school_col_name: st.column_config.TextColumn(width=160),
            "Tier": st.column_config.TextColumn(width=90),
            "Review by": st.column_config.TextColumn(width=110),
            "Why flagged (top drivers)": st.column_config.TextColumn(width=270),
            "Recommended intervention": st.column_config.TextColumn(width=330),
            "Hours / course": st.column_config.NumberColumn(width=105),
            "Avg quiz": st.column_config.NumberColumn(width=80),
            "Courses done": st.column_config.TextColumn(width=105),
        }
        if "grade" in watch.columns:
            config["Grade"] = st.column_config.TextColumn(width=85)
        if school != "All schools":                  # one school selected: the school column adds nothing
            table = table.drop(columns=[school_col_name])
            del config[school_col_name]
        st.dataframe(table, hide_index=True, width="stretch", height=440, column_config=config)
        med_h = students["avg_hours_per_course"].median()
        med_q = students["avg_quiz_score"].median()
        st.caption(f"For comparison, the network median is {med_h:.1f} hours per course and an average quiz score of {med_q:.1f}.")
        st.download_button("Download watchlist (CSV)", table.to_csv(index=False).encode("utf-8"),
                           file_name="edutrack_watchlist.csv", mime="text/csv", on_click="ignore")
    st.caption("Drivers show which behaviours push a student's risk up. Interventions are suggestions for staff to review, "
               "not decisions.")

# ---------------------------------------------------------------
# TAB 4: Term-end PDF report
# ---------------------------------------------------------------
with tab4:
    st.subheader("Term-end report")
    st.write(f"The report covers the current selection: **{school}**, **{grade}**, **{subject}**. "
             "It includes key indicators, subject performance and the top 15 at-risk students"
             + (", plus a comparison of all schools." if school == "All schools" else "."))
    file_label = school.replace(" ", "_").lower()
    st.download_button("Download term-end PDF report", build_report(school, subject, selected_grade),
                       file_name=f"edutrack_term_report_{file_label}.pdf", mime="application/pdf",
                       type="primary", on_click="ignore")
