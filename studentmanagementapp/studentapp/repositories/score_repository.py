from sqlalchemy import func

from studentapp.extensions import db
from studentapp.models.score import Score, ALL_SCORE_COLUMNS

def get_by_id(score_id):
    try:
        sid = int(score_id)
    except (TypeError, ValueError):
        return None
    return db.session.get(Score, sid)

def get_by_assignment_and_student(assignment_id, student_id):

    return (
        Score.query.filter_by(
            assignment_id=int(assignment_id), student_id=int(student_id)
        )
        .first()
    )

def list_by_assignment(assignment_id, draft_only=None):

    q = Score.query.filter_by(assignment_id=int(assignment_id))
    if draft_only is not None:
        q = q.filter_by(is_draft=bool(draft_only))
    return q.order_by(Score.student_id).all()

def list_by_student(student_id, assignment_ids=None, draft_only=False):

    q = Score.query.filter_by(student_id=int(student_id))
    if assignment_ids:
        q = q.filter(Score.assignment_id.in_([int(i) for i in assignment_ids]))
    if draft_only is not None:
        q = q.filter_by(is_draft=bool(draft_only))
    return q.order_by(Score.assignment_id).all()

def count_filled_cells(score: Score, active_columns=None) -> int:

    cols = active_columns or ALL_SCORE_COLUMNS
    return sum(1 for col in cols if getattr(score, col) is not None)

def count_missing_cells(score: Score, active_columns=None) -> list:

    cols = active_columns or ALL_SCORE_COLUMNS
    return [col for col in cols if getattr(score, col) is None]

def list_by_class_subject_year(class_id, subject_id, academic_year_id, draft_only=False):

    from studentapp.models.semester import Semester
    from studentapp.models.teaching_assignment import TeachingAssignment

    q = (
        Score.query.join(
            TeachingAssignment, Score.assignment_id == TeachingAssignment.id
        )
        .join(Semester, TeachingAssignment.semester_id == Semester.id)
        .filter(
            TeachingAssignment.class_id == int(class_id),
            TeachingAssignment.subject_id == int(subject_id),
            Semester.academic_year_id == int(academic_year_id),
        )
    )
    if draft_only is not None:
        q = q.filter(Score.is_draft.is_(bool(draft_only)))
    return q.order_by(Score.student_id).all()
