"""REPOSITORY score — truy vấn bảng điểm."""
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
    """Lấy dòng điểm của 1 học sinh trong 1 assignment."""
    return (
        Score.query.filter_by(
            assignment_id=int(assignment_id), student_id=int(student_id)
        )
        .first()
    )


def list_by_assignment(assignment_id, draft_only=None):
    """Lấy toàn bộ dòng điểm của một lớp môn học.

    ``draft_only``:
      * ``None``  → trả cả nháp & chính thức (kèm cờ ``is_draft``).
      * ``True``  → chỉ bảng điểm tạm.
      * ``False`` → chỉ điểm chính thức (dùng cho báo cáo & xuất file).
    """
    q = Score.query.filter_by(assignment_id=int(assignment_id))
    if draft_only is not None:
        q = q.filter_by(is_draft=bool(draft_only))
    return q.order_by(Score.student_id).all()


def list_by_assignment_and_students(assignment_id, student_ids, draft_only=None):
    ids = [int(i) for i in (student_ids or [])]
    if not ids:
        return []
    q = Score.query.filter(
        Score.assignment_id == int(assignment_id), Score.student_id.in_(ids)
    )
    if draft_only is not None:
        q = q.filter_by(is_draft=bool(draft_only))
    return q.order_by(Score.student_id).all()


def list_by_student(student_id, assignment_ids=None, draft_only=False):
    """Toàn bộ điểm của một học sinh.

    Mặc định ``draft_only=False`` → chỉ điểm **chính thức** (chống lộ điểm tạm).
    """
    q = Score.query.filter_by(student_id=int(student_id))
    if assignment_ids:
        q = q.filter(Score.assignment_id.in_([int(i) for i in assignment_ids]))
    if draft_only is not None:
        q = q.filter_by(is_draft=bool(draft_only))
    return q.order_by(Score.assignment_id).all()


def count_by_assignment(assignment_id, draft_only=None) -> int:
    q = Score.query.filter_by(assignment_id=int(assignment_id))
    if draft_only is not None:
        q = q.filter_by(is_draft=bool(draft_only))
    return q.count()


def count_filled_cells(score: Score, active_columns=None) -> int:
    """Đếm số ô điểm đã có giá trị (không tính ô NULL)."""
    cols = active_columns or ALL_SCORE_COLUMNS
    return sum(1 for col in cols if getattr(score, col) is not None)


def count_all_cells(score: Score, active_columns=None) -> int:
    """Tổng số ô điểm của một dòng (luôn là 9 theo thiết kế hiện tại)."""
    return len(active_columns or ALL_SCORE_COLUMNS)


def count_missing_cells(score: Score, active_columns=None) -> list:
    """Trả về danh sách tên cột đang NULL (chưa nhập)."""
    cols = active_columns or ALL_SCORE_COLUMNS
    return [col for col in cols if getattr(score, col) is None]


def count_filled_cells_bulk(assignment_id) -> int:
    """Tổng số ô đã nhập của cả lớp (dùng cho rule B1/B2)."""
    rows = list_by_assignment(assignment_id, draft_only=True)
    return sum(count_filled_cells(r) for r in rows)


def sum_of_filled(score: Score) -> float:
    """Tổng điểm của các ô đã nhập (chưa nhân trọng số)."""
    total = 0.0
    for col in ALL_SCORE_COLUMNS:
        v = getattr(score, col)
        if v is not None:
            total += float(v)
    return total
