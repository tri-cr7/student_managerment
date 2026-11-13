"""Test cụm cuối Giáo vụ: SD21 rules, SD22 subjects, SD20 reports, SD15 audit, SD26 years, SD27 homeroom."""
from studentapp.services import catalog_service, report_service


class TestRules:
    def test_list_and_get(self, app, seed_data):
        rules = catalog_service.list_rules()
        assert any(r["rule_key"] == "MAX_CLASS_SIZE" for r in rules)
        one = catalog_service.get_rule("MAX_CLASS_SIZE")
        assert one["rule_value"] == "40"

    def test_update_ok(self, app, seed_data):
        out = catalog_service.update_rule("MAX_CLASS_SIZE", "45",
                                          actor_id=seed_data["academic"].id)
        assert out["new_value"] == "45"
        assert catalog_service.get_rule("MAX_CLASS_SIZE")["rule_value"] == "45"

    def test_update_logic_rejected(self, app, seed_data):
        from studentapp.exceptions import BusinessRuleError
        try:
            catalog_service.update_rule("MIN_AGE", "25",
                                        actor_id=seed_data["academic"].id)
        except BusinessRuleError as e:
            assert e.error == "INVALID_RULE_LOGIC"
            return
        raise AssertionError("MIN_AGE=25 > MAX_AGE phải bị chặn!")

    def test_bulk_atomic(self, app, seed_data):
        from studentapp.exceptions import BusinessRuleError
        before = catalog_service.get_rule("MAX_CLASS_SIZE")["rule_value"]
        try:
            catalog_service.bulk_update_rules(
                [{"rule_key": "MAX_CLASS_SIZE", "rule_value": "42"},
                 {"rule_key": "MIN_AGE", "rule_value": "99"}],
                actor_id=seed_data["academic"].id)
        except BusinessRuleError:
            pass
        else:
            raise AssertionError("Bulk phi logic phải rollback!")
        assert catalog_service.get_rule("MAX_CLASS_SIZE")["rule_value"] == before

    def test_rules_endpoints(self, app, client, seed_data, auth_headers):
        h = auth_headers("ACADEMIC", seed_data["academic"].id)
        assert client.get("/api/v1/rules", headers=h).status_code == 200
        r = client.put("/api/v1/rules/MAX_CLASS_SIZE",
                       json={"rule_value": "44"}, headers=h)
        assert r.status_code == 200, r.get_json()
        r = client.put("/api/v1/rules/MIN_AGE",
                       json={"rule_value": "99"}, headers=h)
        assert r.status_code == 422
        r = client.put("/api/v1/rules/bulk",
                       json={"rules": [{"rule_key": "MAX_CLASS_SIZE",
                                        "rule_value": "43"}]}, headers=h)
        assert r.status_code == 200


class TestSubjects:
    def test_crud_roundtrip(self, app, seed_data):
        s = catalog_service.create_subject(
            {"subject_code": "LY10", "subject_name": "Vat ly 10",
             "grade_id": seed_data["grade"].id, "periods_count": 35},
            actor_id=seed_data["academic"].id)
        assert s["subject_code"] == "LY10"
        got = catalog_service.get_subject(s["id"])
        assert got["grade_name"] == "Khối 10"
        found = catalog_service.list_subjects(keyword="vat ly")
        assert any(x["id"] == s["id"] for x in found)
        upd = catalog_service.update_subject(s["id"], {"subject_name": "Vật lý 10"},
                                             actor_id=seed_data["academic"].id)
        assert upd["subject_name"] == "Vật lý 10"
        catalog_service.delete_subject(s["id"], actor_id=seed_data["academic"].id)
        from studentapp.exceptions import NotFoundError
        try:
            catalog_service.get_subject(s["id"])
        except NotFoundError:
            return
        raise AssertionError("Xóa rồi phải 404!")

    def test_delete_blocked_with_assignments(self, app, seed_data):
        from studentapp.exceptions import BusinessRuleError
        try:
            catalog_service.delete_subject(seed_data["subject"].id,
                                           actor_id=seed_data["academic"].id)
        except BusinessRuleError as e:
            assert e.error == "SUBJECT_HAS_ASSIGNMENTS"
            return
        raise AssertionError("Môn đã có phân công phải chặn xóa!")

    def test_subject_endpoints(self, app, client, seed_data, auth_headers):
        h = auth_headers("ACADEMIC", seed_data["academic"].id)
        r = client.get("/api/v1/subjects?keyword=toan", headers=h)
        assert r.status_code == 200
        assert len(r.get_json()["data"]) >= 1
        r = client.post("/api/v1/subjects",
                        json={"subject_code": "HOA10", "subject_name": "Hoa 10",
                              "grade_id": seed_data["grade"].id},
                        headers=h)
        assert r.status_code == 201, r.get_json()
        nid = r.get_json()["data"]["id"]
        r = client.delete(f"/api/v1/subjects/{nid}", headers=h)
        assert r.status_code == 200
        # xóa môn đang dạy → 422
        r = client.delete(f"/api/v1/subjects/{seed_data['subject'].id}", headers=h)
        assert r.status_code == 422


class TestYearsSemestersHomeroom:
    def test_year_current_singleton(self, app, seed_data):
        y2 = catalog_service.create_academic_year(
            {"year_name": "2027-2028", "start_year": 2027, "end_year": 2028},
            actor_id=seed_data["academic"].id)
        catalog_service.set_current_year(y2["id"], actor_id=seed_data["academic"].id)
        cur = catalog_service.get_current_year()
        assert cur["id"] == y2["id"]
        from studentapp.models.academic_year import AcademicYear
        assert AcademicYear.query.filter_by(is_current=True).count() == 1

    def test_semester_crud(self, app, seed_data):
        s = catalog_service.create_semester(
            {"semester_name": "HK2",
             "academic_year_id": seed_data["academic_year"].id, "factor": 2},
            actor_id=seed_data["academic"].id)
        assert s["semester_name"] == "HK2"
        cur = catalog_service.set_current_semester(
            s["id"], actor_id=seed_data["academic"].id)
        assert cur["is_current"] is True

    def test_homeroom(self, app, seed_data):
        out = catalog_service.set_homeroom(
            seed_data["class"].id, seed_data["teacher"].id,
            actor_id=seed_data["academic"].id)
        assert out["homeroom_teacher_id"] == seed_data["teacher"].id
        assert out["homeroom_teacher_name"] == "Giáo Viên Một"
        from studentapp.exceptions import ValidationError
        try:
            catalog_service.set_homeroom(
                seed_data["class"].id, seed_data["staff"].id,
                actor_id=seed_data["academic"].id)
        except ValidationError as e:
            assert e.error == "INVALID_HOMEROOM_TEACHER"
            return
        raise AssertionError("STAFF không thể làm GVCN!")

    def test_year_endpoints(self, app, client, seed_data, auth_headers):
        h = auth_headers("ACADEMIC", seed_data["academic"].id)
        r = client.get("/api/v1/academic-years", headers=h)
        assert r.status_code == 200
        r = client.post("/api/v1/academic-years",
                        json={"year_name": "2028-2029",
                              "start_year": 2028, "end_year": 2029}, headers=h)
        assert r.status_code == 201, r.get_json()
        nid = r.get_json()["data"]["id"]
        r = client.put(f"/api/v1/academic-years/{nid}/current", headers=h)
        assert r.status_code == 200
        assert r.get_json()["data"]["is_current"] is True
        r = client.put(f"/api/v1/classes/{seed_data['class'].id}/homeroom",
                       json={"teacher_id": seed_data["teacher"].id}, headers=h)
        assert r.status_code == 200, r.get_json()
        r = client.get("/api/v1/grades", headers=h)
        assert r.status_code == 200


class TestReportsAudit:
    def _seed_official(self, seed_data):
        from studentapp.extensions import db
        from studentapp.models.score import Score
        from studentapp.services import score_service
        rows = []
        for i, st in enumerate(seed_data["students"]):
            rows.append({
                "student_id": st.id, "score_15m_1": 4.0 + i,
                "score_15m_2": 8.0, "score_final": 8.5})
        score_service.save_batch_scores(
            {"assignment_id": seed_data["assignment"].id, "scores": rows},
            seed_data["teacher"].id)
        for row in Score.query.filter_by(
                assignment_id=seed_data["assignment"].id).all():
            row.is_draft = False
            db.session.add(row)
        db.session.commit()

    def test_subject_summary_counts(self, app, seed_data):
        self._seed_official(seed_data)
        out = report_service.subject_summary(seed_data["subject"].id,
                                             seed_data["semester"].id)
        assert out["passing_threshold"] == 5.0
        # Cả 2 lớp 10A1/10B1 đều có phân công cùng môn → summary có 2 dòng;
        # chỉ 10A1 có học sinh (3 HS đều đạt), 10B1 sĩ số 0.
        assert len(out["summary"]) == 2
        row = next(r for r in out["summary"] if r["class_name"] == "10A1")
        assert row["class_size"] == 3
        # HS1: ĐTB ~ (4+8+8.5*3)/5 = 6.9 đạt; HS2, HS3 đạt → 3/3
        assert row["passed_count"] == 3
        assert row["pass_rate"] == 100.0

    def test_chart_and_exports(self, app, seed_data):
        self._seed_official(seed_data)
        ch = report_service.chart_data(seed_data["subject"].id,
                                       seed_data["semester"].id)
        assert ch["data"]["labels"] == ["10A1", "10B1"]
        xbytes, _ = report_service.build_excel(seed_data["subject"].id,
                                               seed_data["semester"].id)
        assert xbytes[:2] == b"PK"
        pbytes, _ = report_service.build_pdf(seed_data["subject"].id,
                                             seed_data["semester"].id)
        assert pbytes[:4] == b"%PDF"

    def test_report_endpoints(self, app, client, seed_data, auth_headers):
        self._seed_official(seed_data)
        h = auth_headers("ACADEMIC", seed_data["academic"].id)
        q = (f"?subject_id={seed_data['subject'].id}"
             f"&semester_id={seed_data['semester'].id}")
        assert client.get(f"/api/v1/reports/subject-summary{q}", headers=h).status_code == 200
        assert client.get(f"/api/v1/reports/chart-data{q}", headers=h).status_code == 200
        r = client.get(f"/api/v1/reports/export/excel{q}", headers=h)
        assert r.status_code == 200
        assert r.data[:2] == b"PK"
        r = client.get(f"/api/v1/reports/export/pdf{q}", headers=h)
        assert r.status_code == 200
        assert r.data[:4] == b"%PDF"

    def test_audit_endpoints(self, app, client, seed_data, auth_headers):
        h = auth_headers("ACADEMIC", seed_data["academic"].id)
        r = client.get("/api/v1/admin/audit-logs", headers=h)
        assert r.status_code == 200
        assert r.get_json()["data"]["total"] >= 0
        r = client.get("/api/v1/admin/audit-logs/export", headers=h)
        assert r.status_code == 200
        assert r.data[:2] == b"PK"
