from alembic import op
import sqlalchemy as sa

revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None

_SEMESTERS = "semesters"
_ACADEMIC_YEARS = "academic_years"
_ASSIGNMENTS = "teaching_assignments"

_NAME_MAP = {
    "hoc ky 1": "HK1",
    "hoc ky 2": "HK2",
    "hk1": "HK1",
    "hk2": "HK2",
    "học kỳ 1": "HK1",
    "học kỳ 2": "HK2",
    "học kỳ 3": "HK2",
    "hk 1": "HK1",
    "hk 2": "HK2",
    "1": "HK1",
    "2": "HK2",
}

_FACTOR = {"HK1": 1, "HK2": 2}

def _normalize_names(conn):

    rows = conn.execute(sa.text(
        f"SELECT id, semester_name FROM {_SEMESTERS}")).fetchall()
    for sid, raw in rows:
        key = (raw or "").strip().lower()
        canonical = _NAME_MAP.get(key)
        if canonical is None:

            canonical = "HK2" if key.startswith("hk2") or key.startswith("2") else "HK1"
        conn.execute(sa.text(
            f"UPDATE {_SEMESTERS} SET semester_name = :name, factor = :factor "
            f"WHERE id = :id"),
            {"name": canonical, "factor": _FACTOR[canonical], "id": sid})

def _dedupe_semesters(conn):

    conn.execute(sa.text(
        f"DELETE s1 FROM {_SEMESTERS} s1 "
        f"INNER JOIN {_SEMESTERS} s2 "
        f"  ON s1.academic_year_id = s2.academic_year_id "
        f" AND s1.semester_name = s2.semester_name "
        f" AND s1.id > s2.id"))

def _dedupe_assignments(conn):

    conn.execute(sa.text(
        f"DELETE a1 FROM {_ASSIGNMENTS} a1 "
        f"INNER JOIN {_ASSIGNMENTS} a2 "
        f"  ON a1.class_id = a2.class_id "
        f" AND a1.subject_id = a2.subject_id "
        f" AND a1.semester_id = a2.semester_id "
        f" AND a1.id > a2.id"))

def upgrade():

    conn = op.get_bind()
    inspector = sa.inspect(conn)

    _normalize_names(conn)

    year_cols = {c["name"] for c in inspector.get_columns(_ACADEMIC_YEARS)}
    for col in ("start_date", "end_date"):
        if col not in year_cols:
            op.add_column(_ACADEMIC_YEARS, sa.Column(col, sa.Date(), nullable=True))

    _dedupe_semesters(conn)
    _dedupe_assignments(conn)

    existing = {i["name"] for i in inspector.get_indexes(_SEMESTERS)}
    if "uq_semester_year" not in existing:
        op.create_index(
            "uq_semester_year", _SEMESTERS,
            ["academic_year_id", "semester_name"], unique=True,
        )

    existing = {i["name"] for i in inspector.get_indexes(_ASSIGNMENTS)}
    if "uq_teacher_class_subject_sem" not in existing:
        op.create_index(
            "uq_teacher_class_subject_sem", _ASSIGNMENTS,
            ["class_id", "subject_id", "semester_id"], unique=True,
        )

def downgrade():

    conn = op.get_bind()
    inspector = sa.inspect(conn)

    existing = {i["name"] for i in inspector.get_indexes(_SEMESTERS)}
    if "uq_semester_year" in existing:
        op.drop_index("uq_semester_year", table_name=_SEMESTERS)

    existing = {i["name"] for i in inspector.get_indexes(_ASSIGNMENTS)}
    if "uq_teacher_class_subject_sem" in existing:
        op.drop_index("uq_teacher_class_subject_sem", table_name=_ASSIGNMENTS)

    year_cols = {c["name"] for c in inspector.get_columns(_ACADEMIC_YEARS)}
    for col in ("end_date", "start_date"):
        if col in year_cols:
            op.drop_column(_ACADEMIC_YEARS, col)
