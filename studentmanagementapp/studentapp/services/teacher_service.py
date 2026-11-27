from studentapp.exceptions import NotFoundError, PermissionDeniedError
from studentapp.repositories import teaching_assignment_repository

def _get_assignment_or_404(assignment_id):
    assignment = teaching_assignment_repository.get_by_id(assignment_id)
    if assignment is None:
        raise NotFoundError("Không tìm thấy lớp môn học (phân công giảng dạy).")
    return assignment

def ensure_teacher_owns_assignment(assignment_id, teacher_id):

    assignment = _get_assignment_or_404(assignment_id)
    if int(assignment.teacher_id) != int(teacher_id):
        raise PermissionDeniedError(
            "Bạn không phụ trách lớp môn học này nên không được thao tác điểm số!"
        )
    return assignment

def ensure_assignment_open(assignment):

    from studentapp.exceptions import ScoreTableLockedError

    if assignment.is_locked:
        raise ScoreTableLockedError(
            "Bảng điểm đã được chốt. Bạn không thể sửa trực tiếp — "
            "vui lòng gửi yêu cầu chỉnh điểm qua đơn phúc khảo!"
        )
    return assignment

def ensure_no_pending_submission(assignment_id):

    from studentapp.exceptions import ScoreSubmissionPendingError

    pending = teaching_assignment_repository.get_pending_submission(assignment_id)
    if pending is not None:
        raise ScoreSubmissionPendingError(
            "Bảng điểm đang được gửi duyệt. Vui lòng hủy đơn gửi duyệt trước khi sửa điểm!",
            pending_submission_id=pending.id,
        )
    return True

def list_my_assignments(teacher_id, semester_id=None, academic_year_id=None):

    return teaching_assignment_repository.list_by_teacher(
        teacher_id, semester_id=semester_id, academic_year_id=academic_year_id
    )

def ensure_teacher_owns_class_subject(teacher_id, class_id, subject_id,
                                     academic_year_id=None):

    assignments = teaching_assignment_repository.list_by_teacher(
        teacher_id, academic_year_id=academic_year_id
    )
    for a in assignments:
        if int(a.class_id) == int(class_id) and int(a.subject_id) == int(subject_id):
            return a
    raise PermissionDeniedError(
        "Bạn không phụ trách môn học này ở lớp đó nên không được xem/xuất "
        "điểm trung bình lớp!"
    )

def list_teacher_class_ids(teacher_id):

    return sorted({int(a.class_id) for a in list_my_assignments(teacher_id)})

def ensure_teacher_can_view_student(teacher_id, student_id):

    from studentapp.repositories import class_enrollment_repository

    my_class_ids = set(list_teacher_class_ids(teacher_id))
    if not my_class_ids:
        raise PermissionDeniedError(
            "Bạn chưa được phân công lớp môn học nào nên không được xem hồ sơ "
            "học sinh."
        )
    student_class_ids = set(
        class_enrollment_repository.list_all_class_ids_by_student(student_id)
    )
    if not (student_class_ids & my_class_ids):
        raise PermissionDeniedError(
            "Học sinh này không thuộc lớp bạn phụ trách nên bạn không được xem "
            "hồ sơ!"
        )
    return True
