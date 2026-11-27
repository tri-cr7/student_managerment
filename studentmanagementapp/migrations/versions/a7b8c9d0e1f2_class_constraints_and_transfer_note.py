from alembic import op
import sqlalchemy as sa

revision = "a7b8c9d0e1f2"
down_revision = "f6a7b8c9d0e1"
branch_labels = None
depends_on = None

def _has_index(conn, table, index_name):

    inspector = sa.inspect(conn)
    if table not in inspector.get_table_names():
        return False
    return any(i["name"] == index_name for i in inspector.get_indexes(table))

def _has_constraint(conn, table, constraint_name):

    inspector = sa.inspect(conn)
    if table not in inspector.get_table_names():
        return False
    names = [u["name"] for u in inspector.get_unique_constraints(table)]
    try:
        names += [c["name"] for c in inspector.get_check_constraints(table)]
    except (NotImplementedError, AttributeError):
        pass
    return constraint_name in names

def upgrade():

    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if "classes" in inspector.get_table_names():

        if not _has_constraint(conn, "classes", "uq_class_name_year"):
            op.create_unique_constraint(
                "uq_class_name_year", "classes", ["class_name", "academic_year_id"]
            )

        if not _has_index(conn, "classes", "idx_classes_grade_year"):
            op.create_index(
                "idx_classes_grade_year", "classes", ["grade_id", "academic_year_id"]
            )

    if "class_enrollments" in inspector.get_table_names():

        columns = {c["name"] for c in inspector.get_columns("class_enrollments")}
        if "transfer_note" not in columns:
            op.add_column(
                "class_enrollments",
                sa.Column("transfer_note", sa.String(length=255), nullable=True),
            )

        if not _has_index(conn, "class_enrollments", "idx_student_year_status"):
            op.create_index(
                "idx_student_year_status",
                "class_enrollments",
                ["student_id", "academic_year_id", "status"],
            )

        if not _has_index(conn, "class_enrollments", "idx_enrollment_class"):
            op.create_index(
                "idx_enrollment_class", "class_enrollments", ["class_id", "status"]
            )

    if "grades" in inspector.get_table_names():

        if not _has_constraint(conn, "grades", "ck_grades_grade_level"):
            op.create_check_constraint(
                "ck_grades_grade_level", "grades", "grade_level IN (10, 11, 12)"
            )

def downgrade():

    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if "grades" in inspector.get_table_names():
        if _has_constraint(conn, "grades", "ck_grades_grade_level"):
            op.drop_constraint("ck_grades_grade_level", "grades", type_="check")

    if "class_enrollments" in inspector.get_table_names():
        if _has_index(conn, "class_enrollments", "idx_enrollment_class"):
            op.drop_index("idx_enrollment_class", table_name="class_enrollments")
        if _has_index(conn, "class_enrollments", "idx_student_year_status"):
            op.drop_index("idx_student_year_status", table_name="class_enrollments")

        columns = {c["name"] for c in inspector.get_columns("class_enrollments")}
        if "transfer_note" in columns:
            op.drop_column("class_enrollments", "transfer_note")

    if "classes" in inspector.get_table_names():
        if _has_index(conn, "classes", "idx_classes_grade_year"):
            op.drop_index("idx_classes_grade_year", table_name="classes")
        if _has_constraint(conn, "classes", "uq_class_name_year"):
            op.drop_constraint("uq_class_name_year", "classes", type_="unique")
