def test_models_create_tables(app):
    from studentapp.extensions import db
    from sqlalchemy import inspect
    tables = set(inspect(db.engine).get_table_names())
    expected = {
        "academic_years", "semesters", "grades", "students", "classes",
        "subjects", "class_enrollments", "teaching_assignments", "scores",
        "score_submissions", "score_change_requests", "score_change_details",
        "email_outbox",
    }
    missing = expected - tables
    assert not missing, f"Thiếu bảng: {missing}"
