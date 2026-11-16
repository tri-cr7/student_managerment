"""SERVICE classes — Logic nghiệp vụ Quản lý lớp học và phân bổ (SD05, SD06)."""
from datetime import date
from studentapp.extensions import db
from studentapp.repositories.class_repository import ClassRepository
from studentapp.models.class_room import Class
from studentapp.models.class_enrollment import ClassEnrollment, EnrollmentStatusEnum
from studentapp.models.student import Student
from studentapp.exceptions import AppError, ValidationError, NotFoundError, BusinessRuleError


class ClassService:

    @staticmethod
    def get_all_grades():
        return ClassRepository.get_all_grades()

    @staticmethod
    def get_classes_by_grade(grade_id):
        return ClassRepository.get_classes_by_grade(grade_id)

    @staticmethod
    def get_all_classes():
        return ClassRepository.get_all_classes()

    @staticmethod
    def get_class_detail(class_id):
        cls = ClassRepository.get_class_by_id(class_id)
        if not cls:
            raise NotFoundError("Không tìm thấy lớp học.")
        return cls.to_dict()

    @staticmethod
    def get_students_in_class(class_id):
        cls = ClassRepository.get_class_by_id(class_id)
        if not cls:
            raise NotFoundError("Không tìm thấy lớp học.")

        # Lấy danh sách học sinh đang học trong lớp thông qua bảng enrollment
        active_enrollments = ClassEnrollment.query.filter_by(
            class_id=class_id,
            status=EnrollmentStatusEnum.DANG_HOC
        ).all()

        return [enrollment.student.to_dict() for enrollment in active_enrollments if enrollment.student]

    @staticmethod
    def create_class(payload):
        name = payload.get("class_name")
        grade_id = payload.get("grade_id")
        academic_year_id = payload.get("academic_year_id")
        homeroom_teacher_id = payload.get("homeroom_teacher_id")

        if not name or not grade_id or not academic_year_id:
            raise ValidationError("Tên lớp, khối lớp và năm học là bắt buộc.")

        new_class = Class(
            class_name=name,
            grade_id=grade_id,
            academic_year_id=academic_year_id,
            homeroom_teacher_id=homeroom_teacher_id,
            current_size=0
        )
        return ClassRepository.save(new_class)

    @staticmethod
    def update_class(class_id, payload):
        cls = ClassRepository.get_class_by_id(class_id)
        if not cls:
            raise NotFoundError("Không tìm thấy lớp học.")

        if "class_name" in payload:
            cls.class_name = payload["class_name"]
        if "homeroom_teacher_id" in payload:
            cls.homeroom_teacher_id = payload["homeroom_teacher_id"]

        db.session.commit()
        return cls

    @staticmethod
    def delete_class(class_id):
        cls = ClassRepository.get_class_by_id(class_id)
        if not cls:
            raise NotFoundError("Không tìm thấy lớp học.")

        if cls.current_size > 0:
            raise BusinessRuleError("Không thể xóa lớp học vẫn còn học sinh đang theo học.")

        ClassRepository.delete(cls)

    @staticmethod
    def enroll_student(class_id, payload):
        student_id = payload.get("student_id")
        academic_year_id = payload.get("academic_year_id")

        if not student_id or not academic_year_id:
            raise ValidationError("Thiếu thông tin mã học sinh hoặc năm học.")

        cls = ClassRepository.get_class_by_id(class_id)
        if not cls:
            raise NotFoundError("Không tìm thấy lớp học.")

        student = Student.query.get(student_id)
        if not student:
            raise NotFoundError("Không tìm thấy học sinh.")

        # Business Rule SD05: Headcount cap <= 40
        if cls.current_size >= 40:
            raise BusinessRuleError("Lớp học đã đạt sĩ số tối đa (40 học sinh).")

        # Kiểm tra xem học sinh đã có bản ghi DANG_HOC nào trong năm học này chưa
        existing_enrollment = ClassEnrollment.query.filter_by(
            student_id=student_id,
            academic_year_id=academic_year_id,
            status=EnrollmentStatusEnum.DANG_HOC
        ).first()

        if existing_enrollment:
            if existing_enrollment.class_id == class_id:
                raise BusinessRuleError("Học sinh này đã có trong lớp học này rồi.")
            else:
                # Nếu đang ở lớp khác, chuyển trạng thái thành DA_CHUYEN và giảm sĩ số lớp cũ
                existing_enrollment.status = EnrollmentStatusEnum.DA_CHUYEN
                old_cls = ClassRepository.get_class_by_id(existing_enrollment.class_id)
                if old_cls and old_cls.current_size > 0:
                    old_cls.current_size -= 1

        # Tạo bản ghi enrollment mới
        new_enrollment = ClassEnrollment(
            student_id=student_id,
            class_id=class_id,
            academic_year_id=academic_year_id,
            enrollment_date=date.today(),
            status=EnrollmentStatusEnum.DANG_HOC
        )

        db.session.add(new_enrollment)
        cls.current_size += 1
        db.session.commit()

        return {"student_id": student.id, "class_id": class_id, "current_size": cls.current_size}

    @staticmethod
    def transfer_student(payload):
        student_id = payload.get("student_id")
        to_class_id = payload.get("to_class_id")
        academic_year_id = payload.get("academic_year_id")

        if not student_id or not to_class_id or not academic_year_id:
            raise ValidationError("Thiếu thông tin điều chuyển (student_id, to_class_id hoặc academic_year_id).")

        student = Student.query.get(student_id)
        if not student:
            raise NotFoundError("Không tìm thấy học sinh.")

        target_class = ClassRepository.get_class_by_id(to_class_id)
        if not target_class:
            raise NotFoundError("Lớp học đích không tồn tại.")

        # Business Rule SD06 / SD05: Check capacity on destination
        if target_class.current_size >= 40:
            raise BusinessRuleError("Lớp học nhận đã đạt sĩ số tối đa (40 học sinh).")

        # Tìm lớp hiện tại đang học của học sinh trong năm học
        current_enrollment = ClassEnrollment.query.filter_by(
            student_id=student_id,
            academic_year_id=academic_year_id,
            status=EnrollmentStatusEnum.DANG_HOC
        ).first()

        old_class_id = None
        if current_enrollment:
            old_class_id = current_enrollment.class_id
            if old_class_id == to_class_id:
                raise BusinessRuleError("Học sinh đã ở trong lớp học này rồi.")

            # Đổi trạng thái lớp cũ sang DA_CHUYEN và giảm sĩ số
            current_enrollment.status = EnrollmentStatusEnum.DA_CHUYEN
            old_cls = ClassRepository.get_class_by_id(old_class_id)
            if old_cls and old_cls.current_size > 0:
                old_cls.current_size -= 1

        # Tạo bản ghi enrollment mới vào lớp đích
        new_enrollment = ClassEnrollment(
            student_id=student_id,
            class_id=to_class_id,
            academic_year_id=academic_year_id,
            enrollment_date=date.today(),
            status=EnrollmentStatusEnum.DANG_HOC
        )

        db.session.add(new_enrollment)
        target_class.current_size += 1
        db.session.commit()

        return {
            "student_id": student.id,
            "from_class_id": old_class_id,
            "to_class_id": to_class_id,
            "new_target_size": target_class.current_size
        }