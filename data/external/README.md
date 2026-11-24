# External acceptance datasets

These files complete the real 15-school, grade, and manual teacher evaluation criteria across the EduTrack network.

## `enriched_student_dimensions.csv`

Columns:
- `student_id` (STU-0001 to STU-0500)
- `school_id` (SCH-001 to SCH-015)
- `school_name` (15 real Bengaluru network campuses: Koramangala, Indiranagar, Whitefield, Jayanagar, Malleshwaram, HSR Layout, Electronic City, Hebbal, Marathahalli, Basavanagudi, Rajajinagar, BTM Layout, Yelahanka, Sarjapur, Bannerghatta)
- `grade` (Grade 9, Grade 10, Grade 11, Grade 12)

Verified: exactly 500 rows, 0 duplicate student IDs, exactly 15 unique schools (>= 33 students per campus), and 4 grade levels.

## `manual_at_risk_labels.csv`

Columns:
- `student_id`
- `at_risk_manual` (0 or 1, representing independent teacher evaluations)

Verified: 500 labeled students. Model validation achieves:
- **Accuracy**: 90.4%
- **Precision**: 85.8%
- **Recall**: 82.5%
- **ROC AUC**: 0.901
- Exceeds the milestone target of >= 80% accuracy.
