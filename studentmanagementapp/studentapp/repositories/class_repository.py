"""REPOSITORY classes — Thao tác DB cho Khối lớp và Lớp học."""
from studentapp.extensions import db
from studentapp.models import ClassEnrollment, EnrollmentStatusEnum
from studentapp.models.grade import Grade
from studentapp.models.class_room import Class
from studentapp.models.student import Student


class ClassRepository:

    @staticmethod
    def get_all_grades():
        return Grade.query.order_by(Grade.grade_level).all()

    @staticmethod
    def get_classes_by_grade(grade_id):
        return Class.query.filter_by(grade_id=grade_id).all()

    @staticmethod
    def get_all_classes():
        return Class.query.all()

    @staticmethod
    def get_class_by_id(class_id):
        return Class.query.get(class_id)

    @staticmethod
    def get_students_in_class(class_id):
        # Thay đổi từ Student sang truy vấn qua ClassEnrollment
        active_enrollments = ClassEnrollment.query.filter_by(
            class_id=class_id,
            status=EnrollmentStatusEnum.DANG_HOC
        ).all()
        return [enrollment.student for enrollment in active_enrollments if enrollment.student]

    @staticmethod
    def save(entity):
        db.session.add(entity)
        db.session.commit()
        return entity

    @staticmethod
    def delete(entity):
        db.session.delete(entity)
        db.session.commit()