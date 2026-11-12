"""SERVICE report — SD20 báo cáo tổng kết môn học (Yêu cầu 4).

Nguyên tắc đọc điểm: chỉ điểm CHÍNH THỨC (WHERE is_draft = FALSE).
Ngưỡng đạt đọc động từ system_rules.PASSING_SCORE.
"""
from studentapp.extensions import db


def _passing_score() -> float:
    from studentapp.repositories import system_rule_repository

    return system_rule_repository.get_float("PASSING_SCORE", 5.0)


def _resolve_scope(subject_id, semester_id):
    from studentapp.models.semester import Semester
    from studentapp.models.subject import Subject

    try:
        sid = int(subject_id)
    except (TypeError, ValueError):
        from studentapp.exceptions import ValidationError
        raise ValidationError("subject_id không hợp lệ.")
    try:
        sem_id = int(semester_id)
    except (TypeError, ValueError):
        from studentapp.exceptions import ValidationError
        raise ValidationError("semester_id không hợp lệ.")
    subject = db.session.get(Subject, sid)
    if subject is None:
        from studentapp.exceptions import NotFoundError
        raise NotFoundError("Không tìm thấy môn học.")
    semester = db.session.get(Semester, sem_id)
    if semester is None:
        from studentapp.exceptions import NotFoundError
        raise NotFoundError("Không tìm thấy học kỳ.")
    return subject, semester


def subject_summary(subject_id, semester_id):
    """Báo cáo tổng kết môn: từng lớp (sĩ số, số đạt, tỷ lệ %)."""
    from studentapp.models.class_room import Class
    from studentapp.models.score import Score
    from studentapp.models.teaching_assignment import TeachingAssignment
    from studentapp.repositories import class_enrollment_repository

    subject, semester = _resolve_scope(subject_id, semester_id)
    passing = _passing_score()
    assignments = TeachingAssignment.query.filter_by(
        subject_id=subject.id, semester_id=semester.id).order_by(
        TeachingAssignment.class_id).all()

    year_name = semester.academic_year.year_name if semester.academic_year else None
    summary = []
    stt = 0
    for a in assignments:
        cls = db.session.get(Class, a.class_id)
        if cls is None:
            continue
        stt += 1
        student_ids = class_enrollment_repository.list_student_ids_by_class(cls.id)
        rows = Score.query.filter_by(
            assignment_id=a.id, is_draft=False).filter(
            Score.student_id.in_(student_ids) if student_ids else False).all() \
            if student_ids else []
        by_student = {r.student_id: r for r in rows}
        passed = 0
        for sid in student_ids:
            r = by_student.get(int(sid))
            if r is None or r.average_score is None:
                continue
            is_pass = bool(r.is_passed) if r.is_passed is not None \
                else float(r.average_score) >= passing
            if is_pass:
                passed += 1
        size = len(student_ids)
        rate = round(passed / size * 100, 2) if size else 0.0
        summary.append({
            "stt": stt, "class_id": cls.id, "class_name": cls.class_name,
            "class_size": size, "passed_count": passed, "pass_rate": rate,
        })
    return {
        "subject_id": subject.id, "subject_name": subject.subject_name,
        "semester_id": semester.id, "semester_name": semester.semester_name,
        "academic_year": year_name, "passing_threshold": passing,
        "summary": summary,
    }


def chart_data(subject_id, semester_id, chart_type="bar"):
    """Dữ liệu JSON chuẩn cho Chart.js (cột + tròn)."""
    data = subject_summary(subject_id, semester_id)
    labels = [r["class_name"] for r in data["summary"]]
    rates = [r["pass_rate"] for r in data["summary"]]
    counts = [r["passed_count"] for r in data["summary"]]
    return {
        "chart_type": chart_type or "bar",
        "subject_name": data["subject_name"],
        "semester_name": data["semester_name"],
        "academic_year": data["academic_year"],
        "data": {
            "labels": labels,
            "datasets": [
                {"label": "Tỷ lệ Đạt (%)", "backgroundColor": "#3b82f6",
                 "borderColor": "#1d4ed8", "borderWidth": 1, "data": rates},
                {"label": "Số lượng học sinh Đạt", "backgroundColor": "#10b981",
                 "borderColor": "#047857", "borderWidth": 1, "data": counts},
            ],
        },
        "options": {"responsive": True,
                    "scales": {"y": {"beginAtZero": True, "max": 100}}},
    }


def grade_summary(grade_id, semester_id):
    """Thống kê tổng kết chung theo khối: gộp các môn của khối trong kỳ."""
    from studentapp.models.subject import Subject

    try:
        gid = int(grade_id)
    except (TypeError, ValueError):
        from studentapp.exceptions import ValidationError
        raise ValidationError("grade_id không hợp lệ.")
    subjects = Subject.query.filter_by(grade_id=gid, is_active=True).all()
    passing = _passing_score()
    total_size = 0
    total_passed = 0
    per_subject = []
    for s in subjects:
        d = subject_summary(s.id, semester_id)
        size = sum(r["class_size"] for r in d["summary"])
        passed = sum(r["passed_count"] for r in d["summary"])
        total_size += size
        total_passed += passed
        per_subject.append({
            "subject_id": s.id, "subject_name": s.subject_name,
            "class_size": size, "passed_count": passed,
            "pass_rate": round(passed / size * 100, 2) if size else 0.0,
        })
    return {
        "grade_id": gid, "semester_id": int(semester_id),
        "passing_threshold": passing,
        "total_size": total_size, "total_passed": total_passed,
        "overall_rate": round(total_passed / total_size * 100, 2) if total_size else 0.0,
        "per_subject": per_subject,
    }


def build_excel(subject_id, semester_id):
    """Xuất báo cáo tổng kết môn ra Excel (openpyxl) → bytes."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font

    data = subject_summary(subject_id, semester_id)
    wb = Workbook()
    ws = wb.active
    ws.title = "Bao cao tong ket mon"
    ws.append([f"BÁO CÁO TỔNG KẾT MÔN HỌC — {data['subject_name']}"])
    ws.append([f"Học kỳ: {data['semester_name']} — Năm học: {data['academic_year']} "
               f"— Điểm đạt ≥ {data['passing_threshold']}"])
    ws.append(["STT", "Lớp", "Sĩ số", "Số lượng đạt", "Tỷ lệ %"])
    for r in data["summary"]:
        ws.append([r["stt"], r["class_name"], r["class_size"],
                   r["passed_count"], r["pass_rate"]])
    for row in ws.iter_rows():
        for cell in row:
            cell.alignment = Alignment(horizontal="center", vertical="center")
    ws["A1"].font = Font(bold=True, size=13)
    for col, width in zip("ABCDE", (8, 14, 10, 16, 12)):
        ws.column_dimensions[col].width = width
    import io

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue(), data


def build_pdf(subject_id, semester_id):
    """Xuất báo cáo tổng kết môn ra PDF (reportlab) → bytes."""
    import io

    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas

    data = subject_summary(subject_id, semester_id)
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    y = h - 20 * mm
    c.setFont("Helvetica-Bold", 14)
    c.drawString(20 * mm, y, "BAO CAO TONG KET MON HOC")
    y -= 8 * mm
    c.setFont("Helvetica", 11)
    c.drawString(20 * mm, y,
                 f"{data['subject_name']} — {data['semester_name']} — "
                 f"{data['academic_year']} (Dat >= {data['passing_threshold']})")
    y -= 10 * mm
    c.setFont("Helvetica-Bold", 10)
    for x, head in zip((20, 40, 90, 120, 155),
                       ["STT", "Lop", "Si so", "SL dat", "Ty le %"]):
        c.drawString(x * mm / 10, y, head)
    y -= 7 * mm
    c.setFont("Helvetica", 10)
    for r in data["summary"]:
        c.drawString(20 * mm / 10, y, str(r["stt"]))
        c.drawString(40 * mm / 10, y, str(r["class_name"]))
        c.drawString(90 * mm / 10, y, str(r["class_size"]))
        c.drawString(120 * mm / 10, y, str(r["passed_count"]))
        c.drawString(155 * mm / 10, y, str(r["pass_rate"]))
        y -= 6 * mm
        if y < 20 * mm:
            c.showPage()
            y = h - 20 * mm
            c.setFont("Helvetica", 10)
    c.showPage()
    c.save()
    return buf.getvalue(), data
