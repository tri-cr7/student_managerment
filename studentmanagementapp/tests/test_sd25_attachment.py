import io
import os

import pytest

@pytest.fixture
def upload_dir(app, tmp_path):

    app.config["UPLOAD_FOLDER"] = str(tmp_path)
    return tmp_path

def _png_bytes():

    return (
        b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
    )

def _pdf_bytes():
    return b"%PDF-1.4\n%%EOF\n"

class TestSaveAttachment:

    def test_saves_png(self, app, upload_dir):
        from werkzeug.datastructures import FileStorage

        from studentapp.services import attachment_service

        fs = FileStorage(
            stream=io.BytesIO(_png_bytes()),
            filename="bai thi HS.png",
            content_type="image/png",
        )
        result = attachment_service.save_attachment(fs)
        assert result["attachment_type"] == "IMAGE"
        assert result["attachment_name"] == "bai_thi_HS.png"
        assert result["attachment_path"].startswith("score_requests/")
        assert os.path.isfile(
            os.path.join(str(upload_dir), result["attachment_path"])
        )

    def test_saves_pdf(self, app, upload_dir):
        from werkzeug.datastructures import FileStorage

        from studentapp.services import attachment_service

        fs = FileStorage(
            stream=io.BytesIO(_pdf_bytes()),
            filename="bien ban.pdf",
            content_type="application/pdf",
        )
        result = attachment_service.save_attachment(fs)
        assert result["attachment_type"] == "PDF"
        assert result["attachment_path"].endswith(".pdf")

    def test_rejects_executable_type(self, app, upload_dir):
        from werkzeug.datastructures import FileStorage

        from studentapp.exceptions import ValidationError
        from studentapp.services import attachment_service

        fs = FileStorage(
            stream=io.BytesIO(b"MZ..."),
            filename="virus.exe",
            content_type="application/x-msdownload",
        )
        with pytest.raises(ValidationError) as exc:
            attachment_service.save_attachment(fs)
        assert exc.value.error == "INVALID_ATTACHMENT_TYPE"

    def test_rejects_missing_file(self, app, upload_dir):
        from studentapp.exceptions import ValidationError
        from studentapp.services import attachment_service

        with pytest.raises(ValidationError) as exc:
            attachment_service.save_attachment(None)
        assert exc.value.error == "MISSING_FILE"

    def test_rejects_file_over_10mb(self, app, upload_dir):
        from werkzeug.datastructures import FileStorage

        from studentapp.exceptions import ValidationError
        from studentapp.services import attachment_service

        big = b"\x00" * (10 * 1024 * 1024 + 1024)
        fs = FileStorage(
            stream=io.BytesIO(big),
            filename="lon.pdf",
            content_type="application/pdf",
        )
        with pytest.raises(ValidationError) as exc:
            attachment_service.save_attachment(fs)
        assert exc.value.error == "FILE_TOO_LARGE"

    def test_sanitizes_filename(self, app, upload_dir):

        from werkzeug.datastructures import FileStorage

        from studentapp.services import attachment_service

        fs = FileStorage(
            stream=io.BytesIO(_png_bytes()),
            filename="../../etc/passwd;rm -rf.png",
            content_type="image/png",
        )
        result = attachment_service.save_attachment(fs)
        assert ".." not in result["attachment_name"]
        assert "/" not in result["attachment_name"]
        assert ";" not in result["attachment_name"]

    def test_unique_path_per_file(self, app, upload_dir):

        from werkzeug.datastructures import FileStorage

        from studentapp.services import attachment_service

        paths = []
        for _ in range(2):
            fs = FileStorage(
                stream=io.BytesIO(_png_bytes()),
                filename="a.png",
                content_type="image/png",
            )
            paths.append(attachment_service.save_attachment(fs)["attachment_path"])
        assert paths[0] != paths[1]

class TestAttachmentEndpoint:

    def test_requires_authentication(self, app, client, upload_dir):
        resp = client.post(
            "/api/v1/score-requests/attachment",
            data={"file": (io.BytesIO(_png_bytes()), "a.png")},
            content_type="multipart/form-data",
        )
        assert resp.status_code == 401

    def test_forbidden_for_staff(self, app, client, seed_data, upload_dir,
                                auth_headers):
        resp = client.post(
            "/api/v1/score-requests/attachment",
            data={"file": (io.BytesIO(_png_bytes()), "a.png")},
            content_type="multipart/form-data",
            headers=auth_headers("STAFF", seed_data["staff"].id),
        )
        assert resp.status_code == 403

    def test_teacher_uploads_file(self, app, client, seed_data, upload_dir,
                                  auth_headers):
        resp = client.post(
            "/api/v1/score-requests/attachment",
            data={"file": (io.BytesIO(_png_bytes()), "bai thi.png")},
            content_type="multipart/form-data",
            headers=auth_headers("TEACHER", seed_data["teacher"].id),
        )
        assert resp.status_code == 201
        body = resp.get_json()
        assert body["success"] is True
        data = body["data"]
        assert data["attachment_type"] == "IMAGE"
        assert data["attachment_path"]
        assert data["attachment_name"] == "bai_thi.png"

    def test_missing_file_returns_400(self, app, client, seed_data, upload_dir,
                                      auth_headers):
        resp = client.post(
            "/api/v1/score-requests/attachment",
            data={},
            content_type="multipart/form-data",
            headers=auth_headers("TEACHER", seed_data["teacher"].id),
        )
        assert resp.status_code == 400
        assert resp.get_json()["error"] == "MISSING_FILE"

    def test_invalid_type_returns_400(self, app, client, seed_data, upload_dir,
                                      auth_headers):
        resp = client.post(
            "/api/v1/score-requests/attachment",
            data={"file": (io.BytesIO(b"MZ"), "virus.exe")},
            content_type="multipart/form-data",
            headers=auth_headers("TEACHER", seed_data["teacher"].id),
        )
        assert resp.status_code == 400
        assert resp.get_json()["error"] == "INVALID_ATTACHMENT_TYPE"
