"""Test đọc điểm — GET /scores/assignment/{id} & GET /scores/student/{id}.

Quy tắc quan trọng: API học sinh mặc định **CHỈ** trả điểm chính thức
(đã duyệt, ``is_draft = false``) để không lộ điểm tạm ra ngoài.
"""
from studentapp.extensions import db
from studentapp.models.score import Score
from studentapp.services import score_service


def _seed_scores(seed_data):
    rows = []
    for i, st in enumerate(seed_data["students"]):
        rows.append(
            {
                "student_id": st.id,
                "score_15m_1": 7.0 + i,
                "score_15m_2": 8.0,
                "score_final": 8.5,
            }
        )
    score_service.save_batch_scores(
        {"assignment_id": seed_data["assignment"].id, "scores": rows},
        seed_data["teacher"].id,
    )


class TestGetAssignmentScores:
    """Xem bảng điểm của lớp."""

    def test_returns_score_list(self, app, seed_data):
        """Trả về danh sách điểm kèm thông tin học sinh."""
        _seed_scores(seed_data)
        result = score_service.get_assignment_scores(
            seed_data["assignment"].id, seed_data["teacher"].id
        )
        assert len(result["score_list"]) == 3
        row = result["score_list"][0]
        assert "student_code" in row
        assert "full_name" in row
        assert "average_score" in row
        assert "is_draft" in row

    def test_includes_nine_score_columns(self, app, seed_data):
        """Mỗi dòng có đủ 9 cột điểm."""
        _seed_scores(seed_data)
        result = score_service.get_assignment_scores(
            seed_data["assignment"].id, seed_data["teacher"].id
        )
        row = result["score_list"][0]
        for col in (
            "score_15m_1", "score_15m_2", "score_15m_3", "score_15m_4", "score_15m_5",
            "score_45m_1", "score_45m_2", "score_45m_3", "score_final",
        ):
            assert col in row

    def test_includes_class_metadata(self, app, seed_data):
        """Response có tên lớp, môn, năm học."""
        _seed_scores(seed_data)
        result = score_service.get_assignment_scores(
            seed_data["assignment"].id, seed_data["teacher"].id
        )
        assert result["class_name"] == "10A1"
        assert result["subject_name"] == "Toán học 10"
        assert result["academic_year"] == "2026-2027"

    def test_forbidden_for_other_teacher(self, app, seed_data):
        """GV khác không xem được bảng điểm lớp không phụ trách."""
        from studentapp.exceptions import PermissionDeniedError
        import pytest

        with pytest.raises(PermissionDeniedError):
            score_service.get_assignment_scores(
                seed_data["assignment"].id, seed_data["other_teacher"].id
            )


class TestGetStudentScores:
    """Xem điểm của 1 học sinh."""

    def test_hides_draft_scores_by_default(self, app, seed_data):
        """Mặc định KHÔNG trả điểm tạm (chỉ điểm chính thức)."""
        _seed_scores(seed_data)
        result = score_service.get_student_scores(
            seed_data["students"][0].id, seed_data["teacher"].id, include_draft=False
        )
        assert all(r["is_draft"] is False for r in result["scores"])

    def test_includes_draft_when_requested(self, app, seed_data):
        """include_draft=True ⇒ trả cả điểm tạm."""
        _seed_scores(seed_data)
        result = score_service.get_student_scores(
            seed_data["students"][0].id, seed_data["teacher"].id, include_draft=True
        )
        assert any(r["is_draft"] is True for r in result["scores"])

    def test_returns_student_identity(self, app, seed_data):
        """Response có mã + tên học sinh."""
        _seed_scores(seed_data)
        result = score_service.get_student_scores(
            seed_data["students"][0].id, seed_data["teacher"].id
        )
        assert result["student_code"].startswith("HS")
        assert result["full_name"]

    def test_404_for_unknown_student(self, app, seed_data):
        """Không tìm thấy học sinh → 404."""
        from studentapp.exceptions import NotFoundError
        import pytest

        with pytest.raises(NotFoundError):
            score_service.get_student_scores(999999, seed_data["teacher"].id)


class TestReadEndpoints:
    """API đọc điểm."""

    def test_assignment_scores_endpoint(self, app, client, seed_data, auth_headers):
        _seed_scores(seed_data)
        resp = client.get(
            f"/api/v1/scores/assignment/{seed_data['assignment'].id}",
            headers=auth_headers("TEACHER", seed_data["teacher"].id),
        )
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert len(data["score_list"]) == 3

    def test_student_scores_endpoint(self, app, client, seed_data, auth_headers):
        _seed_scores(seed_data)
        resp = client.get(
            f"/api/v1/scores/student/{seed_data['students'][0].id}",
            headers=auth_headers("TEACHER", seed_data["teacher"].id),
        )
        assert resp.status_code == 200
        assert resp.get_json()["data"]["student_code"]

    def test_student_scores_endpoint_include_draft(self, app, client, seed_data, auth_headers):
        _seed_scores(seed_data)
        resp = client.get(
            f"/api/v1/scores/student/{seed_data['students'][0].id}?include_draft=true",
            headers=auth_headers("TEACHER", seed_data["teacher"].id),
        )
        assert resp.status_code == 200
        scores = resp.get_json()["data"]["scores"]
        assert any(s["is_draft"] is True for s in scores)

    def test_requires_authentication(self, app, client, seed_data):
        resp = client.get(f"/api/v1/scores/assignment/{seed_data['assignment'].id}")
        assert resp.status_code == 401
