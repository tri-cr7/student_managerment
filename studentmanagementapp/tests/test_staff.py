import io
from datetime import date

import pytest

from studentapp.extensions import db
from studentapp.models.academic_year import AcademicYear
from studentapp.models.class_enrollment import ClassEnrollment, EnrollmentStatusEnum
from studentapp.models.class_room import Class
from studentapp.models.grade import Grade
from studentapp.models.student import Student, StudentStatusEnum
from studentapp.models.user import User, UserRoleEnum

@pytest.fixture
def users(app):

    from flask_jwt_extended import create_access_token

    def _mk(username, role):
        u = User(username=username, email="%s@school.local" % username,
                 full_name=username.upper(), role=role)
        u.set_password("Test@123")
        db.session.add(u)
        return u

    staff = _mk("nv01", UserRoleEnum.STAFF)
    teacher = _mk("gv01", UserRoleEnum.TEACHER)
    academic = _mk("hv01", UserRoleEnum.ACADEMIC)
    db.session.commit()

    def _tok(u):
        with app.app_context():
            return create_access_token(identity=str(u.id),
                                       additional_claims={"role": u.role.value})

    return {
        "staff": staff, "teacher": teacher, "academic": academic,
        "H": {"Authorization": "Bearer %s" % _tok(staff)},
        "H_T": {"Authorization": "Bearer %s" % _tok(teacher)},
        "H_A": {"Authorization": "Bearer %s" % _tok(academic)},
    }

@pytest.fixture
def org(app):

    year = AcademicYear(year_name="2026-2027", start_year=2026, end_year=2027, is_current=True)
    grades = [Grade(grade_level=g, grade_name="Khối %d" % g) for g in (10, 11, 12)]
    db.session.add_all([year] + grades)
    db.session.commit()
    return {"year": year, "grades": grades}

@pytest.fixture
def klass(app, org):

    cls = Class(class_name="10A1", grade_id=org["grades"][0].id,
                academic_year_id=org["year"].id, current_size=0)
    db.session.add(cls)
    db.session.commit()
    return cls

@pytest.fixture
def admit(client, users):

    def _do(code="HS001", name="Nguyen Van A", dob="2010-05-10", **extra):
        payload = {"student_code": code, "full_name": name, "date_of_birth": dob}
        payload.update(extra)
        r = client.post("/api/v1/students/admit", headers=users["H"], json=payload)
        return r, (r.get_json().get("data") or {}).get("id") if r.status_code == 201 else None

    return _do

class TestSD03Admit:
    def test_admit_valid_returns_201(self, client, users):
        r = client.post("/api/v1/students/admit", headers=users["H"], json={
            "student_code": "HS001", "full_name": "Le Hoang Yen",
            "date_of_birth": "2010-09-20", "gender": "NU",
            "address": "456 Vo Van Tan", "phone": "0988776655", "email": "yen.le@gmail.com"})
        assert r.status_code == 201
        d = r.get_json()["data"]
        assert d["student_code"] == "HS001"
        assert d["full_name"] == "Le Hoang Yen"
        assert d["status"] == "DANG_HOC"

    def test_response_contains_calculated_age_and_created_at(self, client, users):

        r = client.post("/api/v1/students/admit", headers=users["H"], json={
            "student_code": "HS001", "full_name": "A", "date_of_birth": "2010-09-20"})
        assert r.status_code == 201
        d = r.get_json()["data"]
        assert "calculated_age" in d
        assert "created_at" in d
        assert d["calculated_age"] == 16

    def test_accepts_dob_alias_from_api_md(self, client, users):

        r = client.post("/api/v1/students/admit", headers=users["H"], json={
            "student_code": "HS001", "full_name": "A", "dob": "2010-09-20"})
        assert r.status_code == 201, r.get_data(as_text=True)
        assert r.get_json()["data"]["date_of_birth"] == "2010-09-20"

    def test_age_below_min_returns_422_with_current_rules(self, client, users):

        r = client.post("/api/v1/students/admit", headers=users["H"], json={
            "student_code": "HS001", "full_name": "A", "date_of_birth": "2016-01-01"})
        assert r.status_code == 422
        j = r.get_json()
        assert j["error"] == "BUSINESS_RULE_VIOLATION"
        assert j["current_rules"] == {"min_age": 15, "max_age": 20}

    def test_age_above_max_returns_422(self, client, users):
        r = client.post("/api/v1/students/admit", headers=users["H"], json={
            "student_code": "HS001", "full_name": "A", "date_of_birth": "2000-01-01"})
        assert r.status_code == 422
        assert r.get_json()["error"] == "BUSINESS_RULE_VIOLATION"

    def test_age_boundaries_15_and_20_accepted(self, client, users):

        today = date.today()
        dob15 = date(today.year - 15, today.month, today.day)
        dob20 = date(today.year - 20, today.month, today.day)
        for i, dob in enumerate((dob15, dob20)):
            r = client.post("/api/v1/students/admit", headers=users["H"], json={
                "student_code": "HSB%d" % i, "full_name": "B", "date_of_birth": dob.isoformat()})
            assert r.status_code == 201, (dob, r.get_data(as_text=True))

    def test_age_reads_dynamic_rule_from_system_rules(self, client, users, app):

        from studentapp.models.system_rule import SystemRule
        rule = SystemRule.query.filter_by(rule_key="MIN_AGE").first()
        old = rule.rule_value
        rule.rule_value = "18"
        db.session.commit()
        try:
            r = client.post("/api/v1/students/admit", headers=users["H"], json={
                "student_code": "HS001", "full_name": "A", "date_of_birth": "2010-01-01"})
            assert r.status_code == 422
            assert r.get_json()["current_rules"]["min_age"] == 18
        finally:
            rule.rule_value = old
            db.session.commit()

    def test_duplicate_code_rejected(self, client, users, admit):
        admit(code="HS001")
        r, _ = admit(code="HS001")
        assert r.status_code == 400
        assert r.get_json()["error"] == "DUPLICATE_CODE"

    def test_missing_fields_rejected(self, client, users):
        r = client.post("/api/v1/students/admit", headers=users["H"], json={})
        assert r.status_code == 400
        assert r.get_json()["error"] == "MISSING_FIELDS"

    def test_invalid_date_format_rejected(self, client, users):
        r = client.post("/api/v1/students/admit", headers=users["H"], json={
            "student_code": "HS001", "full_name": "A", "date_of_birth": "abc-def"})
        assert r.status_code == 400
        assert r.get_json()["error"] == "INVALID_DATE_FORMAT"

    def test_invalid_email_rejected(self, client, users):
        r = client.post("/api/v1/students/admit", headers=users["H"], json={
            "student_code": "HS001", "full_name": "A",
            "date_of_birth": "2010-01-01", "email": "khong-hop-le"})
        assert r.status_code == 400
        assert r.get_json()["error"] == "INVALID_EMAIL"

    def test_teacher_cannot_admit(self, client, users):
        r = client.post("/api/v1/students/admit", headers=users["H_T"], json={
            "student_code": "HS001", "full_name": "A", "date_of_birth": "2010-01-01"})
        assert r.status_code == 403

    def test_requires_auth(self, client):
        r = client.post("/api/v1/students/admit", json={
            "student_code": "HS001", "full_name": "A", "date_of_birth": "2010-01-01"})
        assert r.status_code == 401

    def test_writes_audit_log(self, client, users, admit):
        from studentapp.models.audit_log import AuditLog
        admit(code="HS001")
        row = AuditLog.query.filter_by(
            user_id=users["staff"].id, action="ADMIT_STUDENT").first()
        assert row is not None
        assert row.details["student_code"] == "HS001"

CSV_HEADER = "student_code,full_name,date_of_birth,gender,email\n"

def _upload(client, headers, content, filename="ds.csv"):
    return client.post("/api/v1/students/import-excel", headers=headers,
                        data={"file": (io.BytesIO(content.encode()), filename)},
                        content_type="multipart/form-data")

class TestSD04Import:
    def test_import_csv_success(self, client, users):

        csv_txt = CSV_HEADER + "HS201,Nam Một,2010-01-01,Nam,a1@s.local\nHS202,Nam Hai,2010-02-02,Nam,a2@s.local\n"
        r = _upload(client, users["H"], csv_txt)
        assert r.status_code == 200
        d = r.get_json()["data"]
        assert d["total_rows"] == 2
        assert d["success_count"] == 2
        assert d["failed_count"] == 0
        assert d["errors"] == []
        assert Student.query.filter_by(student_code="HS201").count() == 1

    def test_response_contract_matches_api_md(self, client, users):

        r = _upload(client, users["H"], CSV_HEADER + "HS201,Nam,2010-01-01,Nam\n")
        assert r.status_code == 200
        d = r.get_json()["data"]
        for k in ("total_rows", "success_count", "failed_count", "errors"):
            assert k in d, "thiếu key %s" % k

    def test_partial_success_invalid_age(self, client, users):

        csv_txt = (CSV_HEADER +
                   "HS201,Nam Một,2010-01-01,Nam\n"
                   "HS202,Nam Hai,2016-01-01,Nam\n")
        r = _upload(client, users["H"], csv_txt)
        assert r.status_code == 200
        d = r.get_json()["data"]
        assert d["total_rows"] == 2
        assert d["success_count"] == 1
        assert d["failed_count"] == 1
        assert len(d["errors"]) == 1
        err = d["errors"][0]
        assert "row" in err and "reason" in err
        assert err["row"] == 3
        assert Student.query.filter_by(student_code="HS201").count() == 1
        assert Student.query.filter_by(student_code="HS202").count() == 0

    def test_partial_success_duplicate_code_in_db(self, client, users, admit):

        admit(code="HS201")
        csv_txt = CSV_HEADER + "HS201,Trung Ma,2010-01-01,Nam\nHS202,OK,2010-01-01,Nam\n"
        r = _upload(client, users["H"], csv_txt)
        d = r.get_json()["data"]
        assert d["success_count"] == 1
        assert d["failed_count"] == 1
        assert "đã tồn tại" in d["errors"][0]["reason"]

    def test_partial_success_duplicate_code_in_file(self, client, users):
        csv_txt = (CSV_HEADER +
                   "HS201,Mot,2010-01-01,Nam\n"
                   "HS201,Hai,2010-01-01,Nam\n")
        r = _upload(client, users["H"], csv_txt)
        d = r.get_json()["data"]
        assert d["success_count"] == 1
        assert d["failed_count"] == 1
        assert "trùng" in d["errors"][0]["reason"].lower()

    def test_missing_required_column_reports_row(self, client, users):
        csv_txt = "student_code,full_name\nHS201,Thieu Ngay Sinh\n"
        r = _upload(client, users["H"], csv_txt)
        d = r.get_json()["data"]
        assert d["success_count"] == 0
        assert d["failed_count"] == 1
        assert "date_of_birth" in d["errors"][0]["reason"]

    def test_import_xlsx_real_file(self, client, users):

        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active
        ws.append(["student_code", "full_name", "date_of_birth", "gender"])
        ws.append(["HS301", "Excel One", "2010-01-01", "Nam"])
        ws.append(["HS302", "Excel Two", "2010-02-02", "Nu"])
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        r = client.post("/api/v1/students/import-excel", headers=users["H"],
                        data={"file": (buf, "ds.xlsx")},
                        content_type="multipart/form-data")
        assert r.status_code == 200
        d = r.get_json()["data"]
        assert d["success_count"] == 2
        assert Student.query.filter_by(student_code="HS301").count() == 1

    def test_import_accepts_vietnamese_headers(self, client, users):

        csv_txt = ("Mã học sinh,Họ tên,Ngày sinh,Giới tính\n"
                   "HS401,Nguyen A,2010-01-01,Nam\n")
        r = _upload(client, users["H"], csv_txt)
        d = r.get_json()["data"]
        assert d["success_count"] == 1, d
        assert Student.query.filter_by(student_code="HS401").count() == 1

    def test_import_semicolon_delimiter(self, client, users):
        csv_txt = "student_code;full_name;date_of_birth;gender\nHS501;Semi;2010-01-01;Nam\n"
        r = _upload(client, users["H"], csv_txt)
        d = r.get_json()["data"]
        assert d["success_count"] == 1, d

    def test_invalid_file_type_rejected(self, client, users):
        r = client.post("/api/v1/students/import-excel", headers=users["H"],
                        data={"file": (io.BytesIO(b"x"), "hs.txt")},
                        content_type="multipart/form-data")
        assert r.status_code == 400
        assert r.get_json()["error"] == "INVALID_FILE_TYPE"

    def test_missing_file_rejected(self, client, users):
        r = client.post("/api/v1/students/import-excel", headers=users["H"],
                        data={}, content_type="multipart/form-data")
        assert r.status_code == 400
        assert r.get_json()["error"] == "MISSING_FILE"

    def test_teacher_cannot_import(self, client, users):
        r = _upload(client, users["H_T"], CSV_HEADER + "HS601,A,2010-01-01,Nam\n")
        assert r.status_code == 403

class TestSD05SD06Classes:
    def test_create_class(self, client, users, org):
        r = client.post("/api/v1/classes", headers=users["H"], json={
            "class_name": "10A2", "grade_id": org["grades"][0].id,
            "academic_year_id": org["year"].id})
        assert r.status_code == 201

    def test_update_class_changes_grade(self, client, users, org, klass):

        new_grade = org["grades"][1]
        r = client.put("/api/v1/classes/%d" % klass.id, headers=users["H"], json={
            "class_name": "10A1", "grade_id": new_grade.id})
        assert r.status_code == 200, r.get_json()
        assert r.get_json()["data"]["grade_id"] == new_grade.id
        db.session.refresh(klass)
        assert klass.grade_id == new_grade.id

    def test_update_class_keeps_academic_year_unchanged(self, client, users, org, klass):

        r = client.put("/api/v1/classes/%d" % klass.id, headers=users["H"], json={
            "class_name": "10A1", "grade_id": org["grades"][1].id,
            "academic_year_id": 99999})
        assert r.status_code == 200, r.get_json()
        db.session.refresh(klass)
        assert klass.academic_year_id == org["year"].id

    def test_update_class_duplicate_name_same_year_returns_409(self, client, users, org, klass):

        cls_b = Class(class_name="10B1", grade_id=org["grades"][0].id,
                      academic_year_id=org["year"].id, current_size=0)
        db.session.add(cls_b)
        db.session.commit()
        r = client.put("/api/v1/classes/%d" % klass.id, headers=users["H"], json={
            "class_name": "10B1", "grade_id": org["grades"][0].id})
        assert r.status_code == 409
        assert r.get_json()["error"] == "DUPLICATE_CLASS_NAME"

        db.session.refresh(klass)
        assert klass.class_name == "10A1"

    def test_update_class_invalid_grade_returns_404(self, client, users, org, klass):

        r = client.put("/api/v1/classes/%d" % klass.id, headers=users["H"], json={
            "class_name": "10A1", "grade_id": 99999})
        assert r.status_code == 404

    def test_update_class_writes_audit_log(self, client, users, org, klass):

        from studentapp.models.audit_log import AuditLog

        r = client.put("/api/v1/classes/%d" % klass.id, headers=users["H"], json={
            "class_name": "10A1", "grade_id": org["grades"][2].id})
        assert r.status_code == 200, r.get_json()
        log = AuditLog.query.filter_by(action="UPDATE_CLASS").order_by(
            AuditLog.id.desc()).first()
        assert log is not None
        assert log.user_id == users["staff"].id
        assert log.details["class_id"] == klass.id
        assert log.details["changes"]["grade_id"]["new"] == org["grades"][2].id

    def test_update_class_rejects_non_teacher_as_homeroom(self, client, users, org, klass):

        r = client.put("/api/v1/classes/%d" % klass.id, headers=users["H"], json={
            "class_name": "10A1", "grade_id": org["grades"][0].id,
            "homeroom_teacher_id": users["academic"].id})
        assert r.status_code == 400
        assert r.get_json()["error"] == "INVALID_HOMEROOM_TEACHER"

    def test_enroll_updates_class_size(self, client, users, org, klass, admit):
        _, sid = admit(code="HS001")
        r = client.post("/api/v1/classes/%d/enroll" % klass.id, headers=users["H"], json={
            "student_id": sid, "academic_year_id": org["year"].id})
        assert r.status_code == 200
        db.session.refresh(klass)
        assert klass.current_size == 1

    def test_class_size_cap_uses_dynamic_rule(self, client, users, org, klass, admit, app):

        from studentapp.models.system_rule import SystemRule
        rule = SystemRule.query.filter_by(rule_key="MAX_CLASS_SIZE").first()
        old = rule.rule_value
        rule.rule_value = "2"
        db.session.commit()
        try:
            ids = []
            for i in range(3):
                _, s = admit(code="HSC%d" % i)
                ids.append(s)
            last = None
            for s in ids:
                last = client.post("/api/v1/classes/%d/enroll" % klass.id, headers=users["H"], json={
                    "student_id": s, "academic_year_id": org["year"].id})
            assert last.status_code == 422
            db.session.refresh(klass)
            assert klass.current_size == 2
        finally:
            rule.rule_value = old
            db.session.commit()

    def test_transfer_student_moves_enrollment(self, client, users, org, klass, admit, app):

        cls_b = Class(class_name="10B1", grade_id=org["grades"][0].id,
                      academic_year_id=org["year"].id, current_size=0)
        db.session.add(cls_b)
        db.session.commit()
        _, sid = admit(code="HS001")
        client.post("/api/v1/classes/%d/enroll" % klass.id, headers=users["H"], json={
            "student_id": sid, "academic_year_id": org["year"].id})
        r = client.post("/api/v1/classes/transfer", headers=users["H"], json={
            "student_id": sid, "to_class_id": cls_b.id,
            "academic_year_id": org["year"].id})
        assert r.status_code == 200
        db.session.refresh(klass)
        db.session.refresh(cls_b)
        assert klass.current_size == 0
        assert cls_b.current_size == 1

    def test_transfer_to_missing_class_returns_404(self, client, users, org, admit):
        _, sid = admit(code="HS001")
        r = client.post("/api/v1/classes/transfer", headers=users["H"], json={
            "student_id": sid, "to_class_id": 99999,
            "academic_year_id": org["year"].id})
        assert r.status_code == 404

    def test_export_class_excel(self, client, users, klass, admit, org):

        _, sid = admit(code="HS001")
        client.post("/api/v1/classes/%d/enroll" % klass.id, headers=users["H"], json={
            "student_id": sid, "academic_year_id": org["year"].id})
        r = client.get("/api/v1/classes/%d/export?format=excel" % klass.id, headers=users["H"])
        assert r.status_code == 200
        assert "spreadsheetml" in (r.headers.get("Content-Type") or "")

    def test_export_class_pdf(self, client, users, klass):
        r = client.get("/api/v1/classes/%d/export?format=pdf" % klass.id, headers=users["H"])
        assert r.status_code == 200
        assert r.headers.get("Content-Type") == "application/pdf"

class TestEnrollTransferContracts:
    def test_enroll_accepts_batch_student_ids(self, client, users, org, klass, admit):

        ids = []
        for i in range(2):
            _, s = admit(code="HSS%d" % i)
            ids.append(s)
        r = client.post("/api/v1/classes/%d/enroll" % klass.id, headers=users["H"], json={
            "student_ids": ids, "academic_year_id": org["year"].id})
        assert r.status_code == 200
        j = r.get_json()
        assert j["enrolled_count"] == 2
        assert j["new_current_size"] == 2
        d = j["data"]
        assert d["enrolled_count"] == 2
        assert d["new_current_size"] == 2
        db.session.refresh(klass)
        assert klass.current_size == 2

    def test_enroll_accepts_single_student_id_backward_compat(self, client, users, org, klass, admit):

        _, sid = admit(code="HS001")
        r = client.post("/api/v1/classes/%d/enroll" % klass.id, headers=users["H"], json={
            "student_id": sid, "academic_year_id": org["year"].id})
        assert r.status_code == 200
        assert r.get_json()["enrolled_count"] == 1

    def test_enroll_exceeding_size_returns_422_class_size_exceeded(
            self, client, users, org, klass, admit, app):

        from studentapp.models.system_rule import SystemRule
        rule = SystemRule.query.filter_by(rule_key="MAX_CLASS_SIZE").first()
        old = rule.rule_value
        rule.rule_value = "1"
        db.session.commit()
        try:
            ids = []
            for i in range(2):
                _, s = admit(code="HSX%d" % i)
                ids.append(s)
            r = client.post("/api/v1/classes/%d/enroll" % klass.id, headers=users["H"], json={
                "student_ids": ids, "academic_year_id": org["year"].id})
            assert r.status_code == 422
            j = r.get_json()
            assert j["error"] == "CLASS_SIZE_EXCEEDED"
            assert j["current_size"] == 0
            assert j["max_size"] == 1

            db.session.refresh(klass)
            assert klass.current_size == 0
        finally:
            rule.rule_value = old
            db.session.commit()

    def test_enroll_missing_ids_returns_400(self, client, users, org, klass):
        r = client.post("/api/v1/classes/%d/enroll" % klass.id, headers=users["H"], json={
            "academic_year_id": org["year"].id})
        assert r.status_code == 400
        assert r.get_json()["error"] == "BAD_REQUEST"

    def test_transfer_response_contract(self, client, users, org, klass, admit, app):

        cls_b = Class(class_name="10B1", grade_id=org["grades"][0].id,
                      academic_year_id=org["year"].id, current_size=0)
        db.session.add(cls_b)
        db.session.commit()
        _, sid = admit(code="HS001")
        client.post("/api/v1/classes/%d/enroll" % klass.id, headers=users["H"], json={
            "student_id": sid, "academic_year_id": org["year"].id})
        r = client.post("/api/v1/classes/transfer", headers=users["H"], json={
            "student_id": sid, "from_class_id": klass.id, "to_class_id": cls_b.id,
            "academic_year_id": org["year"].id, "transfer_reason": "Chuyen lop"})
        assert r.status_code == 200
        j = r.get_json()
        assert j["student_id"] == sid
        assert j["from_class"] == "10A1"
        assert j["to_class"] == "10B1"
        assert j["from_class_new_size"] == 0
        assert j["to_class_new_size"] == 1
        d = j["data"]
        for k in ("from_class", "to_class", "from_class_new_size", "to_class_new_size"):
            assert k in d
        assert d["transfer_reason"] == "Chuyen lop"

    def test_transfer_to_full_class_returns_422(self, client, users, org, klass, admit, app):

        from studentapp.models.system_rule import SystemRule
        rule = SystemRule.query.filter_by(rule_key="MAX_CLASS_SIZE").first()
        old = rule.rule_value
        rule.rule_value = "1"
        db.session.commit()
        try:
            cls_b = Class(class_name="10B1", grade_id=org["grades"][0].id,
                          academic_year_id=org["year"].id, current_size=0)
            db.session.add(cls_b)
            db.session.commit()
            _, sid = admit(code="HS001")
            client.post("/api/v1/classes/%d/enroll" % klass.id, headers=users["H"], json={
                "student_id": sid, "academic_year_id": org["year"].id})

            client.post("/api/v1/classes/%d/enroll" % cls_b.id, headers=users["H"], json={
                "student_id": sid, "academic_year_id": org["year"].id})
            _, sid2 = admit(code="HS002")
            r = client.post("/api/v1/classes/transfer", headers=users["H"], json={
                "student_id": sid2, "from_class_id": klass.id, "to_class_id": cls_b.id,
                "academic_year_id": org["year"].id})
            assert r.status_code == 422
            assert r.get_json()["error"] == "CLASS_SIZE_EXCEEDED"
        finally:
            rule.rule_value = old
            db.session.commit()

    def test_transfer_same_class_returns_422(self, client, users, org, klass, admit):
        _, sid = admit(code="HS001")
        client.post("/api/v1/classes/%d/enroll" % klass.id, headers=users["H"], json={
            "student_id": sid, "academic_year_id": org["year"].id})
        r = client.post("/api/v1/classes/transfer", headers=users["H"], json={
            "student_id": sid, "to_class_id": klass.id,
            "academic_year_id": org["year"].id})
        assert r.status_code == 422

    def test_transfer_writes_audit_log(self, client, users, org, klass, admit):

        from studentapp.models.audit_log import AuditLog

        cls_b = Class(class_name="10B1", grade_id=org["grades"][0].id,
                      academic_year_id=org["year"].id, current_size=0)
        db.session.add(cls_b)
        db.session.commit()
        _, sid = admit(code="HS001")
        client.post("/api/v1/classes/%d/enroll" % klass.id, headers=users["H"], json={
            "student_id": sid, "academic_year_id": org["year"].id})

        r = client.post("/api/v1/classes/transfer", headers=users["H"], json={
            "student_id": sid, "to_class_id": cls_b.id,
            "academic_year_id": org["year"].id, "transfer_reason": "Chuyen sang lop chuyen"})
        assert r.status_code == 200

        log = AuditLog.query.filter_by(action="TRANSFER_STUDENT").order_by(
            AuditLog.id.desc()).first()
        assert log is not None
        assert log.user_id == users["staff"].id
        d = log.details
        assert d["student_id"] == sid
        assert d["from_class_id"] == klass.id
        assert d["to_class_id"] == cls_b.id
        assert d["transfer_reason"] == "Chuyen sang lop chuyen"
        assert d["to_class_new_size"] == 1

    def test_transfer_to_other_academic_year_returns_422(self, client, users, org, klass, admit):

        other_year = AcademicYear(year_name="2024-2025", start_year=2024,
                                   end_year=2025, is_current=False)
        db.session.add(other_year)
        db.session.commit()
        cls_other = Class(class_name="10C9", grade_id=org["grades"][0].id,
                          academic_year_id=other_year.id, current_size=0)
        db.session.add(cls_other)
        db.session.commit()

        _, sid = admit(code="HS001")
        client.post("/api/v1/classes/%d/enroll" % klass.id, headers=users["H"], json={
            "student_id": sid, "academic_year_id": org["year"].id})
        r = client.post("/api/v1/classes/transfer", headers=users["H"], json={
            "student_id": sid, "to_class_id": cls_other.id,
            "academic_year_id": org["year"].id})
        assert r.status_code == 422
        assert r.get_json()["error"] == "BUSINESS_RULE_VIOLATION"

    def test_transfer_syncs_class_size_from_enrollments(self, client, users, org, klass, admit):

        cls_b = Class(class_name="10B1", grade_id=org["grades"][0].id,
                      academic_year_id=org["year"].id, current_size=99)
        db.session.add(cls_b)
        db.session.commit()
        _, sid = admit(code="HS001")
        client.post("/api/v1/classes/%d/enroll" % klass.id, headers=users["H"], json={
            "student_id": sid, "academic_year_id": org["year"].id})

        r = client.post("/api/v1/classes/transfer", headers=users["H"], json={
            "student_id": sid, "to_class_id": cls_b.id,
            "academic_year_id": org["year"].id})
        assert r.status_code == 200
        db.session.refresh(cls_b)
        db.session.refresh(klass)
        assert cls_b.current_size == 1
        assert klass.current_size == 0

    def test_transfer_allowed_for_academic_role(self, client, users, org, klass, admit):

        cls_b = Class(class_name="10B1", grade_id=org["grades"][0].id,
                      academic_year_id=org["year"].id, current_size=0)
        db.session.add(cls_b)
        db.session.commit()
        _, sid = admit(code="HS001")
        client.post("/api/v1/classes/%d/enroll" % klass.id, headers=users["H"], json={
            "student_id": sid, "academic_year_id": org["year"].id})
        r = client.post("/api/v1/classes/transfer", headers=users["H_A"], json={
            "student_id": sid, "to_class_id": cls_b.id,
            "academic_year_id": org["year"].id})
        assert r.status_code == 200

    def test_transfer_rejected_for_teacher_role(self, client, users, org, klass, admit):

        cls_b = Class(class_name="10B1", grade_id=org["grades"][0].id,
                      academic_year_id=org["year"].id, current_size=0)
        db.session.add(cls_b)
        db.session.commit()
        _, sid = admit(code="HS001")
        r = client.post("/api/v1/classes/transfer", headers=users["H_T"], json={
            "student_id": sid, "to_class_id": cls_b.id,
            "academic_year_id": org["year"].id})
        assert r.status_code == 403

class TestSD07Update:
    def test_update_fields(self, client, users, admit):
        _, sid = admit(code="HS001")
        r = client.put("/api/v1/students/%d" % sid, headers=users["H"], json={
            "full_name": "Ten Moi", "phone": "0987654321", "address": "Ba Dinh"})
        assert r.status_code == 200
        d = r.get_json()["data"]
        assert d["full_name"] == "Ten Moi"
        assert d["phone"] == "0987654321"

    def test_duplicate_email_returns_409(self, client, users, admit):

        admit(code="HS001", email="a@s.local")
        _, s2 = admit(code="HS002", email="b@s.local")
        r = client.put("/api/v1/students/%d" % s2, headers=users["H"],
                       json={"email": "a@s.local"})
        assert r.status_code == 409
        assert r.get_json()["error"] == "DUPLICATE"

    def test_duplicate_phone_returns_409(self, client, users, admit):
        admit(code="HS001", phone="0900000001")
        _, s2 = admit(code="HS002", phone="0900000002")
        r = client.put("/api/v1/students/%d" % s2, headers=users["H"],
                       json={"phone": "0900000001"})
        assert r.status_code == 409

    def test_duplicate_citizen_id_returns_409(self, client, users, admit):
        admit(code="HS001", citizen_id="CCCD001")
        _, s2 = admit(code="HS002", citizen_id="CCCD002")
        r = client.put("/api/v1/students/%d" % s2, headers=users["H"],
                       json={"citizen_id": "CCCD001"})
        assert r.status_code == 409

    def test_keeping_own_email_is_allowed(self, client, users, admit):

        _, sid = admit(code="HS001", email="a@s.local")
        r = client.put("/api/v1/students/%d" % sid, headers=users["H"],
                       json={"email": "a@s.local"})
        assert r.status_code == 200

    def test_update_invalid_age_returns_422(self, client, users, admit):
        _, sid = admit(code="HS001")
        r = client.put("/api/v1/students/%d" % sid, headers=users["H"],
                       json={"date_of_birth": "2016-01-01"})
        assert r.status_code == 422
        assert r.get_json()["current_rules"] == {"min_age": 15, "max_age": 20}

    def test_update_too_long_name_rejected(self, client, users, admit):
        _, sid = admit(code="HS001")
        r = client.put("/api/v1/students/%d" % sid, headers=users["H"],
                       json={"full_name": "A" * 300})
        assert r.status_code == 400
        assert r.get_json()["error"] == "INVALID_LENGTH"

    def test_update_invalid_email_rejected(self, client, users, admit):
        _, sid = admit(code="HS001")
        r = client.put("/api/v1/students/%d" % sid, headers=users["H"],
                       json={"email": "khong-hop-le"})
        assert r.status_code == 400
        assert r.get_json()["error"] == "INVALID_EMAIL"

    def test_update_missing_student_returns_404(self, client, users):
        r = client.put("/api/v1/students/999999", headers=users["H"], json={"full_name": "X"})
        assert r.status_code == 404

    def test_teacher_cannot_update(self, client, users, admit):
        _, sid = admit(code="HS001")
        r = client.put("/api/v1/students/%d" % sid, headers=users["H_T"], json={"full_name": "X"})
        assert r.status_code == 403

    def test_writes_audit_log(self, client, users, admit):
        from studentapp.models.audit_log import AuditLog
        _, sid = admit(code="HS001")
        client.put("/api/v1/students/%d" % sid, headers=users["H"], json={"phone": "0900111222"})
        row = AuditLog.query.filter_by(
            user_id=users["staff"].id, action="UPDATE_STUDENT").first()
        assert row is not None
        assert "phone" in row.details["changed_fields"]

class TestStudentStatus:
    def test_update_status(self, client, users, admit):
        _, sid = admit(code="HS001")
        r = client.patch("/api/v1/students/%d/status" % sid, headers=users["H"],
                         json={"status": "THOI_HOC"})
        assert r.status_code == 200
        assert r.get_json()["data"]["status"] == "THOI_HOC"

    def test_invalid_status_returns_400(self, client, users, admit):
        _, sid = admit(code="HS001")
        r = client.patch("/api/v1/students/%d/status" % sid, headers=users["H"],
                         json={"status": "SAI_STATUS"})
        assert r.status_code == 400
        assert r.get_json()["error"] == "INVALID_STATUS"

    def test_status_change_syncs_enrollment_and_class_size(self, client, users, org, klass, admit):

        _, sid = admit(code="HS001")
        client.post("/api/v1/classes/%d/enroll" % klass.id, headers=users["H"], json={
            "student_id": sid, "academic_year_id": org["year"].id})
        db.session.refresh(klass)
        assert klass.current_size == 1

        r = client.patch("/api/v1/students/%d/status" % sid, headers=users["H"],
                         json={"status": "THOI_HOC"})
        assert r.status_code == 200
        db.session.refresh(klass)
        enr = ClassEnrollment.query.filter_by(student_id=sid).first()
        assert enr.status == EnrollmentStatusEnum.DA_CHUYEN
        assert klass.current_size == 0

    def test_status_back_to_dang_hoc_restores_enrollment(self, client, users, org, klass, admit):
        _, sid = admit(code="HS001")
        client.post("/api/v1/classes/%d/enroll" % klass.id, headers=users["H"], json={
            "student_id": sid, "academic_year_id": org["year"].id})
        client.patch("/api/v1/students/%d/status" % sid, headers=users["H"],
                     json={"status": "THOI_HOC"})
        r = client.patch("/api/v1/students/%d/status" % sid, headers=users["H"],
                         json={"status": "DANG_HOC"})
        assert r.status_code == 200
        db.session.refresh(klass)
        enr = ClassEnrollment.query.filter_by(student_id=sid).first()
        assert enr.status == EnrollmentStatusEnum.DANG_HOC
        assert klass.current_size == 1

    def test_teacher_cannot_change_status(self, client, users, admit):
        _, sid = admit(code="HS001")
        r = client.patch("/api/v1/students/%d/status" % sid, headers=users["H_T"],
                         json={"status": "THOI_HOC"})
        assert r.status_code == 403

class TestSD08SearchAndPrint:
    def test_list_students(self, client, users, admit):
        admit(code="HS001", name="An")
        admit(code="HS002", name="Binh")
        r = client.get("/api/v1/students", headers=users["H"])
        assert r.status_code == 200
        d = r.get_json()["data"]
        assert d["total"] == 2
        for k in ("items", "total", "page", "pages", "per_page"):
            assert k in d

    def test_search_by_name_and_code(self, client, users, admit):
        admit(code="HS001", name="Nguyen Van A")
        admit(code="HS002", name="Tran Van B")
        r = client.get("/api/v1/students?q=Nguyen", headers=users["H"])
        assert r.get_json()["data"]["total"] == 1
        r = client.get("/api/v1/students?q=HS002", headers=users["H"])
        assert r.get_json()["data"]["total"] == 1

    def test_search_by_class(self, client, users, org, klass, admit):

        _, s1 = admit(code="HS001")
        _, s2 = admit(code="HS002")
        client.post("/api/v1/classes/%d/enroll" % klass.id, headers=users["H"], json={
            "student_id": s1, "academic_year_id": org["year"].id})
        r = client.get("/api/v1/students?class_id=%d" % klass.id, headers=users["H"])
        assert r.status_code == 200
        d = r.get_json()["data"]
        assert d["total"] == 1
        assert d["items"][0]["student_code"] == "HS001"

    def test_search_by_status(self, client, users, admit):
        _, sid = admit(code="HS001")
        admit(code="HS002")
        client.patch("/api/v1/students/%d/status" % sid, headers=users["H"],
                     json={"status": "THOI_HOC"})
        r = client.get("/api/v1/students?status=THOI_HOC", headers=users["H"])
        assert r.get_json()["data"]["total"] == 1

    def test_get_detail(self, client, users, admit):
        _, sid = admit(code="HS001")
        r = client.get("/api/v1/students/%d" % sid, headers=users["H"])
        assert r.status_code == 200
        assert r.get_json()["data"]["student_code"] == "HS001"

    def test_get_detail_missing_returns_404(self, client, users):
        r = client.get("/api/v1/students/999999", headers=users["H"])
        assert r.status_code == 404
        assert r.get_json()["error"] == "STUDENT_NOT_FOUND"

    def test_get_by_code(self, client, users, admit):
        admit(code="HS001")
        r = client.get("/api/v1/students/code/HS001", headers=users["H"])
        assert r.status_code == 200
        assert r.get_json()["data"]["student_code"] == "HS001"

    def test_get_by_code_missing_returns_404(self, client, users):
        r = client.get("/api/v1/students/code/NOPE", headers=users["H"])
        assert r.status_code == 404

    def test_teacher_cannot_read_student_outside_own_class(self, client, users, admit, org, klass):

        _, sid = admit(code="HS001")

        r = client.get("/api/v1/students/%d" % sid, headers=users["H_T"])
        assert r.status_code == 403
        r = client.get("/api/v1/students/code/HS001", headers=users["H_T"])
        assert r.status_code == 403

    def test_teacher_can_read_student_in_own_class(self, client, users, admit, org, klass):

        from studentapp.models.teaching_assignment import TeachingAssignment

        _, sid = admit(code="HS001")
        client.post("/api/v1/classes/%d/enroll" % klass.id, headers=users["H"], json={
            "student_id": sid, "academic_year_id": org["year"].id})

        db.session.add(TeachingAssignment(
            teacher_id=users["teacher"].id, class_id=klass.id,
            subject_id=1, semester_id=1, is_locked=False,
        ))
        db.session.commit()

        r = client.get("/api/v1/students/%d" % sid, headers=users["H_T"])
        assert r.status_code == 200
        r = client.get("/api/v1/students/code/HS001", headers=users["H_T"])
        assert r.status_code == 200

    def test_print_json(self, client, users, admit):

        _, sid = admit(code="HS001")
        r = client.get("/api/v1/students/%d/print" % sid, headers=users["H"])
        assert r.status_code == 200, r.get_data(as_text=True)[:300]
        assert "application/json" in (r.headers.get("Content-Type") or "")
        j = r.get_json()
        assert j["success"] is True
        assert j["data"]["student"]["student_code"] == "HS001"
        assert "print_date" in j["data"]

    def test_print_pdf(self, client, users, admit):

        _, sid = admit(code="HS001")
        r = client.get("/api/v1/students/%d/print?format=pdf" % sid, headers=users["H"])
        assert r.status_code == 200
        assert r.headers.get("Content-Type") == "application/pdf"
        assert r.data[:4] == b"%PDF"

    def test_print_missing_student_returns_404(self, client, users):
        r = client.get("/api/v1/students/999999/print", headers=users["H"])
        assert r.status_code == 404

class TestDeleteStudent:

    def test_soft_delete_flags_student_and_keeps_row(self, client, users, admit):

        _, sid = admit(code="HS001")
        r = client.delete("/api/v1/students/%d" % sid, headers=users["H_A"],
                          json={"reason": "Nhập trường sai thông tin"})
        assert r.status_code == 200
        assert r.get_json()["data"]["mode"] == "SOFT"
        st = Student.query.get(sid)
        assert st is not None, "xoá mềm không được xoá hẳn bản ghi"
        assert st.is_deleted is True
        assert st.deleted_at is not None
        assert st.deleted_reason == "Nhập trường sai thông tin"

    def test_soft_delete_removes_from_default_list(self, client, users, admit):

        _, sid = admit(code="HS001")
        client.delete("/api/v1/students/%d" % sid, headers=users["H_A"],
                      json={"reason": "Nhập trùng"})
        r = client.get("/api/v1/students", headers=users["H"])
        assert r.get_json()["data"]["total"] == 0

    def test_soft_delete_still_visible_with_include_deleted(self, client, users, admit):

        _, sid = admit(code="HS001")
        client.delete("/api/v1/students/%d" % sid, headers=users["H_A"],
                      json={"reason": "Nhập trùng"})
        r = client.get("/api/v1/students?include_deleted=true", headers=users["H"])
        data = r.get_json()["data"]
        assert data["total"] == 1
        assert data["items"][0]["is_deleted"] is True

    def test_delete_blocked_when_has_scores(self, client, users, admit):

        from studentapp.models.score import Score
        from studentapp.models.teaching_assignment import TeachingAssignment

        _, sid = admit(code="HS001")
        assignment = TeachingAssignment(
            teacher_id=users["teacher"].id, class_id=1,
            subject_id=1, semester_id=1, is_locked=True,
        )
        db.session.add(assignment)
        db.session.flush()
        db.session.add(Score(assignment_id=assignment.id, student_id=sid, is_draft=False))
        db.session.commit()

        r = client.delete("/api/v1/students/%d" % sid, headers=users["H_A"],
                          json={"reason": "Nhập sai"})
        assert r.status_code == 400
        assert r.get_json()["error"] == "STUDENT_DELETE_BLOCKED"
        blockers = r.get_json()["blockers"]
        assert any(b["code"] == "HAS_SCORES" for b in blockers)
        assert Student.query.get(sid).is_deleted is False

    def test_delete_blocked_when_active_enrollment_current_year(
            self, client, users, org, klass, admit):

        _, sid = admit(code="HS001")
        client.post("/api/v1/classes/%d/enroll" % klass.id, headers=users["H"], json={
            "student_id": sid, "academic_year_id": org["year"].id})
        r = client.delete("/api/v1/students/%d" % sid, headers=users["H_A"],
                          json={"reason": "Nhập sai"})
        assert r.status_code == 400
        blockers = r.get_json()["blockers"]
        assert any(b["code"] == "ACTIVE_ENROLLMENT" for b in blockers)
        assert Student.query.get(sid).is_deleted is False

    def test_staff_can_delete_with_reason(self, client, users, admit):

        _, sid = admit(code="HS001")
        r = client.delete("/api/v1/students/%d" % sid, headers=users["H"],
                          json={"reason": "Nhập trường sai thông tin"})
        assert r.status_code == 200
        assert r.get_json()["data"]["mode"] == "SOFT"

    def test_delete_requires_reason(self, client, users, admit):

        _, sid = admit(code="HS001")
        r = client.delete("/api/v1/students/%d" % sid, headers=users["H_A"], json={})
        assert r.status_code == 400
        assert r.get_json()["error"] == "BAD_REQUEST"

    def test_delete_blank_reason_returns_400(self, client, users, admit):

        _, sid = admit(code="HS001")
        r = client.delete("/api/v1/students/%d" % sid, headers=users["H_A"],
                          json={"reason": "   "})
        assert r.status_code == 400

    def test_teacher_cannot_delete(self, client, users, admit):

        _, sid = admit(code="HS001")
        r = client.delete("/api/v1/students/%d" % sid, headers=users["H_T"])
        assert r.status_code == 403

    def test_delete_missing_returns_404(self, client, users):
        r = client.delete("/api/v1/students/999999", headers=users["H_A"],
                          json={"reason": "Không tồn tại"})
        assert r.status_code == 404

    def test_invalid_mode_returns_400(self, client, users, admit):

        _, sid = admit(code="HS001")
        r = client.delete("/api/v1/students/%d" % sid, headers=users["H_A"],
                          json={"reason": "test", "mode": "SAY_BYE"})
        assert r.status_code == 400

    def test_delete_twice_returns_409(self, client, users, admit):

        _, sid = admit(code="HS001")
        client.delete("/api/v1/students/%d" % sid, headers=users["H_A"],
                      json={"reason": "Nhập trùng"})
        r = client.delete("/api/v1/students/%d" % sid, headers=users["H_A"],
                          json={"reason": "Nhập trùng"})
        assert r.status_code == 409
        assert r.get_json()["error"] == "STUDENT_ALREADY_DELETED"

    def test_delete_writes_audit_log_with_reason(self, client, users, admit):

        from studentapp.models.audit_log import AuditLog

        _, sid = admit(code="HS001")
        client.delete("/api/v1/students/%d" % sid, headers=users["H_A"],
                      json={"reason": "Nhập trùng hồ sơ"})
        log = AuditLog.query.filter_by(action="DELETE_STUDENT_SOFT").order_by(
            AuditLog.id.desc()).first()
        assert log is not None
        assert log.user_id == users["academic"].id
        details = log.details or {}
        assert details.get("student_code") == "HS001"
        assert details.get("reason") == "Nhập trùng hồ sơ"

class TestDeleteModes:
    def test_delete_check_reports_no_data(self, client, users, admit):

        _, sid = admit(code="HS001")
        r = client.get("/api/v1/students/%d/delete-check" % sid, headers=users["H"])
        assert r.status_code == 200
        data = r.get_json()["data"]
        assert data["can_soft_delete"] is True
        assert data["has_data"] is False
        assert data["recommended_mode"] == "SOFT"
        assert data["blockers"] == []

    def test_delete_check_reports_relations(self, client, users, org, klass, admit):

        _, sid = admit(code="HS001")
        client.post("/api/v1/classes/%d/enroll" % klass.id, headers=users["H"], json={
            "student_id": sid, "academic_year_id": org["year"].id})
        r = client.get("/api/v1/students/%d/delete-check" % sid, headers=users["H"])
        assert r.status_code == 200
        data = r.get_json()["data"]
        assert data["has_data"] is True
        assert data["relations"]["enrollments"]["total"] == 1
        assert data["relations"]["enrollments"]["active"] == 1

        assert data["can_soft_delete"] is False
        assert any(b["code"] == "ACTIVE_ENROLLMENT" for b in data["blockers"])

    def test_delete_check_missing_returns_404(self, client, users):
        r = client.get("/api/v1/students/999999/delete-check", headers=users["H"])
        assert r.status_code == 404

    def test_soft_delete_keeps_enrollment_row(self, client, users, org, klass, admit):

        from studentapp.models.class_enrollment import ClassEnrollment

        _, sid = admit(code="HS001")
        client.post("/api/v1/classes/%d/enroll" % klass.id, headers=users["H"], json={
            "student_id": sid, "academic_year_id": org["year"].id})

        client.patch("/api/v1/students/%d/status" % sid, headers=users["H"],
                     json={"status": "THOI_HOC"})
        r = client.delete("/api/v1/students/%d" % sid, headers=users["H_A"],
                          json={"reason": "Nhập trùng", "mode": "SOFT"})
        assert r.status_code == 200
        assert r.get_json()["data"]["mode"] == "SOFT"
        st = Student.query.get(sid)
        assert st is not None
        assert st.is_deleted is True
        assert ClassEnrollment.query.filter_by(student_id=sid).count() == 1

    def test_restore_brings_student_back(self, client, users, admit):

        _, sid = admit(code="HS001")
        client.delete("/api/v1/students/%d" % sid, headers=users["H_A"],
                      json={"reason": "Nhập trùng"})
        r = client.post("/api/v1/students/%d/restore" % sid, headers=users["H_A"],
                        json={"reason": "Xoá nhầm"})
        assert r.status_code == 200
        st = Student.query.get(sid)
        assert st.is_deleted is False
        assert st.deleted_at is None
        assert st.deleted_reason is None
        lst = client.get("/api/v1/students", headers=users["H"])
        assert lst.get_json()["data"]["total"] == 1

    def test_restore_requires_academic_role(self, client, users, admit):

        _, sid = admit(code="HS001")
        client.delete("/api/v1/students/%d" % sid, headers=users["H_A"],
                      json={"reason": "Nhập trùng"})
        r = client.post("/api/v1/students/%d/restore" % sid, headers=users["H"],
                        json={"reason": "Xoá nhầm"})
        assert r.status_code == 403

    def test_teacher_cannot_check_delete(self, client, users, admit):

        _, sid = admit(code="HS001")
        r = client.get("/api/v1/students/%d/delete-check" % sid, headers=users["H_T"])
        assert r.status_code == 403

class TestNoUIRoutes:

    def test_student_ui_route_removed(self, client, users):
        assert client.get("/api/v1/students/ui", headers=users["H"]).status_code == 404

    def test_admit_form_route_removed(self, client, users):
        assert client.get("/api/v1/students/form", headers=users["H"]).status_code == 404

    def test_login_page_route_removed(self, client):
        assert client.get("/login").status_code == 404

    def test_classes_ui_route_removed(self, client):
        assert client.get("/classes-ui").status_code == 404

    def test_enroll_ui_route_removed(self, client, users):
        assert client.get("/classes/enroll-ui", headers=users["H"]).status_code == 404

    def test_unknown_path_returns_json_404(self, client):
        r = client.get("/khong-ton-tai")
        assert r.status_code == 404
        assert r.get_json()["error"] == "NOT_FOUND"
