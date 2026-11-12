"""REPOSITORY teaching_assignment — truy vấn phân công giảng dạy."""
from studentapp.extensions import db
from studentapp.models.teaching_assignment import TeachingAssignment
from studentapp.models.semester import Semester


def get_by_id(assignment_id):
    try:
        aid = int(assignment_id)
    except (TypeError, ValueError):
        return None
    return db.session.get(TeachingAssignment, aid)


def list_by_teacher(teacher_id, semester_id=None, academic_year_id=None):
    """Danh sách lớp môn học mà Giáo viên được phụ trách (SD09).

    Lọc theo học kỳ / năm học nếu được truyền vào.
    """
    q = TeachingAssignment.query.filter_by(teacher_id=int(teacher_id))
    if semester_id:
        q = q.filter_by(semester_id=int(semester_id))
    if academic_year_id:
        q = q.join(Semester).filter(Semester.academic_year_id == int(academic_year_id))
    return q.order_by(TeachingAssignment.id.desc()).all()


def list_by_teacher_ids(teacher_ids, semester_id=None):
    ids = [int(i) for i in (teacher_ids or [])]
    if not ids:
        return []
    q = TeachingAssignment.query.filter(TeachingAssignment.teacher_id.in_(ids))
    if semester_id:
        q = q.filter_by(semester_id=int(semester_id))
    return q.order_by(TeachingAssignment.id.desc()).all()


def count_by_teacher(teacher_id) -> int:
    return TeachingAssignment.query.filter_by(teacher_id=int(teacher_id)).count()


def has_pending_submission(assignment_id) -> bool:
    """Bảng điểm đang có đơn gửi duyệt ở trạng thái PENDING hay không."""
    from studentapp.models.score_submission import ScoreSubmission, SubmissionStatusEnum

    return (
        ScoreSubmission.query.filter_by(
            assignment_id=int(assignment_id), status=SubmissionStatusEnum.PENDING
        ).count()
        > 0
    )


def get_pending_submission(assignment_id):
    """Trả về đơn gửi duyệt đang PENDING của assignment (nếu có)."""
    from studentapp.models.score_submission import ScoreSubmission, SubmissionStatusEnum

    return (
        ScoreSubmission.query.filter_by(
            assignment_id=int(assignment_id), status=SubmissionStatusEnum.PENDING
        )
        .order_by(ScoreSubmission.id.desc())
        .first()
    )
