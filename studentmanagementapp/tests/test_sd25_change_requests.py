import pytest

from studentapp.extensions import db
from studentapp.models.score import Score
from studentapp.models.score_change_detail import ScoreChangeDetail
from studentapp.models.score_change_request import ScoreChangeRequest
from studentapp.services import score_service

def _seed_locked_scores(seed_data):

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
    for row in Score.query.filter_by(assignment_id=seed_data["assignment"].id).all():
        row.is_draft = False
        db.session.add(row)
    seed_data["assignment"].is_locked = True
    db.session.commit()

class TestCreateChangeRequest:

    def test_creates_request_with_details(self, app, seed_data):

        _seed_locked_scores(seed_data)
        st = seed_data["students"][0]
        result = score_service.create_change_request(
            {
                "assignment_id": seed_data["assignment"].id,
                "reason": "Học sinh bị chấm nhầm điểm kiểm tra 15 phút.",
                "changes": [
                    {"student_id": st.id, "score_column": "score_15m_1", "new_value": 9.0}
                ],
            },
            seed_data["teacher"].id,
        )
        assert result["status"] == "PENDING"
        assert result["total_changes"] == 1
        assert result["is_batch"] is False
        assert len(result["details"]) == 1
        detail = result["details"][0]
        assert detail["score_column"] == "score_15m_1"
        assert detail["old_value"] == 7.0
        assert detail["new_value"] == 9.0

    def test_creates_batch_request(self, app, seed_data):

        _seed_locked_scores(seed_data)
        s1, s2 = seed_data["students"][0], seed_data["students"][1]
        result = score_service.create_change_request(
            {
                "assignment_id": seed_data["assignment"].id,
                "reason": "Nhóm học sinh ngồi sai vị trí, đề nghị chấm lại.",
                "changes": [
                    {"student_id": s1.id, "score_column": "score_15m_1", "new_value": 9.0},
                    {"student_id": s2.id, "score_column": "score_final", "new_value": 9.5},
                ],
            },
            seed_data["teacher"].id,
        )
        assert result["is_batch"] is True
        assert result["total_changes"] == 2
        assert len(result["details"]) == 2

    def test_old_value_is_not_null(self, app, seed_data):

        _seed_locked_scores(seed_data)
        st = seed_data["students"][0]
        score_service.create_change_request(
            {
                "assignment_id": seed_data["assignment"].id,
                "reason": "Xin xem xét lại.",
                "changes": [
                    {"student_id": st.id, "score_column": "score_15m_1", "new_value": 9.0}
                ],
            },
            seed_data["teacher"].id,
        )
        detail = ScoreChangeDetail.query.first()
        assert detail.old_value is not None
        assert float(detail.old_value) == 7.0

    def test_persists_to_database(self, app, seed_data):

        _seed_locked_scores(seed_data)
        st = seed_data["students"][0]
        score_service.create_change_request(
            {
                "assignment_id": seed_data["assignment"].id,
                "reason": "Xin xem xét lại.",
                "changes": [
                    {"student_id": st.id, "score_column": "score_15m_1", "new_value": 9.0}
                ],
            },
            seed_data["teacher"].id,
        )
        assert ScoreChangeRequest.query.count() == 1
        assert ScoreChangeDetail.query.count() == 1

    def test_does_not_change_actual_score(self, app, seed_data):

        _seed_locked_scores(seed_data)
        st = seed_data["students"][0]
        score_service.create_change_request(
            {
                "assignment_id": seed_data["assignment"].id,
                "reason": "Xin xem xét lại.",
                "changes": [
                    {"student_id": st.id, "score_column": "score_15m_1", "new_value": 9.0}
                ],
            },
            seed_data["teacher"].id,
        )
        row = Score.query.filter_by(student_id=st.id).first()
        db.session.refresh(row)
        assert float(row.score_15m_1) == 7.0

class TestChangeRequestValidation:

    def test_rejects_when_table_not_locked(self, app, seed_data):

        from studentapp.exceptions import ScoreTableNotLockedError

        st = seed_data["students"][0]
        score_service.save_batch_scores(
            {"assignment_id": seed_data["assignment"].id,
             "scores": [{"student_id": st.id, "score_15m_1": 8.0}]},
            seed_data["teacher"].id,
        )
        with pytest.raises(ScoreTableNotLockedError):
            score_service.create_change_request(
                {
                    "assignment_id": seed_data["assignment"].id,
                    "reason": "Xin sửa điểm.",
                    "changes": [
                        {"student_id": st.id, "score_column": "score_15m_1", "new_value": 9.0}
                    ],
                },
                seed_data["teacher"].id,
            )

    def test_rejects_missing_reason(self, app, seed_data):

        from studentapp.exceptions import ValidationError

        _seed_locked_scores(seed_data)
        st = seed_data["students"][0]
        with pytest.raises(ValidationError):
            score_service.create_change_request(
                {
                    "assignment_id": seed_data["assignment"].id,
                    "reason": "   ",
                    "changes": [
                        {"student_id": st.id, "score_column": "score_15m_1", "new_value": 9.0}
                    ],
                },
                seed_data["teacher"].id,
            )

    def test_rejects_empty_changes(self, app, seed_data):

        from studentapp.exceptions import ValidationError

        _seed_locked_scores(seed_data)
        with pytest.raises(ValidationError):
            score_service.create_change_request(
                {
                    "assignment_id": seed_data["assignment"].id,
                    "reason": "Xin sửa điểm.",
                    "changes": [],
                },
                seed_data["teacher"].id,
            )

    def test_rejects_invalid_column(self, app, seed_data):

        from studentapp.exceptions import InvalidColumnNameError

        _seed_locked_scores(seed_data)
        st = seed_data["students"][0]
        with pytest.raises(InvalidColumnNameError):
            score_service.create_change_request(
                {
                    "assignment_id": seed_data["assignment"].id,
                    "reason": "Xin sửa điểm.",
                    "changes": [
                        {"student_id": st.id, "score_column": "score_hack", "new_value": 9.0}
                    ],
                },
                seed_data["teacher"].id,
            )

    def test_rejects_out_of_range_new_value(self, app, seed_data):

        from studentapp.exceptions import InvalidScoreRangeError

        _seed_locked_scores(seed_data)
        st = seed_data["students"][0]
        with pytest.raises(InvalidScoreRangeError):
            score_service.create_change_request(
                {
                    "assignment_id": seed_data["assignment"].id,
                    "reason": "Xin sửa điểm.",
                    "changes": [
                        {"student_id": st.id, "score_column": "score_15m_1", "new_value": 15.0}
                    ],
                },
                seed_data["teacher"].id,
            )

    def test_rejects_same_value(self, app, seed_data):

        from studentapp.exceptions import ValidationError

        _seed_locked_scores(seed_data)
        st = seed_data["students"][0]
        with pytest.raises(ValidationError):
            score_service.create_change_request(
                {
                    "assignment_id": seed_data["assignment"].id,
                    "reason": "Xin sửa điểm.",
                    "changes": [
                        {"student_id": st.id, "score_column": "score_15m_1", "new_value": 7.0}
                    ],
                },
                seed_data["teacher"].id,
            )

    def test_rejects_duplicate_cell(self, app, seed_data):

        from studentapp.exceptions import ValidationError

        _seed_locked_scores(seed_data)
        st = seed_data["students"][0]
        with pytest.raises(ValidationError):
            score_service.create_change_request(
                {
                    "assignment_id": seed_data["assignment"].id,
                    "reason": "Xin sửa điểm.",
                    "changes": [
                        {"student_id": st.id, "score_column": "score_15m_1", "new_value": 9.0},
                        {"student_id": st.id, "score_column": "score_15m_1", "new_value": 8.5},
                    ],
                },
                seed_data["teacher"].id,
            )

class TestChangeRequestAuthorization:

    def test_forbidden_for_other_teacher(self, app, seed_data):

        from studentapp.exceptions import PermissionDeniedError

        _seed_locked_scores(seed_data)
        st = seed_data["students"][0]
        with pytest.raises(PermissionDeniedError):
            score_service.create_change_request(
                {
                    "assignment_id": seed_data["assignment"].id,
                    "reason": "Xin sửa điểm.",
                    "changes": [
                        {"student_id": st.id, "score_column": "score_15m_1", "new_value": 9.0}
                    ],
                },
                seed_data["other_teacher"].id,
            )

class TestChangeRequestEndpoints:

    def test_create_endpoint(self, app, client, seed_data, auth_headers):
        _seed_locked_scores(seed_data)
        st = seed_data["students"][0]
        resp = client.post(
            "/api/v1/score-requests",
            json={
                "assignment_id": seed_data["assignment"].id,
                "reason": "Học sinh bị chấm nhầm điểm.",
                "changes": [
                    {"student_id": st.id, "score_column": "score_15m_1", "new_value": 9.0}
                ],
            },
            headers=auth_headers("TEACHER", seed_data["teacher"].id),
        )
        assert resp.status_code == 201
        body = resp.get_json()
        assert body["data"]["status"] == "PENDING"
        assert body["data"]["details"][0]["old_value"] == 7.0

    def test_create_endpoint_not_locked_returns_422(self, app, client, seed_data, auth_headers):
        st = seed_data["students"][0]
        score_service.save_batch_scores(
            {"assignment_id": seed_data["assignment"].id,
             "scores": [{"student_id": st.id, "score_15m_1": 8.0}]},
            seed_data["teacher"].id,
        )
        resp = client.post(
            "/api/v1/score-requests",
            json={
                "assignment_id": seed_data["assignment"].id,
                "reason": "Xin sửa điểm.",
                "changes": [
                    {"student_id": st.id, "score_column": "score_15m_1", "new_value": 9.0}
                ],
            },
            headers=auth_headers("TEACHER", seed_data["teacher"].id),
        )
        assert resp.status_code == 422
        assert resp.get_json()["error"] == "SCORE_TABLE_NOT_LOCKED"

    def test_my_requests_endpoint(self, app, client, seed_data, auth_headers):
        _seed_locked_scores(seed_data)
        st = seed_data["students"][0]
        score_service.create_change_request(
            {
                "assignment_id": seed_data["assignment"].id,
                "reason": "Xin sửa điểm.",
                "changes": [
                    {"student_id": st.id, "score_column": "score_15m_1", "new_value": 9.0}
                ],
            },
            seed_data["teacher"].id,
        )
        resp = client.get(
            "/api/v1/score-requests/my",
            headers=auth_headers("TEACHER", seed_data["teacher"].id),
        )
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert len(data) == 1
        assert len(data[0]["details"]) == 1

class TestChangeRequestAttachment:

    def test_saves_attachment_to_request(self, app, seed_data):

        _seed_locked_scores(seed_data)
        st = seed_data["students"][0]
        result = score_service.create_change_request(
            {
                "assignment_id": seed_data["assignment"].id,
                "reason": "Xin sửa điểm kèm biên bản.",
                "changes": [
                    {"student_id": st.id, "score_column": "score_15m_1", "new_value": 9.0}
                ],
                "attachment_path": "score_requests/2026/11/bai_thi.png",
                "attachment_type": "IMAGE",
                "attachment_name": "bai_thi.png",
            },
            seed_data["teacher"].id,
        )
        assert result["attachment_path"] == "score_requests/2026/11/bai_thi.png"
        assert result["attachment_type"] == "IMAGE"
        assert result["attachment_name"] == "bai_thi.png"

        row = ScoreChangeRequest.query.one()
        assert row.attachment_path == "score_requests/2026/11/bai_thi.png"
        assert row.attachment_type == "IMAGE"

    def test_attachment_is_optional(self, app, seed_data):

        _seed_locked_scores(seed_data)
        st = seed_data["students"][0]
        result = score_service.create_change_request(
            {
                "assignment_id": seed_data["assignment"].id,
                "reason": "Gõ nhầm số.",
                "changes": [
                    {"student_id": st.id, "score_column": "score_15m_1", "new_value": 9.0}
                ],
            },
            seed_data["teacher"].id,
        )
        assert result["attachment_path"] is None
        assert result["attachment_type"] is None

    def test_rejects_path_traversal(self, app, seed_data):

        from studentapp.exceptions import ValidationError

        _seed_locked_scores(seed_data)
        st = seed_data["students"][0]
        with pytest.raises(ValidationError):
            score_service.create_change_request(
                {
                    "assignment_id": seed_data["assignment"].id,
                    "reason": "Xin sửa điểm.",
                    "changes": [
                        {"student_id": st.id, "score_column": "score_15m_1", "new_value": 9.0}
                    ],
                    "attachment_path": "../../etc/passwd",
                    "attachment_type": "IMAGE",
                },
                seed_data["teacher"].id,
            )

    def test_rejects_invalid_attachment_type(self, app, seed_data):

        from studentapp.exceptions import ValidationError

        _seed_locked_scores(seed_data)
        st = seed_data["students"][0]
        with pytest.raises(ValidationError):
            score_service.create_change_request(
                {
                    "assignment_id": seed_data["assignment"].id,
                    "reason": "Xin sửa điểm.",
                    "changes": [
                        {"student_id": st.id, "score_column": "score_15m_1", "new_value": 9.0}
                    ],
                    "attachment_path": "score_requests/2026/11/a.zip",
                    "attachment_type": "ZIP",
                },
                seed_data["teacher"].id,
            )

class TestDuplicatePendingAppeal:

    def test_rejects_duplicate_pending_cell(self, app, seed_data):

        from studentapp.exceptions import DuplicatePendingAppealError

        _seed_locked_scores(seed_data)
        st = seed_data["students"][0]
        payload = {
            "assignment_id": seed_data["assignment"].id,
            "reason": "Xin sửa điểm.",
            "changes": [
                {"student_id": st.id, "score_column": "score_15m_1", "new_value": 9.0}
            ],
        }
        score_service.create_change_request(payload, seed_data["teacher"].id)

        with pytest.raises(DuplicatePendingAppealError) as exc:
            score_service.create_change_request(
                {
                    **payload,
                    "changes": [
                        {"student_id": st.id, "score_column": "score_15m_1", "new_value": 9.5}
                    ],
                },
                seed_data["teacher"].id,
            )
        assert exc.value.cells == [
            {"student_id": st.id, "score_column": "score_15m_1"}
        ]

    def test_allows_different_cell(self, app, seed_data):

        _seed_locked_scores(seed_data)
        s1, s2 = seed_data["students"][0], seed_data["students"][1]
        score_service.create_change_request(
            {
                "assignment_id": seed_data["assignment"].id,
                "reason": "Xin sửa điểm.",
                "changes": [
                    {"student_id": s1.id, "score_column": "score_15m_1", "new_value": 9.0}
                ],
            },
            seed_data["teacher"].id,
        )
        result = score_service.create_change_request(
            {
                "assignment_id": seed_data["assignment"].id,
                "reason": "Xin sửa điểm ô khác.",
                "changes": [
                    {"student_id": s2.id, "score_column": "score_15m_1", "new_value": 9.0}
                ],
            },
            seed_data["teacher"].id,
        )
        assert result["status"] == "PENDING"
        assert ScoreChangeRequest.query.count() == 2

    def test_endpoint_returns_409_with_cells(self, app, client, seed_data, auth_headers):

        _seed_locked_scores(seed_data)
        st = seed_data["students"][0]
        body = {
            "assignment_id": seed_data["assignment"].id,
            "reason": "Xin sửa điểm.",
            "changes": [
                {"student_id": st.id, "score_column": "score_15m_1", "new_value": 9.0}
            ],
        }
        headers = auth_headers("TEACHER", seed_data["teacher"].id)
        assert client.post("/api/v1/score-requests", json=body, headers=headers).status_code == 201

        body["changes"][0]["new_value"] = 9.5
        resp = client.post("/api/v1/score-requests", json=body, headers=headers)
        assert resp.status_code == 409
        payload = resp.get_json()
        assert payload["error"] == "DUPLICATE_PENDING_APPEAL"
        assert payload["cells"][0]["score_column"] == "score_15m_1"
