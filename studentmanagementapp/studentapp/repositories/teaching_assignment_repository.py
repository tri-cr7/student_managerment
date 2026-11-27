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

    q = TeachingAssignment.query.filter_by(teacher_id=int(teacher_id))
    if semester_id:
        q = q.filter_by(semester_id=int(semester_id))
    if academic_year_id:
        q = q.join(Semester).filter(Semester.academic_year_id == int(academic_year_id))
    return q.order_by(TeachingAssignment.id.desc()).all()

def list_all(page=1, limit=20, teacher_id=None, semester_id=None,
             class_id=None, subject_id=None):

    q = TeachingAssignment.query
    if teacher_id not in (None, ""):
        q = q.filter_by(teacher_id=int(teacher_id))
    if semester_id not in (None, ""):
        q = q.filter_by(semester_id=int(semester_id))
    if class_id not in (None, ""):
        q = q.filter_by(class_id=int(class_id))
    if subject_id not in (None, ""):
        q = q.filter_by(subject_id=int(subject_id))
    total = q.count()
    try:
        page = max(1, int(page))
    except (TypeError, ValueError):
        page = 1
    try:
        limit = min(100, max(1, int(limit)))
    except (TypeError, ValueError):
        limit = 20
    rows = (
        q.order_by(TeachingAssignment.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )
    return {"total": total, "page": page, "limit": limit, "data": rows}

def get_by_triplet(class_id, subject_id, semester_id, exclude_id=None):

    q = TeachingAssignment.query.filter_by(
        class_id=int(class_id),
        subject_id=int(subject_id),
        semester_id=int(semester_id),
    )
    if exclude_id is not None:
        q = q.filter(TeachingAssignment.id != int(exclude_id))
    return q.first()

def create(teacher_id, class_id, subject_id, semester_id):
    row = TeachingAssignment(
        teacher_id=int(teacher_id),
        class_id=int(class_id),
        subject_id=int(subject_id),
        semester_id=int(semester_id),
        is_locked=False,
    )
    db.session.add(row)
    db.session.flush()
    return row

def delete_row(row):
    db.session.delete(row)
    db.session.flush()

def count_scores(assignment_id) -> int:

    from studentapp.models.score import Score

    return Score.query.filter_by(assignment_id=int(assignment_id)).count()

def has_submissions(assignment_id) -> bool:

    from studentapp.models.score_submission import ScoreSubmission

    return (
        ScoreSubmission.query.filter_by(assignment_id=int(assignment_id)).count() > 0
    )

def has_pending_submission(assignment_id) -> bool:

    from studentapp.models.score_submission import ScoreSubmission, SubmissionStatusEnum

    return (
        ScoreSubmission.query.filter_by(
            assignment_id=int(assignment_id), status=SubmissionStatusEnum.PENDING
        ).count()
        > 0
    )

def get_pending_submission(assignment_id):

    from studentapp.models.score_submission import ScoreSubmission, SubmissionStatusEnum

    return (
        ScoreSubmission.query.filter_by(
            assignment_id=int(assignment_id), status=SubmissionStatusEnum.PENDING
        )
        .order_by(ScoreSubmission.id.desc())
        .first()
    )
