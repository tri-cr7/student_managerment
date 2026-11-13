"""Sinh file Postman collection cho module GIÁO VIÊN (điểm số).

Chạy: ``./venv/bin/python build_teacher_collection.py``
Output: ``postman_teacher_collection.json``
"""
import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT = os.path.join(BASE_DIR, "postman_teacher_collection.json")

SCHEMA = "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"

VARIABLES = [
    {"key": "baseUrl", "value": "http://localhost:5001/api/v1"},
    {"key": "token", "value": ""},
    {"key": "teacherToken", "value": ""},
    {"key": "otherTeacherToken", "value": ""},
    {"key": "teacherId", "value": "41"},
    {"key": "otherTeacherId", "value": "42"},
    {"key": "classId", "value": "1"},
    {"key": "subjectId", "value": "1"},
    {"key": "studentId", "value": "1"},
    {"key": "assignmentId", "value": "1"},
    {"key": "scoreId", "value": ""},
    {"key": "submissionId", "value": ""},
    {"key": "requestId", "value": ""},
]


def bearer(token_var="token"):
    return {
        "type": "bearer",
        "bearer": [{"key": "token", "value": "{{%s}}" % token_var, "type": "string"}],
    }


def url(path, raw=None):
    raw = raw or "{{baseUrl}}/" + path.lstrip("/")
    parts = [p for p in path.strip("/").split("/") if p]
    return {"raw": raw, "host": ["{{baseUrl}}"], "path": parts}


def json_body(payload):
    return {
        "mode": "raw",
        "options": {"raw": {"language": "json"}},
        "raw": json.dumps(payload, ensure_ascii=False, indent=2),
    }


def item(name, method, path, description, body=None, token="token", tests=None, raw_url=None):
    req = {
        "method": method,
        "header": [{"key": "Content-Type", "value": "application/json"}],
        "url": url(path, raw_url),
        "description": description,
    }
    if token:
        req["auth"] = bearer(token)
    if body is not None:
        req["body"] = json_body(body)
    entry = {"name": name, "request": req}
    if tests:
        entry["event"] = [
            {"listen": "test", "script": {"type": "text/javascript", "exec": tests}}
        ]
    return entry


def folder(name, description, items):
    return {"name": name, "description": description, "item": items}


# --------------------------------------------------------------------------- #
# 00 — Chuẩn bị: đăng nhập lấy token
# --------------------------------------------------------------------------- #
LOGIN_TEACHER_TESTS = [
    "pm.test('Status 200', () => pm.response.to.have.status(200));",
    "const b = pm.response.json();",
    "pm.test('Có access token', () => pm.expect(b.data.token).to.be.a('string'));",
    "if (b && b.data && b.data.token) pm.collectionVariables.set('teacherToken', b.data.token);",
    "if (b && b.data && b.data.user && b.data.user.id) pm.collectionVariables.set('teacherId', b.data.user.id);",
]

LOGIN_OTHER_TESTS = [
    "pm.test('Status 200', () => pm.response.to.have.status(200));",
    "const b = pm.response.json();",
    "if (b && b.data && b.data.token) pm.collectionVariables.set('otherTeacherToken', b.data.token);",
    "if (b && b.data && b.data.user && b.data.user.id) pm.collectionVariables.set('otherTeacherId', b.data.user.id);",
]

FOLDER_00 = folder(
    "00-Chuan-bi (Dang nhap lay token)",
    "BẮT BUỘC chạy trước các request khác.\n"
    "Tài khoản seed:\n"
    "  - GV giao viên   : gv01 / Gv@123456\n"
    "  - GV khác        : gv02 / Gv@123456\n"
    "  - Giao vu (Admin): giaovu / Admin@123\n\n"
    "Nếu chưa có dữ liệu mẫu, chạy trước trong terminal:\n"
    "  ./venv/bin/python seed_teacher_demo.py",
    [
        item(
            "00a-Health (server song?)",
            "GET",
            "health",
            "MỤC ĐÍCH: kiểm tra server đang chạy (port 5001).\nKẾT QUẢ ĐÚNG: 200, data.db = 'up'.",
            token=None,
            tests=[
                "pm.test('Status 200', () => pm.response.to.have.status(200));",
                "pm.test('DB up', () => pm.expect(pm.response.json().data.db).to.eql('up'));",
            ],
        ),
        item(
            "00b-Login-GV01 (token giao vien)",
            "POST",
            "auth/login",
            "MỤC ĐÍCH: đăng nhập Giáo viên gv01, lấy token lưu vào {{teacherToken}}.\n"
            "KẾT QUẢ ĐÚNG: 200, có data.token + data.user.id.",
            body={"username": "gv01", "password": "Gv@123456"},
            token=None,
            tests=LOGIN_TEACHER_TESTS,
        ),
        item(
            "00c-Login-GV02 (token GV khac - de test 403)",
            "POST",
            "auth/login",
            "MỤC ĐÍCH: đăng nhập GV thứ 2 (gv02) để kiểm tra quyền sở hữu.\n"
            "KẾT QUẢ ĐÚNG: 200, token lưu vào {{otherTeacherToken}}.",
            body={"username": "gv02", "password": "Gv@123456"},
            token=None,
            tests=LOGIN_OTHER_TESTS,
        ),
        item(
            "00d-Login-GiaoVu (token de duyet)",
            "POST",
            "auth/login",
            "MỤC ĐÍCH: đăng nhập Giáo vụ (giaovu) để dùng cho luồng duyệt/chốt bảng điểm.\n"
            "KẾT QUẢ ĐÚNG: 200, có token.",
            body={"username": "giaovu", "password": "Admin@123"},
            token=None,
            tests=[
                "pm.test('Status 200', () => pm.response.to.have.status(200));",
                "const b = pm.response.json();",
                "if (b && b.data && b.data.token) pm.collectionVariables.set('token', b.data.token);",
            ],
        ),
    ],
)

# --------------------------------------------------------------------------- #
# 01 — SD09: danh sách lớp phụ trách
# --------------------------------------------------------------------------- #
FOLDER_01 = folder(
    "01-SD09-Danh-sach-lop-phu-trach",
    "SD09 — Giáo viên xem các lớp môn học mình được phụ trách.\n"
    "GET /assignments/my → trả về danh sách kèm class_name, subject_name, semester_name,\n"
    "academic_year_name, is_locked, has_pending_submission.",
    [
        item(
            "01a-Lop-phu-trach (co token)",
            "GET",
            "assignments/my",
            "MỤC ĐÍCH: lấy danh sách lớp phụ trách (SD09).\n"
            "KẾT QUẢ ĐÚNG: 200, data là mảng, mỗi phần tử có class_name + subject_name.",
            token="teacherToken",
            tests=[
                "pm.test('Status 200', () => pm.response.to.have.status(200));",
                "const b = pm.response.json();",
                "pm.test('data là mảng', () => pm.expect(b.data).to.be.an('array'));",
                "pm.test('Có class_name + subject_name', () => {",
                "  pm.expect(b.data[0].class_name).to.be.a('string');",
                "  pm.expect(b.data[0].subject_name).to.be.a('string');",
                "});",
                "if (b.data && b.data[0] && b.data[0].id) pm.collectionVariables.set('assignmentId', b.data[0].id);",
            ],
        ),
        item(
            "01b-Khong token (PHAI 401)",
            "GET",
            "assignments/my",
            "MỤC ĐÍCH: kiểm tra chưa đăng nhập bị chặn.\n"
            "KẾT QUẢ ĐÚNG: 401 UNAUTHORIZED.",
            token=None,
            tests=[
                "pm.test('Status 401', () => pm.response.to.have.status(401));",
                "pm.test('error = UNAUTHORIZED', () => pm.expect(pm.response.json().error).to.eql('UNAUTHORIZED'));",
            ],
        ),
    ],
)

# --------------------------------------------------------------------------- #
# 02 — SD11: nhập điểm (bảng điểm TẠM)
# --------------------------------------------------------------------------- #
BATCH_FULL = {
    "assignment_id": "{{assignmentId}}",
    "scores": [
        {
            "student_id": 1,
            "score_15m_1": 8.0,
            "score_15m_2": 9.0,
            "score_15m_3": 7.5,
            "score_15m_4": 8.5,
            "score_15m_5": 9.0,
            "score_45m_1": 7.0,
            "score_45m_2": 8.0,
            "score_45m_3": 7.5,
            "score_final": 8.5,
        },
        {
            "student_id": 2,
            "score_15m_1": 6.0,
            "score_15m_2": 7.0,
            "score_15m_3": 6.5,
            "score_15m_4": 7.0,
            "score_15m_5": 7.5,
            "score_45m_1": 6.0,
            "score_45m_2": 6.5,
            "score_45m_3": 6.0,
            "score_final": 7.0,
        },
        {
            "student_id": 3,
            "score_15m_1": 9.0,
            "score_15m_2": 9.5,
            "score_15m_3": 9.0,
            "score_15m_4": 8.5,
            "score_15m_5": 9.0,
            "score_45m_1": 8.5,
            "score_45m_2": 9.0,
            "score_45m_3": 8.5,
            "score_final": 9.0,
        },
        {
            "student_id": 4,
            "score_15m_1": 7.0,
            "score_15m_2": 7.5,
            "score_15m_3": 7.0,
            "score_15m_4": 7.5,
            "score_15m_5": 8.0,
            "score_45m_1": 6.5,
            "score_45m_2": 7.0,
            "score_45m_3": 6.5,
            "score_final": 7.5,
        },
        {
            "student_id": 5,
            "score_15m_1": 5.0,
            "score_15m_2": 6.0,
            "score_15m_3": 5.5,
            "score_15m_4": 6.0,
            "score_15m_5": 6.5,
            "score_45m_1": 5.0,
            "score_45m_2": 5.5,
            "score_45m_3": 5.0,
            "score_final": 6.0,
        },
    ],
}

FOLDER_02 = folder(
    "02-SD11-Nhap-diem (bang diem TAM)",
    "SD11 — Giáo viên nhập điểm cho cả lớp. Điểm được lưu vào BẢNG ĐIỂM TẠM (is_draft = true).\n"
    "ĐTB tự tính: (15'×1 + 1tiết×2 + thi×3) / (số ô CÓ GIÁ TRỊ tương ứng).\n"
    "Ô NULL (chưa nhập) bị loại khỏi cả tử số và mẫu số; ô 0.00 vẫn được tính.",
    [
        item(
            "02a-Nhap-diem-day-du (5 HS x 9 cot)",
            "POST",
            "scores/batch",
            "MỤC ĐÍCH: nhập đủ điểm cho 5 học sinh → lưu bảng điểm TẠM.\n"
            "KẾT QUẢ ĐÚNG: 200, data.updated_count = 5, data.is_draft = true,\n"
            "mỗi học sinh có average_score & is_passed.",
            body=BATCH_FULL,
            token="teacherToken",
            tests=[
                "pm.test('Status 200', () => pm.response.to.have.status(200));",
                "const b = pm.response.json();",
                "pm.test('updated_count = 5', () => pm.expect(b.data.updated_count).to.eql(5));",
                "pm.test('is_draft = true', () => pm.expect(b.data.is_draft).to.be.true);",
                "pm.test('Có average_score cho từng HS', () => {",
                "  b.data.scores.forEach(s => pm.expect(s).to.have.property('average_score'));",
                "});",
            ],
        ),
        item(
            "02b-Update 1 o diem (partial update - null giu nguyen)",
            "POST",
            "scores/batch",
            "MỤC ĐÍCH: cập nhật chỉ 1 ô của HS id=1, các ô khác gửi null.\n"
            "KẾT QUẢ ĐÚNG: 200. Sau đó gọi 02e để thấy score_15m_2 VẪN = 9.0 (null KHÔNG xoá dữ liệu).",
            body={
                "assignment_id": "{{assignmentId}}",
                "scores": [
                    {
                        "student_id": 1,
                        "score_15m_1": 6.0,
                        "score_15m_2": None,
                        "score_15m_3": None,
                        "score_15m_4": None,
                        "score_15m_5": None,
                        "score_45m_1": None,
                        "score_45m_2": None,
                        "score_45m_3": None,
                        "score_final": None,
                    }
                ],
            },
            token="teacherToken",
            tests=[
                "pm.test('Status 200', () => pm.response.to.have.status(200));",
                "const b = pm.response.json();",
                "pm.test('updated_count = 1', () => pm.expect(b.data.updated_count).to.eql(1));",
            ],
        ),
        item(
            "02c-Diem ngoai khoang (PHAI 422)",
            "POST",
            "scores/batch",
            "MỤC ĐÍCH: kiểm tra validation điểm nằm ngoài [0, 10] (rule A1).\n"
            "KẾT QUẢ ĐÚNG: 422 INVALID_SCORE_RANGE.",
            body={
                "assignment_id": "{{assignmentId}}",
                "scores": [{"student_id": 1, "score_15m_1": 99.0}],
            },
            token="teacherToken",
            tests=[
                "pm.test('Status 422', () => pm.response.to.have.status(422));",
                "pm.test('error = INVALID_SCORE_RANGE', () => pm.expect(pm.response.json().error).to.eql('INVALID_SCORE_RANGE'));",
            ],
        ),
        item(
            "02d-GV khac sua lop nguoi ta (PHAI 403)",
            "POST",
            "scores/batch",
            "MỤC ĐÍCH: kiểm tra quyền sở hữu — GV2 không được ghi điểm lớp của GV1 (rule A11).\n"
            "KẾT QUẢ ĐÚNG: 403 FORBIDDEN.",
            body={
                "assignment_id": "{{assignmentId}}",
                "scores": [{"student_id": 1, "score_15m_1": 5.0}],
            },
            token="otherTeacherToken",
            tests=[
                "pm.test('Status 403', () => pm.response.to.have.status(403));",
                "pm.test('error = FORBIDDEN', () => pm.expect(pm.response.json().error).to.eql('FORBIDDEN'));",
            ],
        ),
        item(
            "02e-Xem bang diem (kiem tra partial update)",
            "GET",
            "scores/assignment/{{assignmentId}}",
            "MỤC ĐÍCH: xem bảng điểm để KIỂM CHỨNG partial update.\n"
            "Sau khi chạy 02b: HS id=1 có score_15m_1 = 6.0 NHƯNG score_15m_2 vẫn = 9.0 (null giữ nguyên).",
            token="teacherToken",
            tests=[
                "pm.test('Status 200', () => pm.response.to.have.status(200));",
                "const b = pm.response.json();",
                "pm.test('score_list không rỗng', () => pm.expect(b.data.score_list).to.have.length.above(0));",
            ],
        ),
    ],
)

# --------------------------------------------------------------------------- #
# 03 — SD14: sửa 1 ô điểm
# --------------------------------------------------------------------------- #
FOLDER_03 = folder(
    "03-SD14-Sua-1-o-diem",
    "SD14 — Sửa một ô điểm khi bảng điểm đang MỞ.\n"
    "Khác với batch: có thể XOÁ có chủ đích bằng cờ clear = true (set NULL).\n"
    "Mọi thao tác sửa điểm đều ghi audit log (old_value / new_value).",
    [
        item(
            "03a-Lay score_id (tu 02e hoac tu DB)",
            "GET",
            "scores/assignment/{{assignmentId}}",
            "MỤC ĐÍCH: lấy score.id của học sinh để dùng cho 03b-03d.\n"
            "KẾT QUẢ ĐÚNG: 200, data.score_list[0].id được lưu vào {{scoreId}}.",
            token="teacherToken",
            tests=[
                "pm.test('Status 200', () => pm.response.to.have.status(200));",
                "const b = pm.response.json();",
                "pm.test('Có score_list', () => pm.expect(b.data.score_list).to.be.an('array'));",
                "if (b.data.score_list && b.data.score_list[0]) pm.collectionVariables.set('scoreId', b.data.score_list[0].id);",
            ],
        ),
        item(
            "03b-Sua o diem (score_15m_1 = 7.5)",
            "PUT",
            "scores/{{scoreId}}",
            "MỤC ĐÍCH: sửa 1 ô điểm.\n"
            "KẾT QUẢ ĐÚNG: 200, data.old_value (giá trị cũ) + data.new_value = 7.5,\n"
            "data.average_score được tính lại.",
            body={"score_column": "score_15m_1", "new_value": 7.5},
            token="teacherToken",
            tests=[
                "pm.test('Status 200', () => pm.response.to.have.status(200));",
                "const b = pm.response.json();",
                "pm.test('new_value = 7.5', () => pm.expect(b.data.new_value).to.eql(7.5));",
                "pm.test('có old_value', () => pm.expect(b.data).to.have.property('old_value'));",
                "pm.test('average_score được tính lại', () => pm.expect(b.data.average_score).to.be.a('number'));",
            ],
        ),
        item(
            "03c-Cot khong hop le (PHAI 422)",
            "PUT",
            "scores/{{scoreId}}",
            "MỤC ĐÍCH: kiểm tra whitelist 9 cột điểm (rule A2).\n"
            "KẾT QUẢ ĐÚNG: 422 INVALID_COLUMN_NAME.",
            body={"score_column": "score_hack", "new_value": 8.0},
            token="teacherToken",
            tests=[
                "pm.test('Status 422', () => pm.response.to.have.status(422));",
                "pm.test('error = INVALID_COLUMN_NAME', () => pm.expect(pm.response.json().error).to.eql('INVALID_COLUMN_NAME'));",
            ],
        ),
        item(
            "03d-Xoa co chu dich (clear = true)",
            "PUT",
            "scores/{{scoreId}}",
            "MỤC ĐÍCH: xoá 1 ô điểm đã chấm (set NULL) bằng cờ clear.\n"
            "KẾT QUẢ ĐÚNG: 200, data.new_value = null. Ô đã xoá KHÔNG còn tính vào ĐTB.",
            body={"score_column": "score_15m_2", "clear": True},
            token="teacherToken",
            tests=[
                "pm.test('Status 200', () => pm.response.to.have.status(200));",
                "const b = pm.response.json();",
                "pm.test('new_value = null', () => pm.expect(b.data.new_value).to.be.null);",
            ],
        ),
        item(
            "03e-GV khac sua (PHAI 403)",
            "PUT",
            "scores/{{scoreId}}",
            "MỤC ĐÍCH: kiểm tra quyền sở hữu khi sửa 1 ô (rule A11).\n"
            "KẾT QUẢ ĐÚNG: 403 FORBIDDEN.",
            body={"score_column": "score_15m_1", "new_value": 5.0},
            token="otherTeacherToken",
            tests=[
                "pm.test('Status 403', () => pm.response.to.have.status(403));",
            ],
        ),
    ],
)

# --------------------------------------------------------------------------- #
# 04 — Đọc điểm
# --------------------------------------------------------------------------- #
FOLDER_04 = folder(
    "04-Doc-diem",
    "Xem bảng điểm lớp và điểm của từng học sinh.\n"
    "Mặc định API học sinh CHỈ trả điểm CHÍNH THỨC (đã duyệt) — thêm ?include_draft=true để xem cả nháp.",
    [
        item(
            "04a-Bang diem cua lop",
            "GET",
            "scores/assignment/{{assignmentId}}",
            "MỤC ĐÍCH: xem bảng điểm của lớp môn học.\n"
            "KẾT QUẢ ĐÚNG: 200, data.score_list[] có 9 cột điểm + average_score + is_draft.",
            token="teacherToken",
            tests=[
                "pm.test('Status 200', () => pm.response.to.have.status(200));",
                "const b = pm.response.json();",
                "pm.test('có class_name', () => pm.expect(b.data.class_name).to.be.a('string'));",
                "pm.test('mỗi HS có 9 cột điểm', () => {",
                "  const s = b.data.score_list[0];",
                "  ['score_15m_1','score_15m_2','score_15m_3','score_15m_4','score_15m_5',",
                "   'score_45m_1','score_45m_2','score_45m_3','score_final'].forEach(c =>",
                "    pm.expect(s).to.have.property(c));",
                "});",
            ],
        ),
        item(
            "04b-Diem cua 1 hoc sinh (chi diem chinh thuc)",
            "GET",
            "scores/student/{{studentId}}",
            "MỤC ĐÍCH: xem điểm của 1 học sinh (chỉ điểm đã duyệt).\n"
            "KẾT QUẢ ĐÚNG: 200, data.scores[] chỉ gồm bản ghi is_draft = false.",
            token="teacherToken",
            tests=[
                "pm.test('Status 200', () => pm.response.to.have.status(200));",
                "const b = pm.response.json();",
                "pm.test('có student_code', () => pm.expect(b.data.student_code).to.be.a('string'));",
            ],
        ),
        item(
            "04c-Diem hoc sinh kem diem tam (include_draft)",
            "GET",
            "scores/student/{{studentId}}",
            "MỤC ĐÍCH: xem cả điểm tạm (chưa duyệt) bằng query param.\n"
            "KẾT QUẢ ĐÚNG: 200, data.scores[] có cả bản ghi is_draft = true.",
            token="teacherToken",
            raw_url="{{baseUrl}}/scores/student/{{studentId}}?include_draft=true",
            tests=[
                "pm.test('Status 200', () => pm.response.to.have.status(200));",
                "const b = pm.response.json();",
                "pm.test('có bản ghi nháp', () => pm.expect(b.data.scores.some(s => s.is_draft === true)).to.be.true);",
            ],
        ),
    ],
)

# --------------------------------------------------------------------------- #
# 05 — SD23: gửi duyệt & hủy đơn
# --------------------------------------------------------------------------- #
FOLDER_05 = folder(
    "05-SD23-Gui-duyet-va-huy-don",
    "SD23 — Vòng đời đơn gửi bảng điểm:\n"
    "  Gửi duyệt → PENDING (GV KHÔNG sửa được nữa, HTTP 423 khi thử sửa)\n"
    "  Hủy đơn  → CANCELLED (GV sửa lại được, bảng điểm VẪN LÀ TẠM)\n"
    "  Đã duyệt/từ chối → KHÔNG hủy được (HTTP 409 INVALID_SUBMISSION_STATUS)\n\n"
    "THỨ TỰ TEST: 05a → 05b → 05c → 05d → 05e.",
    [
        item(
            "05a-Gui bang diem len duyet",
            "POST",
            "score-submissions",
            "MỤC ĐÍCH: gửi bảng điểm tạm lên Giáo vụ (SD23).\n"
            "ĐIỀU KIỆN: phải nhập ĐỦ điểm cho mọi HS (rule B1) — nếu không sẽ 422 INCOMPLETE_SCORES.\n"
            "KẾT QUẢ ĐÚNG: 201, data.status = PENDING, total_students = 5, total_scores = 45.",
            body={"assignment_id": "{{assignmentId}}", "note": "Gửi duyệt học kỳ 1"},
            token="teacherToken",
            tests=[
                "pm.test('Status 201', () => pm.response.to.have.status(201));",
                "const b = pm.response.json();",
                "pm.test('status = PENDING', () => pm.expect(b.data.status).to.eql('PENDING'));",
                "if (b.data && b.data.submission_id) pm.collectionVariables.set('submissionId', b.data.submission_id);",
            ],
        ),
        item(
            "05b-Tho sua diem khi dang PENDING (PHAI 423)",
            "POST",
            "scores/batch",
            "MỤC ĐÍCH: kiểm tra rule A10 — đang gửi duyệt thì GV không sửa được điểm.\n"
            "KẾT QUẢ ĐÚNG: 423 SCORE_SUBMISSION_PENDING.",
            body={
                "assignment_id": "{{assignmentId}}",
                "scores": [{"student_id": 1, "score_15m_1": 5.0}],
            },
            token="teacherToken",
            tests=[
                "pm.test('Status 423', () => pm.response.to.have.status(423));",
                "pm.test('error = SCORE_SUBMISSION_PENDING', () => pm.expect(pm.response.json().error).to.eql('SCORE_SUBMISSION_PENDING'));",
            ],
        ),
        item(
            "05c-Huy don de sua lai",
            "PUT",
            "score-submissions/{{submissionId}}/cancel",
            "MỤC ĐÍCH: hủy đơn PENDING để sửa lại bảng điểm tạm (SD23).\n"
            "KẾT QUẢ ĐÚNG: 200, data.status = CANCELLED, data.cancel_note ghi lại lý do.",
            body={"cancel_note": "Nhập nhầm điểm học sinh số 1, xin hủy để sửa lại"},
            token="teacherToken",
            tests=[
                "pm.test('Status 200', () => pm.response.to.have.status(200));",
                "const b = pm.response.json();",
                "pm.test('status = CANCELLED', () => pm.expect(b.data.status).to.eql('CANCELLED'));",
                "pm.test('có cancelled_at', () => pm.expect(b.data.cancelled_at).to.be.a('string'));",
            ],
        ),
        item(
            "05d-Sua lai duoc sau khi huy don",
            "POST",
            "scores/batch",
            "MỤC ĐÍCH: sau khi hủy đơn, GV sửa lại bảng điểm tạm được.\n"
            "KẾT QUẢ ĐÚNG: 200 (không còn 423).",
            body={
                "assignment_id": "{{assignmentId}}",
                "scores": [{"student_id": 1, "score_15m_1": 5.0}],
            },
            token="teacherToken",
            tests=[
                "pm.test('Status 200', () => pm.response.to.have.status(200));",
            ],
        ),
        item(
            "05e-Danh sach don da gui",
            "GET",
            "score-submissions/my",
            "MỤC ĐÍCH: xem lịch sử các đơn đã gửi (kể cả đã hủy).\n"
            "KẾT QUẢ ĐÚNG: 200, data là mảng các đơn có status PENDING/CANCELLED/…",
            token="teacherToken",
            tests=[
                "pm.test('Status 200', () => pm.response.to.have.status(200));",
                "const b = pm.response.json();",
                "pm.test('data là mảng', () => pm.expect(b.data).to.be.an('array'));",
            ],
        ),
        item(
            "05f-Gui trung khi da co don PENDING (PHAI 409)",
            "POST",
            "score-submissions",
            "MỤC ĐÍCH: kiểm tra rule B3 — không gửi trùng đơn PENDING.\n"
            "KẾT QUẢ ĐÚNG: 409 DUPLICATE_PENDING_SUBMISSION.",
            body={"assignment_id": "{{assignmentId}}"},
            token="teacherToken",
            tests=[
                "pm.test('Status 409', () => pm.response.to.have.status(409));",
                "pm.test('error = DUPLICATE_PENDING_SUBMISSION', () => pm.expect(pm.response.json().error).to.eql('DUPLICATE_PENDING_SUBMISSION'));",
            ],
        ),
    ],
)

# --------------------------------------------------------------------------- #
# 06 — SD25: đơn phúc khảo (sau khi bảng điểm đã chốt)
# --------------------------------------------------------------------------- #
FOLDER_06 = folder(
    "06-SD25-Don-phuc-khao (sau khi CHOT)",
    "SD25 — Khi bảng điểm đã CHỐT (is_locked = true), GV không sửa trực tiếp được.\n"
    "Muốn sửa ⇒ gửi ĐƠN PHÚC KHẢO có cấu trúc: mỗi ô cần sửa ghi rõ cột + giá trị cũ + giá trị mới.\n"
    "old_value BẮT BUỘC có giá trị (bảng đã chốt thì không có ô NULL).\n\n"
    "CHUẨN BỊ: dùng script để mô phỏng Giáo vụ chốt bảng điểm:\n"
    "  ./venv/bin/python lock_assignment_demo.py {{assignmentId}}\n"
    "Sau đó chạy: 06a → 06b → 06c.",
    [
        item(
            "06a-Tao don phuc khao (1 o diem)",
            "POST",
            "score-requests",
            "MỤC ĐÍCH: gửi đơn yêu cầu chỉnh 1 ô điểm (SD25).\n"
            "ĐIỀU KIỆN: bảng điểm phải ĐÃ CHỐT (is_locked = true), nếu không sẽ 422 SCORE_TABLE_NOT_LOCKED.\n"
            "KẾT QUẢ ĐÚNG: 201, data.status = PENDING, data.details[] có old_value + new_value.",
            body={
                "assignment_id": "{{assignmentId}}",
                "reason": "Học sinh bị đánh nhầm điểm kiểm tra 15 phút, đề nghị Giáo vụ xem xét lại.",
                "changes": [
                    {
                        "student_id": 1,
                        "score_column": "score_15m_1",
                        "new_value": 8.0,
                        "note": "Bài làm đúng thực tế đã chấm nhầm 3 điểm.",
                    }
                ],
            },
            token="teacherToken",
            tests=[
                "pm.test('Status 201', () => pm.response.to.have.status(201));",
                "const b = pm.response.json();",
                "pm.test('status = PENDING', () => pm.expect(b.data.status).to.eql('PENDING'));",
                "pm.test('có details', () => pm.expect(b.data.details).to.be.an('array'));",
                "if (b.data && b.data.request_id) pm.collectionVariables.set('requestId', b.data.request_id);",
            ],
        ),
        item(
            "06b-Don phuc khao nhieu HS (dang lo)",
            "POST",
            "score-requests",
            "MỤC ĐÍCH: gửi đơn sửa NHIỀU ô điểm cùng lúc (is_batch = true).\n"
            "KẾT QUẢ ĐÚNG: 201, data.is_batch = true, data.total_changes = số ô.",
            body={
                "assignment_id": "{{assignmentId}}",
                "reason": "Đề nghị xem xét lại điểm kiểm tra giữa kỳ cho nhóm học sinh ngồi sai vị trí.",
                "changes": [
                    {"student_id": 1, "score_column": "score_15m_2", "new_value": 8.5},
                    {"student_id": 2, "score_column": "score_15m_2", "new_value": 7.5},
                    {"student_id": 3, "score_column": "score_final", "new_value": 9.5},
                ],
            },
            token="teacherToken",
            tests=[
                "pm.test('Status 201', () => pm.response.to.have.status(201));",
                "const b = pm.response.json();",
                "pm.test('is_batch = true', () => pm.expect(b.data.is_batch).to.be.true);",
                "pm.test('total_changes = 3', () => pm.expect(b.data.total_changes).to.eql(3));",
            ],
        ),
        item(
            "06c-Danh sach don da gui",
            "GET",
            "score-requests/my",
            "MỤC ĐÍCH: xem các đơn phúc khảo đã gửi.\n"
            "KẾT QUẢ ĐÚNG: 200, data là mảng đơn có details[] chi tiết từng ô.",
            token="teacherToken",
            tests=[
                "pm.test('Status 200', () => pm.response.to.have.status(200));",
                "const b = pm.response.json();",
                "pm.test('data là mảng', () => pm.expect(b.data).to.be.an('array'));",
            ],
        ),
        item(
            "06d-Sua diem truc tiep khi bang da CHOT (PHAI 423)",
            "PUT",
            "scores/{{scoreId}}",
            "MỤC ĐÍCH: kiểm tra rule A8 — bảng đã chốt thì GV không sửa trực tiếp được.\n"
            "KẾT QUẢ ĐÚNG: 423 SCORE_TABLE_LOCKED.",
            body={"score_column": "score_15m_1", "new_value": 9.0},
            token="teacherToken",
            tests=[
                "pm.test('Status 423', () => pm.response.to.have.status(423));",
                "pm.test('error = SCORE_TABLE_LOCKED', () => pm.expect(pm.response.json().error).to.eql('SCORE_TABLE_LOCKED'));",
            ],
        ),
    ],
)

COLLECTION = {
    "info": {
        "name": "StudentApp-Teacher-Score (Module Giao Vien)",
        "schema": SCHEMA,
        "description": (
            "BỘ TEST API MODULE GIÁO VIÊN (điểm số).\n\n"
            "=== CHUẨN BỊ ===\n"
            "1. Seed dữ liệu mẫu (1 lần):\n"
            "   cd studentmanagementapp && ./venv/bin/python seed_teacher_demo.py\n"
            "2. Chạy server:\n"
            "   cd studentmanagementapp && ./venv/bin/python run.py   (port 5001)\n"
            "3. Import file này vào Postman.\n\n"
            "=== TÀI KHOẢN SEED ===\n"
            "  gv01   / Gv@123456   → Giáo viên (phụ trách lớp 10A1)\n"
            "  gv02   / Gv@123456   → Giáo viên khác (test quyền 403)\n"
            "  giaovu / Admin@123    → Giáo vụ (duyệt & chốt bảng điểm)\n\n"
            "=== THỨ TỰ CHẠY ===\n"
            "  00 → 01 → 02 → 03 → 04 → 05 → (lock bảng điểm) → 06\n\n"
            "=== BIẾN TỰ ĐỘNG ===\n"
            "  {{teacherToken}}  token GV (login 00b)\n"
            "  {{otherTeacherToken}} token GV khác (login 00c)\n"
            "  {{assignmentId}}  lớp môn học (tự set từ 01a)\n"
            "  {{scoreId}}       dòng điểm (tự set từ 03a)\n"
            "  {{submissionId}}  đơn gửi duyệt (tự set từ 05a)\n"
            "  {{requestId}}     đơn phúc khảo (tự set từ 06a)\n\n"
            "=== MÃ LỖI NGHIỆP VỤ ===\n"
            "  400 BAD_REQUEST / 403 FORBIDDEN / 404 NOT_FOUND\n"
            "  409 DUPLICATE_PENDING_SUBMISSION / INVALID_SUBMISSION_STATUS\n"
            "  422 INCOMPLETE_SCORES / INVALID_SCORE_RANGE / INVALID_COLUMN_NAME\n"
            "  423 SCORE_TABLE_LOCKED / SCORE_SUBMISSION_PENDING"
        ),
    },
    "variable": VARIABLES,
    "item": [
        FOLDER_00,
        FOLDER_01,
        FOLDER_02,
        FOLDER_03,
        FOLDER_04,
        FOLDER_05,
        FOLDER_06,
    ],
}


def main():
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(COLLECTION, f, ensure_ascii=False, indent=2)
    print(f"OK: da tao {OUTPUT}")

    total = 0
    for f in COLLECTION["item"]:
        count = len(f["item"])
        total += count
        print(f"  - {f['name']}: {count} request")
    print(f"  TONG: {total} request")


if __name__ == "__main__":
    main()
