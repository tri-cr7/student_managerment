import pytest

from studentapp.exceptions import BusinessRuleError, DuplicateError, ValidationError
from studentapp.services import catalog_service

class TestAcademicYear:
    def test_create_year_auto_creates_two_semesters(self, app, seed_data):

        from studentapp.models.semester import Semester

        out = catalog_service.create_academic_year(
            {"year_name": "2027-2028", "start_year": 2027, "end_year": 2028},
            actor_id=seed_data["academic"].id,
        )
        rows = Semester.query.filter_by(academic_year_id=out["id"]).all()
        assert {s.semester_name for s in rows} == {"HK1", "HK2"}
        assert {int(s.factor) for s in rows} == {1, 2}

    def test_create_year_with_dates(self, app, seed_data):

        out = catalog_service.create_academic_year(
            {"year_name": "2028-2029", "start_year": 2028, "end_year": 2029,
             "start_date": "2028-09-05", "end_date": "2029-05-31"},
            actor_id=seed_data["academic"].id,
        )
        assert out["start_date"] == "2028-09-05"
        assert out["end_date"] == "2029-05-31"

    def test_create_year_rejects_bad_date_range(self, app, seed_data):
        with pytest.raises(ValidationError):
            catalog_service.create_academic_year(
                {"year_name": "2029-2030", "start_year": 2029, "end_year": 2030,
                 "start_date": "2029-09-05", "end_date": "2029-01-01"},
                actor_id=seed_data["academic"].id,
            )

    def test_duplicate_year_rejected(self, app, seed_data):
        with pytest.raises(DuplicateError):
            catalog_service.create_academic_year(
                {"year_name": "2026-2027", "start_year": 2026, "end_year": 2027},
                actor_id=seed_data["academic"].id,
            )

class TestSemester:
    def test_only_hk1_hk2_allowed(self, app, seed_data):

        with pytest.raises(ValidationError) as exc:
            catalog_service.create_semester(
                {"semester_name": "HK3", "academic_year_id":
                 seed_data["academic_year"].id},
                actor_id=seed_data["academic"].id,
            )
        assert exc.value.error == "INVALID_SEMESTER_NAME"

    def test_factor_is_derived_not_client_supplied(self, app, seed_data):

        from studentapp.models.academic_year import AcademicYear
        from studentapp.extensions import db

        year = AcademicYear(
            year_name="2025-2026", start_year=2025, end_year=2026,
            is_current=False,
        )
        db.session.add(year)
        db.session.commit()

        out = catalog_service.create_semester(
            {"semester_name": "HK2", "academic_year_id": year.id, "factor": 99},
            actor_id=seed_data["academic"].id,
        )
        assert out["factor"] == 2

    def test_duplicate_semester_in_year_rejected(self, app, seed_data):
        with pytest.raises(DuplicateError):
            catalog_service.create_semester(
                {"semester_name": "HK1", "academic_year_id":
                 seed_data["academic_year"].id},
                actor_id=seed_data["academic"].id,
            )

    def test_semester_names_are_normalized(self, app, seed_data):

        from studentapp.models.academic_year import AcademicYear
        from studentapp.extensions import db

        year = AcademicYear(
            year_name="2025-2026", start_year=2025, end_year=2026,
            is_current=False,
        )
        db.session.add(year)
        db.session.commit()

        out = catalog_service.create_semester(
            {"semester_name": "hk1", "academic_year_id": year.id},
            actor_id=seed_data["academic"].id,
        )
        assert out["semester_name"] == "HK1"
        assert out["semester_display"] == "Học kỳ 1"

class TestCurrentSemester:
    def test_current_semester_scoped_to_current_year(self, app, seed_data):

        from studentapp.models.semester import Semester

        cur = catalog_service.get_current_semester()
        assert cur["academic_year_id"] == seed_data["academic_year"].id
        assert cur["semester_name"] == "HK1"

        y2 = catalog_service.create_academic_year(
            {"year_name": "2027-2028", "start_year": 2027, "end_year": 2028},
            actor_id=seed_data["academic"].id,
        )
        catalog_service.set_current_year(
            y2["id"], actor_id=seed_data["academic"].id)

        cur = catalog_service.get_current_semester()
        assert cur["academic_year_id"] == y2["id"]
        assert cur["semester_name"] == "HK1"

        assert Semester.query.filter_by(is_current=True).count() == 1

    def test_set_current_semester_does_not_touch_other_years(self, app, seed_data):

        from studentapp.models.semester import Semester

        y2 = catalog_service.create_academic_year(
            {"year_name": "2027-2028", "start_year": 2027, "end_year": 2028},
            actor_id=seed_data["academic"].id,
        )
        hk2_old = seed_data["semester_hk2"]
        hk2_new = Semester.query.filter_by(
            academic_year_id=y2["id"], semester_name="HK2").first()

        catalog_service.set_current_semester(
            hk2_new.id, actor_id=seed_data["academic"].id)

        assert hk2_new.is_current is True

        assert hk2_old.is_current is False
        assert seed_data["semester_hk1"].is_current is True

    def test_current_semester_with_academic_year_filter(self, app, seed_data):

        cur = catalog_service.get_current_semester(
            academic_year_id=seed_data["academic_year"].id)
        assert cur["semester_name"] == "HK1"

    def test_current_semester_unknown_year_404(self, app, seed_data):
        from studentapp.exceptions import NotFoundError

        with pytest.raises(NotFoundError):
            catalog_service.get_current_semester(academic_year_id=9999)

class TestAssignmentAcademicYearGuard:
    def test_reject_assignment_across_academic_years(self, app, seed_data):

        from studentapp.extensions import db
        from studentapp.models.academic_year import AcademicYear
        from studentapp.models.class_room import Class
        from studentapp.models.semester import Semester
        from studentapp.services import assignment_service

        old_year = AcademicYear(
            year_name="2025-2026", start_year=2025, end_year=2026,
            is_current=False,
        )
        db.session.add(old_year)
        db.session.flush()
        old_hk1 = Semester(
            semester_name="HK1", academic_year_id=old_year.id, factor=1,
        )
        db.session.add(old_hk1)
        db.session.flush()
        old_class = Class(
            class_name="11B1", grade_id=seed_data["grade"].id,
            academic_year_id=old_year.id,
        )
        db.session.add(old_class)
        db.session.commit()

        with pytest.raises(BusinessRuleError) as exc:
            assignment_service.create_assignment(
                {"teacher_id": seed_data["teacher"].id,
                 "class_id": old_class.id,
                 "subject_id": seed_data["subject"].id,
                 "semester_id": seed_data["semester_hk1"].id},
                actor_id=seed_data["academic"].id,
            )
        assert exc.value.error == "ACADEMIC_YEAR_MISMATCH"

    def test_update_assignment_rejects_cross_year(self, app, seed_data):

        from studentapp.extensions import db
        from studentapp.models.academic_year import AcademicYear
        from studentapp.models.semester import Semester
        from studentapp.services import assignment_service

        old_year = AcademicYear(
            year_name="2025-2026", start_year=2025, end_year=2026,
            is_current=False,
        )
        db.session.add(old_year)
        db.session.flush()
        old_hk1 = Semester(
            semester_name="HK1", academic_year_id=old_year.id, factor=1,
        )
        db.session.add(old_hk1)
        db.session.commit()

        with pytest.raises(BusinessRuleError):
            assignment_service.update_assignment(
                seed_data["assignment"].id,
                {"semester_id": old_hk1.id},
                actor_id=seed_data["academic"].id,
            )

    def test_same_year_assignment_allowed(self, app, seed_data):

        from studentapp.services import assignment_service

        out = assignment_service.create_assignment(
            {"teacher_id": seed_data["other_teacher"].id,
             "class_id": seed_data["class"].id,
             "subject_id": seed_data["subject"].id,
             "semester_id": seed_data["semester_hk2"].id},
            actor_id=seed_data["academic"].id,
        )
        assert out["semester_name"] == "HK2"
        assert out["academic_year_name"] == "2026-2027"
