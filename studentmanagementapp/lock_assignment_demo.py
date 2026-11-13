"""Mô phỏng Giáo vụ CHỐT bảng điểm (chuyển bảng điểm TẠM → bảng điểm CHÍNH THỨC).

Dùng để test luồng SD25 (đơn phúc khảo) trong Postman: sau khi bảng điểm được
chốt thì Giáo viên KHÔNG sửa trực tiếp được nữa, phải gửi đơn phúc khảo.

Cách chạy (từ thư mục ``studentmanagementapp``)::

    ./venv/bin/python lock_assignment_demo.py              # chốt assignment đầu tiên
    ./venv/bin/python lock_assignment_demo.py 1            # chốt assignment id=1
    ./venv/bin/python lock_assignment_demo.py 1 --unlock    # mở lại để test lại từ đầu

Hiệu lực (giống hệt luồng Giáo vụ duyệt trong tài liệu):
* ``teaching_assignments.is_locked = TRUE`` + ``locked_at = now``
* ``scores.is_draft = FALSE``  (điểm chính thức)
* ``scores.submitted_at = now``
* ``score_submissions.status = 'APPROVED'`` (nếu có đơn PENDING)
"""
import argparse
import os
import sys
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from studentapp import create_app  # noqa: E402
from studentapp.extensions import db  # noqa: E402


def lock_assignment(assignment_id):
    """Chốt bảng điểm của 1 assignment."""
    from studentapp.models.score import Score
    from studentapp.models.score_submission import ScoreSubmission, SubmissionStatusEnum
    from studentapp.models.teaching_assignment import TeachingAssignment

    assignment = db.session.get(TeachingAssignment, assignment_id)
    if assignment is None:
        print(f"KHONG tim thay assignment id={assignment_id}")
        return False

    now = datetime.utcnow()
    assignment.is_locked = True
    assignment.locked_at = now

    scores = Score.query.filter_by(assignment_id=assignment_id).all()
    for s in scores:
        s.is_draft = False
        s.submitted_at = now
        db.session.add(s)

    pending = (
        ScoreSubmission.query.filter_by(
            assignment_id=assignment_id, status=SubmissionStatusEnum.PENDING
        )
        .order_by(ScoreSubmission.id.desc())
        .first()
    )
    if pending is not None:
        pending.status = SubmissionStatusEnum.APPROVED
        pending.reviewed_at = now
        pending.review_note = "Chot bang diem (mô phỏng Giáo vụ)"
        db.session.add(pending)

    db.session.commit()

    print(f"Da CHOT bang diem assignment id={assignment_id}")
    print(f"  - teaching_assignments.is_locked = True")
    print(f"  - {len(scores)} dong diem chuyen sang CHINH THUC (is_draft = False)")
    if pending is not None:
        print(f"  - don gui duyet #{pending.id} chuyen sang APPROVED")
    return True


def unlock_assignment(assignment_id):
    """Mở lại bảng điểm (đưa về trạng thái nháp, GV sửa được)."""
    from studentapp.models.score import Score
    from studentapp.models.teaching_assignment import TeachingAssignment

    assignment = db.session.get(TeachingAssignment, assignment_id)
    if assignment is None:
        print(f"KHONG tim thay assignment id={assignment_id}")
        return False

    assignment.is_locked = False
    assignment.locked_at = None

    scores = Score.query.filter_by(assignment_id=assignment_id).all()
    for s in scores:
        s.is_draft = True
        db.session.add(s)

    db.session.commit()
    print(f"Da MO LAI bang diem assignment id={assignment_id} ({len(scores)} dong diem)")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Mo phong Giao vu CHOT bang diem (cho test SD25)"
    )
    parser.add_argument(
        "assignment_id",
        nargs="?",
        type=int,
        default=None,
        help="ID assignment can chot (mac dinh: assignment dau tien)",
    )
    parser.add_argument(
        "--unlock", action="store_true", help="Mo lai bang diem thay vi chot"
    )
    args = parser.parse_args()

    app = create_app("development")
    with app.app_context():
        from studentapp.models.teaching_assignment import TeachingAssignment

        if args.assignment_id is not None:
            assignment_id = args.assignment_id
        else:
            first = TeachingAssignment.query.order_by(TeachingAssignment.id).first()
            if first is None:
                print("Chua co assignment nao trong DB. Hay chay seed_teacher_demo.py truoc.")
                return
            assignment_id = first.id

        if args.unlock:
            unlock_assignment(assignment_id)
        else:
            lock_assignment(assignment_id)


if __name__ == "__main__":
    main()
