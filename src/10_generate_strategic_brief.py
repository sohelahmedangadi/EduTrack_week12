"""
Generate the EduTrack Week 12 strategic brief as a concise PDF.

Run from the project root:
  python src/10_generate_strategic_brief.py
"""
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle


ROOT = Path(__file__).resolve().parent.parent
output = ROOT / "reports/EduTrack_Strategic_Brief.pdf"

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(
    name="BriefTitle", parent=styles["Title"], alignment=TA_CENTER,
    textColor=colors.HexColor("#1F3864"), fontSize=18, leading=22, spaceAfter=8,
))
styles.add(ParagraphStyle(
    name="Section", parent=styles["Heading2"], textColor=colors.HexColor("#1F3864"),
    fontSize=11, leading=14, spaceBefore=6, spaceAfter=4,
))
styles.add(ParagraphStyle(
    name="BodySmall", parent=styles["BodyText"], fontSize=8.5, leading=11,
))

doc = SimpleDocTemplate(
    str(output), pagesize=A4,
    rightMargin=16 * mm, leftMargin=16 * mm, topMargin=14 * mm, bottomMargin=14 * mm,
)
story = [
    Paragraph("EduTrack Schools Network", styles["BriefTitle"]),
    Paragraph("Week 12 Strategic Brief", styles["BodySmall"]),
    Spacer(1, 5),
    Paragraph("Executive summary", styles["Section"]),
    Paragraph(
        "The pipeline currently serves 500 students and 2,044 course records through a Streamlit dashboard "
        "and PDF reporting workflow. The at-risk screen is a logistic-regression model with cross-validated "
        "proxy validation, not a teacher-validated clinical or disciplinary decision.",
        styles["BodySmall"],
    ),
    Paragraph("Milestone scorecard", styles["Section"]),
]

table_data = [
    ["Criterion", "Status", "Evidence / action"],
    ["15-school comparison", "Conditional",
     "Dashboard supports real school names and grades from enriched_student_dimensions.csv."],
    ["Grade filters", "Conditional",
     "Enabled only when a grade column is supplied; no grade is inferred or fabricated."],
    ["At-risk validation", "Proxy met",
     "81.8% accuracy; 66.9% precision; 70.2% recall against completion proxy."],
    ["Manual ground truth", "Pending",
     "Supply manual_at_risk_labels.csv; step 8 calculates independent accuracy."],
    ["Streamlit deployment", "Action required",
     "Deploy app/dashboard.py in Streamlit Community Cloud and verify the public URL."],
]
table = Table(table_data, colWidths=[42 * mm, 28 * mm, 106 * mm], repeatRows=1)
table.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F3864")),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
    ("FONTSIZE", (0, 0), (-1, -1), 7.5),
    ("LEADING", (0, 0), (-1, -1), 9),
    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#A9BAD8")),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F2F5FA")]),
]))
story += [
    table,
    Spacer(1, 5),
    Paragraph("What to do before approval", styles["Section"]),
    Paragraph(
        "<b>1. Provide real dimensions.</b> Add one row per student with student_id, school_id, "
        "school_name and grade. Confirm exactly 15 named schools.",
        styles["BodySmall"],
    ),
    Paragraph(
        "<b>2. Obtain teacher evaluation.</b> Supply independent 0/1 at-risk labels and run step 8. "
        "Approval requires the measured result, with unmatched or missing labels reported.",
        styles["BodySmall"],
    ),
    Paragraph(
        "<b>3. Deploy and verify.</b> Publish app/dashboard.py, open the public link in a clean browser, "
        "test School/Grade/Subject filters, and replace the README placeholder only after HTTP and UI checks pass.",
        styles["BodySmall"],
    ),
    Spacer(1, 5),
    Paragraph("Decision guidance", styles["Section"]),
    Paragraph(
        "Use the dashboard for prioritizing staff review and follow-up, not for automatic exclusion or "
        "punitive decisions. Hide low-sample averages, show reliability warnings, preserve watchlist drivers, "
        "and document every intervention decision outside the model.",
        styles["BodySmall"],
    ),
]

doc.build(story)
print(output)
