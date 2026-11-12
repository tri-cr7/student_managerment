"""Test SD09 — GET /assignments/my (danh sách lớp phụ trách của Giáo viên)."""
from studentapp.services import score_service


class TestListMyAssignments:
    """SD09 — Tra cứu danh sách lớp phụ trách."""

    def test_returns_own_assignments(self, app, seed_data):
        """GV chỉ thấy lớp môn học MÌNH phụ trách."""
        result = score_service.list_my_assignments(seed_data["teacher"].id)
        ids = [a["id"] for a in result]
        assert ids == [seed_data["assignment"].id]

    def test_does_not_leak_other_teacher_assignments(self, app, seed_data):
        """GV không thấy lớp của GV khác (rule A11)."""
        result = score_service.list_my_assignments(seed_data["other_teacher"].id)
        ids = [a["id"] for a in result]
        assert ids == [seed_data["other_assignment"].id]
        assert seed_data["assignment"].id not in ids

    def test_includes_class_subject_semester_info(self, app, seed_data):
        """Response có đủ thông tin lớp / môn / kỳ để GV chọn bảng điểm."""
        item = score_service.list_my_assignments(seed_data["teacher"].id)[0]
        assert item["class_name"] == "10A1"
        assert item["subject_name"] == "Toán học 10"
        assert item["semester_name"] == "Học kỳ 1"
        assert item["academic_year_name"] == "2026-2027"

    def test_includes_lock_and_pending_flags(self, app, seed_data):
        """Response có cờ is_locked & has_pending_submission để UI disable nút."""
        item = score_service.list_my_assignments(seed_data["teacher"].id)[0]
        assert item["is_locked"] is False
        assert item["has_pending_submission"] is False


class TestMyAssignmentsEndpoint:
    """API GET /api/v1/assignments/my."""

    def test_requires_authentication(self, app, client):
        resp = client.get("/api/v1/assignments/my")
        assert resp.status_code == 401

    def test_forbidden_for_staff_role(self, app, client, seed_data, auth_headers):
        """Role không phải TEACHER/ACADEMIC bị từ chối (403)."""
        resp = client.get(
            "/api/v1/assignments/my",
            headers=auth_headers("STAFF", seed_data["staff"].id),
        )
        assert resp.status_code == 403

    def test_teacher_gets_own_list(self, app, client, seed_data, auth_headers):
        resp = client.get(
            "/api/v1/assignments/my",
            headers=auth_headers("TEACHER", seed_data["teacher"].id),
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["success"] is True
        data = body["data"]
        assert len(data) == 1
        assert data[0]["class_name"] == "10A1"
