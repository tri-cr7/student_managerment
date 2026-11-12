"""REPOSITORY class_enrollment — danh sách học sinh thuộc lớp."""
from studentapp.extensions import db
from studentapp.models.class_enrollment import ClassEnrollment, EnrollmentStatusEnum


def list_student_ids_by_class(class_id, only_active=True):
    """Danh sách ID học sinh đang học trong một lớp."""
    q = ClassEnrollment.query.filter_by(class_id=int(class_id))
    if only_active:
        q = q.filter_by(status=EnrollmentStatusEnum.DANG_HOC)
    return [e.student_id for e in q.order_by(ClassEnrollment.id).all()]


def list_by_class(class_id, only_active=True):
    q = ClassEnrollment.query.filter_by(class_id=int(class_id))
    if only_active:
        q = q.filter_by(status=EnrollmentStatusEnum.DANG_HOC)
    return q.order_by(ClassEnrollment.id).all()


def is_student_in_class(student_id, class_id) -> bool:
    """Kiểm tra học sinh có thuộc lớp (dùng cho rule A6)."""
    return (
        ClassEnrollment.query.filter_by(
            student_id=int(student_id),
            class_id=int(class_id),
            status=EnrollmentStatusEnum.DANG_HOC,
        ).count()
        > 0
    )


def list_class_ids_by_student(student_id, academic_year_id=None):
    """Các lớp mà một học sinh đang học."""
    q = ClassEnrollment.query.filter_by(
        student_id=int(student_id), status=EnrollmentStatusEnum.DANG_HOC
    )
    if academic_year_id:
        q = q.filter_by(academic_year_id=int(academic_year_id))
    return [e.class_id for e in q.all()]
