from studentapp.extensions import db
from studentapp.models.class_enrollment import ClassEnrollment, EnrollmentStatusEnum
from studentapp.models.student import Student

def _not_deleted(q):

    return q.filter(
        ClassEnrollment.student_id.in_(
            db.session.query(Student.id).filter(Student.is_deleted.is_(False))
        )
    )

def list_student_ids_by_class(class_id, only_active=True, academic_year_id=None):

    q = ClassEnrollment.query.filter_by(class_id=int(class_id))
    if only_active:
        q = q.filter_by(status=EnrollmentStatusEnum.DANG_HOC)
    if academic_year_id not in (None, ""):
        q = q.filter_by(academic_year_id=int(academic_year_id))
    q = _not_deleted(q)
    return [e.student_id for e in q.order_by(ClassEnrollment.id).all()]

def list_enrolled_student_ids_by_class(class_id, academic_year_id=None):

    return list_student_ids_by_class(
        class_id, only_active=True, academic_year_id=academic_year_id
    )

def list_all_class_ids_by_student(student_id):

    q = ClassEnrollment.query.filter_by(student_id=int(student_id))
    return sorted({int(e.class_id) for e in q.all()})
