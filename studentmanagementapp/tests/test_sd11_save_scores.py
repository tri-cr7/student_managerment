"""Test SD11 — POST /scores/batch (nhập điểm lớp vào bảng điểm TẠM)."""
import pytest

from studentapp.extensions import db
from studentapp.models.score import Score
from studentapp.models.score_submission import ScoreSubmission, SubmissionStatusEnum
from studentapp.services import score_service


def _payload(seed_data, scores):
    return {"assignment_id": seed_data["assignment"].id, "scores": scores}


class TestSaveBatchHappyPath:
    """Luồng chuẩn: nhập điểm → lưu bảng điểm tạm → tính ĐTB."""

    def test_saves_scores_as_draft(self, app, seed_data):
        """Điểm lưu vào bảng điểm TẠM (is_draft = True)."""
        st = seed_data["students"][0]
        result = score_service.save_batch_scores(
            _payload(seed_data, [{"student_id": st.id, "score_15m_1": 8.0}]),
            seed_data["teacher"].id,
        )
        assert result["data"]["updated_count"] == 1

        row = Score.query.filter_by(
            assignment_id=seed_data["assignment"].id, student_id=st.id
        ).first()
        assert row is not None
        assert row.is_draft is True
        assert float(row.score_15m_1) == 8.0

    def test_calculates_average(self, app, seed_data):
        """ĐTB được tính tự động theo công thức trọng số."""
        st = seed_data["students"][0]
        score_service.save_batch_scores(
            _payload(seed_data, [
                {"student_id": st.id, "score_15m_1": 8.0, "score_45m_1": 7.5, "score_final": 8.5}
            ]),
            seed_data["teacher"].id,
        )
        row = Score.query.filter_by(student_id=st.id).first()
        # tử số = 8*1 + 7.5*2 + 8.5*3 = 8 + 15 + 25.5 = 48.5
        # mẫu số = 1*1 + 1*2 + 1*3 = 6  →  ĐTB = 48.5/6 = 8.0833...
        assert float(row.average_score) == pytest.approx(8.08, abs=0.01)
        assert row.is_passed is True

    def test_zero_score_is_saved_and_counted(self, app, seed_data):
        """Điểm 0.00 (HS vắng) được lưu và vẫn tính vào ĐTB."""
        st = seed_data["students"][0]
        score_service.save_batch_scores(
            _payload(seed_data, [{"student_id": st.id, "score_15m_1": 0.0, "score_15m_2": 8.0}]),
            seed_data["teacher"].id,
        )
        row = Score.query.filter_by(student_id=st.id).first()
        assert float(row.score_15m_1) == 0.0
        assert float(row.average_score) == pytest.approx(4.0)

    def test_absent_alias_v_saved_as_zero(self, app, seed_data):
        """Nhập 'v' (vắng) được quy về 0 điểm, vẫn tính vào ĐTB."""
        st = seed_data["students"][0]
        score_service.save_batch_scores(
            _payload(seed_data, [{"student_id": st.id, "score_15m_1": "v", "score_15m_2": 8.0}]),
            seed_data["teacher"].id,
        )
        row = Score.query.filter_by(student_id=st.id).first()
        assert float(row.score_15m_1) == 0.0
        assert float(row.average_score) == pytest.approx(4.0)

    def test_creates_row_for_each_student(self, app, seed_data):
        """Mỗi học sinh được nhập tạo 1 dòng điểm riêng."""
        rows = [
            {"student_id": st.id, "score_15m_1": 7.0 + i}
            for i, st in enumerate(seed_data["students"])
        ]
        score_service.save_batch_scores(_payload(seed_data, rows), seed_data["teacher"].id)
        count = Score.query.filter_by(assignment_id=seed_data["assignment"].id).count()
        assert count == 3


class TestPartialUpdate:
    """Partial update — ô null giữ nguyên, không xoá dữ liệu đã chấm."""

    def test_null_preserves_existing_value(self, app, seed_data):
        """Gửi null cho ô đã có điểm → giữ nguyên giá trị cũ (chống mất dữ liệu)."""
        st = seed_data["students"][0]
        score_service.save_batch_scores(
            _payload(seed_data, [{"student_id": st.id, "score_15m_1": 8.0, "score_15m_2": 9.0}]),
            seed_data["teacher"].id,
        )
        # Lần 2: chỉ gửi score_15m_1, các ô khác null
        score_service.save_batch_scores(
            _payload(seed_data, [{"student_id": st.id, "score_15m_1": 7.0, "score_15m_2": None}]),
            seed_data["teacher"].id,
        )
        row = Score.query.filter_by(student_id=st.id).first()
        assert float(row.score_15m_1) == 7.0
        assert float(row.score_15m_2) == 9.0  # GIỮ NGUYÊN

    def test_omitted_column_also_preserved(self, app, seed_data):
        """Ô không được gửi lên (hoặc gửi null) đều giữ nguyên."""
        st = seed_data["students"][0]
        score_service.save_batch_scores(
            _payload(seed_data, [{"student_id": st.id, "score_final": 9.0}]),
            seed_data["teacher"].id,
        )
        score_service.save_batch_scores(
            _payload(seed_data, [{"student_id": st.id, "score_15m_1": 6.0}]),
            seed_data["teacher"].id,
        )
        row = Score.query.filter_by(student_id=st.id).first()
        assert float(row.score_final) == 9.0
        assert float(row.score_15m_1) == 6.0


class TestValidationRules:
    """Các rule validation của SD11."""

    def test_rejects_score_out_of_range(self, app, seed_data):
        """Điểm > 10 bị từ chối (rule A1)."""
        from studentapp.exceptions import InvalidScoreRangeError

        st = seed_data["students"][0]
        with pytest.raises(InvalidScoreRangeError):
            score_service.save_batch_scores(
                _payload(seed_data, [{"student_id": st.id, "score_15m_1": 11.0}]),
                seed_data["teacher"].id,
            )

    def test_rejects_negative_score(self, app, seed_data):
        """Điểm < 0 bị từ chối (rule A1)."""
        from studentapp.exceptions import InvalidScoreRangeError

        st = seed_data["students"][0]
        with pytest.raises(InvalidScoreRangeError):
            score_service.save_batch_scores(
                _payload(seed_data, [{"student_id": st.id, "score_15m_1": -1.0}]),
                seed_data["teacher"].id,
            )

    def test_rejects_column_over_limit(self, app, seed_data):
        """Cột vượt quá MAX_COL quy định bị từ chối (rule A2/A3/A4)."""
        from studentapp.exceptions import InvalidColumnCountError
        from studentapp.models.system_rule import SystemRule

        SystemRule.query.filter_by(rule_key="MAX_COL_15M").first().rule_value = "2"
        from studentapp.extensions import db
        db.session.commit()

        st = seed_data["students"][0]
        with pytest.raises(InvalidColumnCountError):
            score_service.save_batch_scores(
                _payload(seed_data, [{"student_id": st.id, "score_15m_3": 8.0}]),
                seed_data["teacher"].id,
            )

    def test_rejects_student_not_in_class(self, app, seed_data):
        """Học sinh không thuộc lớp bị từ chối (rule A6)."""
        from studentapp.exceptions import ValidationError

        with pytest.raises(ValidationError):
            score_service.save_batch_scores(
                _payload(seed_data, [{"student_id": 999999, "score_15m_1": 8.0}]),
                seed_data["teacher"].id,
            )

    def test_rejects_duplicate_student_in_batch(self, app, seed_data):
        """Trùng học sinh trong 1 request bị từ chối (rule A5)."""
        from studentapp.exceptions import ValidationError

        st = seed_data["students"][0]
        with pytest.raises(ValidationError) as exc:
            score_service.save_batch_scores(
                _payload(seed_data, [
                    {"student_id": st.id, "score_15m_1": 8.0},
                    {"student_id": st.id, "score_15m_2": 9.0},
                ]),
                seed_data["teacher"].id,
            )
        assert exc.value.error == "DUPLICATE_STUDENT_IN_BATCH"

    def test_rejects_missing_assignment_id(self, app, seed_data):
        """Thiếu assignment_id bị từ chối."""
        from studentapp.exceptions import ValidationError

        with pytest.raises(ValidationError):
            score_service.save_batch_scores({"scores": []}, seed_data["teacher"].id)

    def test_rejects_empty_scores_list(self, app, seed_data):
        """Danh sách điểm rỗng bị từ chối."""
        from studentapp.exceptions import ValidationError

        with pytest.raises(ValidationError):
            score_service.save_batch_scores(
                {"assignment_id": seed_data["assignment"].id, "scores": []},
                seed_data["teacher"].id,
            )


class TestAuthorizationRules:
    """Quyền truy cập — GV chỉ được sửa lớp MÌNH phụ trách."""

    def test_forbidden_for_other_teacher(self, app, seed_data):
        """GV khác không được ghi điểm cho lớp không phụ trách (rule A11)."""
        from studentapp.exceptions import PermissionDeniedError

        st = seed_data["students"][0]
        with pytest.raises(PermissionDeniedError):
            score_service.save_batch_scores(
                _payload(seed_data, [{"student_id": st.id, "score_15m_1": 8.0}]),
                seed_data["other_teacher"].id,
            )

    def test_forbidden_when_assignment_locked(self, app, seed_data):
        """Bảng điểm đã chốt → GV không sửa trực tiếp được (rule A8)."""
        from studentapp.exceptions import ScoreTableLockedError

        assignment = seed_data["assignment"]
        assignment.is_locked = True
        db.session.commit()

        st = seed_data["students"][0]
        with pytest.raises(ScoreTableLockedError):
            score_service.save_batch_scores(
                _payload(seed_data, [{"student_id": st.id, "score_15m_1": 8.0}]),
                seed_data["teacher"].id,
            )

    def test_forbidden_when_submission_pending(self, app, seed_data):
        """Đang có đơn gửi duyệt PENDING → GV phải hủy đơn trước (rule A10)."""
        from studentapp.exceptions import ScoreSubmissionPendingError

        assignment = seed_data["assignment"]
        db.session.add(
            ScoreSubmission(
                assignment_id=assignment.id,
                teacher_id=seed_data["teacher"].id,
                status=SubmissionStatusEnum.PENDING,
            )
        )
        db.session.commit()

        st = seed_data["students"][0]
        with pytest.raises(ScoreSubmissionPendingError):
            score_service.save_batch_scores(
                _payload(seed_data, [{"student_id": st.id, "score_15m_1": 8.0}]),
                seed_data["teacher"].id,
            )


class TestBatchEndpoint:
    """API POST /api/v1/scores/batch."""

    def test_requires_authentication(self, app, client):
        resp = client.post("/api/v1/scores/batch", json={})
        assert resp.status_code == 401

    def test_teacher_saves_scores(self, app, client, seed_data, auth_headers):
        st = seed_data["students"][0]
        resp = client.post(
            "/api/v1/scores/batch",
            json={
                "assignment_id": seed_data["assignment"].id,
                "scores": [{"student_id": st.id, "score_15m_1": 8.0}],
            },
            headers=auth_headers("TEACHER", seed_data["teacher"].id),
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["success"] is True
        assert body["data"]["updated_count"] == 1
        assert body["data"]["is_draft"] is True

    def test_invalid_score_returns_422(self, app, client, seed_data, auth_headers):
        st = seed_data["students"][0]
        resp = client.post(
            "/api/v1/scores/batch",
            json={
                "assignment_id": seed_data["assignment"].id,
                "scores": [{"student_id": st.id, "score_15m_1": 99.0}],
            },
            headers=auth_headers("TEACHER", seed_data["teacher"].id),
        )
        assert resp.status_code == 422
        assert resp.get_json()["error"] == "INVALID_SCORE_RANGE"

    def test_other_teacher_gets_403(self, app, client, seed_data, auth_headers):
        st = seed_data["students"][0]
        resp = client.post(
            "/api/v1/scores/batch",
            json={
                "assignment_id": seed_data["assignment"].id,
                "scores": [{"student_id": st.id, "score_15m_1": 8.0}],
            },
            headers=auth_headers("TEACHER", seed_data["other_teacher"].id),
        )
        assert resp.status_code == 403
