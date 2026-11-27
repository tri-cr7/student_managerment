from datetime import date
from studentapp.extensions import db
from studentapp.repositories.class_repository import ClassRepository
from studentapp.repositories import system_rule_repository
from studentapp.models.class_room import Class
from studentapp.models.class_enrollment import ClassEnrollment, EnrollmentStatusEnum
from studentapp.models.academic_year import AcademicYear
from studentapp.models.grade import Grade
from studentapp.models.student import Student
from studentapp.models.user import User, UserRoleEnum
from studentapp.models.teaching_assignment import TeachingAssignment
from studentapp.exceptions import (
    AppError,
    DuplicateError,
    ValidationError,
    NotFoundError,
    BusinessRuleError,
    ClassSizeExceededError,
)
from studentapp.utils.audit import write_audit

def get_max_class_size():

    return system_rule_repository.get_int("MAX_CLASS_SIZE", 40)

def count_active_students(class_id):

    from studentapp.repositories import class_enrollment_repository

    return len(class_enrollment_repository.list_student_ids_by_class(class_id))

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

        active_enrollments = ClassEnrollment.query.filter_by(
            class_id=class_id,
            status=EnrollmentStatusEnum.DANG_HOC
        ).all()

        return [
            enrollment.student.to_dict()
            for enrollment in active_enrollments
            if enrollment.student and not enrollment.student.is_deleted
        ]

    @staticmethod
    def create_class(payload):

        name = (payload.get("class_name") or "").strip()
        grade_id = payload.get("grade_id")
        academic_year_id = payload.get("academic_year_id")
        homeroom_teacher_id = payload.get("homeroom_teacher_id")

        if not name or grade_id in (None, "") or academic_year_id in (None, ""):
            raise ValidationError("Tên lớp, khối lớp và năm học là bắt buộc.")

        try:
            grade_id = int(grade_id)
        except (TypeError, ValueError):
            raise ValidationError("grade_id không hợp lệ.")
        grade = db.session.get(Grade, grade_id)
        if grade is None:
            raise NotFoundError("Không tìm thấy khối lớp.")

        try:
            academic_year_id = int(academic_year_id)
        except (TypeError, ValueError):
            raise ValidationError("academic_year_id không hợp lệ.")
        if db.session.get(AcademicYear, academic_year_id) is None:
            raise NotFoundError("Không tìm thấy năm học.")

        teacher_id = None if homeroom_teacher_id in (None, "") else homeroom_teacher_id
        if teacher_id is not None:
            try:
                teacher_id = int(teacher_id)
            except (TypeError, ValueError):
                raise ValidationError("teacher_id không hợp lệ.")
            teacher = db.session.get(User, teacher_id)
            if teacher is None:
                raise NotFoundError("Không tìm thấy giáo viên.")
            if teacher.role != UserRoleEnum.TEACHER:
                raise ValidationError(
                    "Người được gán phải có vai trò Giáo viên (TEACHER).",
                    error="INVALID_HOMEROOM_TEACHER",
                )
            if not teacher.is_active or teacher.is_locked:
                raise ValidationError(
                    "Giáo viên không còn hoạt động nên không thể làm GVCN.",
                    error="TEACHER_INACTIVE",
                )

        duplicate = Class.query.filter(
            Class.class_name == name,
            Class.academic_year_id == academic_year_id,
        ).first()
        if duplicate is not None:
            raise DuplicateError(
                "Tên lớp %s đã tồn tại trong năm học này." % name,
                error="DUPLICATE_CLASS_NAME",
            )

        new_class = Class(
            class_name=name,
            grade_id=grade_id,
            academic_year_id=academic_year_id,
            homeroom_teacher_id=teacher_id,
            current_size=0
        )
        return ClassRepository.save(new_class)

    @staticmethod
    def update_class(class_id, payload):

        cls = ClassRepository.get_class_by_id(class_id)
        if not cls:
            raise NotFoundError("Không tìm thấy lớp học.")

        changed = {}

        if "class_name" in payload:
            new_name = (payload["class_name"] or "").strip()
            if not new_name:
                raise ValidationError("Tên lớp là bắt buộc.")
            if new_name != cls.class_name:
                changed["class_name"] = {"old": cls.class_name, "new": new_name}

        if payload.get("grade_id") not in (None, ""):
            try:
                grade_id = int(payload["grade_id"])
            except (TypeError, ValueError):
                raise ValidationError("grade_id không hợp lệ.")
            if db.session.get(Grade, grade_id) is None:
                raise NotFoundError("Không tìm thấy khối lớp.")
            if grade_id != cls.grade_id:
                changed["grade_id"] = {"old": cls.grade_id, "new": grade_id}

        if "homeroom_teacher_id" in payload:
            raw_teacher = payload["homeroom_teacher_id"]
            teacher_id = None if raw_teacher in (None, "") else raw_teacher
            if teacher_id is not None:
                try:
                    teacher_id = int(teacher_id)
                except (TypeError, ValueError):
                    raise ValidationError("teacher_id không hợp lệ.")
                teacher = db.session.get(User, teacher_id)
                if teacher is None:
                    raise NotFoundError("Không tìm thấy giáo viên.")
                if teacher.role != UserRoleEnum.TEACHER:
                    raise ValidationError(
                        "Người được gán phải có vai trò Giáo viên (TEACHER).",
                        error="INVALID_HOMEROOM_TEACHER",
                    )
                if not teacher.is_active or teacher.is_locked:
                    raise ValidationError(
                        "Giáo viên không còn hoạt động nên không thể làm GVCN.",
                        error="TEACHER_INACTIVE",
                    )
            if teacher_id != cls.homeroom_teacher_id:
                changed["homeroom_teacher_id"] = {
                    "old": cls.homeroom_teacher_id,
                    "new": teacher_id,
                }

        if "class_name" in changed:
            duplicate = Class.query.filter(
                Class.class_name == changed["class_name"]["new"],
                Class.academic_year_id == cls.academic_year_id,
                Class.id != cls.id,
            ).first()
            if duplicate is not None:
                raise DuplicateError(
                    "Tên lớp %s đã tồn tại trong năm học này."
                    % changed["class_name"]["new"],
                    error="DUPLICATE_CLASS_NAME",
                )

        if "class_name" in changed:
            cls.class_name = changed["class_name"]["new"]
        if "grade_id" in changed:
            cls.grade_id = changed["grade_id"]["new"]
        if "homeroom_teacher_id" in changed:
            cls.homeroom_teacher_id = changed["homeroom_teacher_id"]["new"]

        if changed:
            write_audit(payload.get("actor_id"), "UPDATE_CLASS", {
                "class_id": cls.id,
                "class_name": cls.class_name,
                "grade_id": cls.grade_id,
                "homeroom_teacher_id": cls.homeroom_teacher_id,
                "changes": changed,
            })

        db.session.commit()
        return cls

    @staticmethod
    def delete_class(class_id):
        cls = ClassRepository.get_class_by_id(class_id)
        if not cls:
            raise NotFoundError("Không tìm thấy lớp học.")

        assignment_count = TeachingAssignment.query.filter_by(
            class_id=cls.id
        ).count()
        if assignment_count > 0:
            raise BusinessRuleError(
                "Không thể xóa lớp học vẫn còn %d phân công giảng dạy. "
                "Vui lòng gỡ phân công trước khi xóa lớp." % assignment_count,
                error="CLASS_HAS_ASSIGNMENTS",
            )

        active_students = count_active_students(cls.id)
        if active_students > 0:
            raise BusinessRuleError(
                "Không thể xóa lớp học vẫn còn %d học sinh đang theo học."
                % active_students
            )

        stale = ClassEnrollment.query.filter_by(class_id=cls.id).all()
        for enr in stale:
            db.session.delete(enr)
        db.session.flush()

        ClassRepository.delete(cls)

    @staticmethod
    def enroll_student(class_id, payload):

        academic_year_id = payload.get("academic_year_id")

        raw_ids = payload.get("student_ids")
        if raw_ids is None:
            raw_ids = payload.get("student_id")
        if raw_ids is None:
            raise ValidationError("Thiếu thông tin mã học sinh hoặc năm học.")
        if isinstance(raw_ids, (list, tuple, set)):
            student_ids = []
            for v in raw_ids:
                try:
                    student_ids.append(int(v))
                except (TypeError, ValueError):
                    raise ValidationError("Danh sách mã học sinh không hợp lệ.")
        else:
            try:
                student_ids = [int(raw_ids)]
            except (TypeError, ValueError):
                raise ValidationError("Mã học sinh không hợp lệ.")

        if not student_ids:
            raise ValidationError("Thiếu thông tin mã học sinh hoặc năm học.")
        if not academic_year_id:
            raise ValidationError("Thiếu thông tin mã học sinh hoặc năm học.")

        seen = set()
        unique_ids = []
        for sid in student_ids:
            if sid not in seen:
                seen.add(sid)
                unique_ids.append(sid)
        student_ids = unique_ids

        cls = ClassRepository.get_class_by_id(class_id)
        if not cls:
            raise NotFoundError("Không tìm thấy lớp học.")

        if db.session.get(AcademicYear, int(academic_year_id)) is None:
            raise ValidationError("Năm học không hợp lệ.")

        if int(cls.academic_year_id) != int(academic_year_id):
            raise BusinessRuleError(
                "Lớp %s không thuộc năm học đang thao tác. "
                "Vui lòng chọn lớp cùng năm học với lớp hiện tại của học sinh."
                % cls.class_name
            )

        students = []
        for sid in student_ids:
            st = Student.query.get(sid)
            if not st:
                raise NotFoundError("Không tìm thấy học sinh (ID: %s)." % sid)

            if st.is_deleted:
                raise BusinessRuleError(
                    "Học sinh %s (%s) đã bị xoá mềm — không thể phân lớp. "
                    "Hãy khôi phục hồ sơ trước."
                    % (st.full_name, st.student_code)
                )
            students.append(st)

        for student in students:
            actives = ClassEnrollment.query.filter(
                ClassEnrollment.student_id == student.id,
                ClassEnrollment.status == EnrollmentStatusEnum.DANG_HOC,
            ).all()
            for enr in actives:
                if int(enr.class_id) == int(class_id):
                    raise BusinessRuleError(
                        "Học sinh %s đã có trong lớp học này rồi."
                        % student.student_code
                    )

        max_size = get_max_class_size()
        current_size = count_active_students(cls.id)
        adding_count = len(student_ids)
        if current_size + adding_count > max_size:
            raise ClassSizeExceededError(
                "Không thể phân lớp! Lớp %s hiện có %d học sinh, thêm %d học sinh "
                "sẽ vượt quá sĩ số tối đa cho phép (%d học sinh)!"
                % (cls.class_name, current_size, adding_count, max_size),
                current_size=current_size,
                max_size=max_size,
            )

        enrolled_count = 0
        touched_class_ids = set()
        for student in students:
            student_id = student.id

            old_enrollments = ClassEnrollment.query.filter(
                ClassEnrollment.student_id == student_id,
                ClassEnrollment.status == EnrollmentStatusEnum.DANG_HOC,
            ).all()
            for enr in old_enrollments:
                enr.status = EnrollmentStatusEnum.DA_CHUYEN
                old_cls = ClassRepository.get_class_by_id(enr.class_id)
                if old_cls is not None:
                    touched_class_ids.add(int(old_cls.id))

            new_enrollment = ClassEnrollment(
                student_id=student_id,
                class_id=class_id,
                academic_year_id=academic_year_id,
                enrollment_date=date.today(),
                status=EnrollmentStatusEnum.DANG_HOC
            )

            db.session.add(new_enrollment)
            enrolled_count += 1

        db.session.flush()

        touched_class_ids.add(int(cls.id))
        for cid in touched_class_ids:
            target = ClassRepository.get_class_by_id(cid)
            if target is not None:
                target.current_size = count_active_students(cid)

        db.session.commit()

        return {
            "class_id": class_id,
            "class_name": cls.class_name,
            "enrolled_count": enrolled_count,
            "new_current_size": cls.current_size,
            "current_size": cls.current_size,
            "max_size": max_size,
            "student_ids": [s.id for s in students],
        }

    @staticmethod
    def transfer_student(payload):

        student_id = payload.get("student_id")
        to_class_id = payload.get("to_class_id")
        from_class_id = payload.get("from_class_id")
        academic_year_id = payload.get("academic_year_id")
        transfer_reason = payload.get("transfer_reason")
        actor_id = payload.get("actor_id")

        if not student_id or not to_class_id:
            raise ValidationError(
                "Thiếu thông tin điều chuyển (student_id hoặc to_class_id).")

        if not academic_year_id:
            academic_year_id = ClassService._get_current_academic_year_id()
        if not academic_year_id:
            raise ValidationError(
                "Thiếu thông tin điều chuyển (student_id, to_class_id hoặc academic_year_id).")

        student = Student.query.get(student_id)
        if not student:
            raise NotFoundError("Không tìm thấy học sinh.")

        if student.is_deleted:
            raise BusinessRuleError(
                "Học sinh %s (%s) đã bị xoá mềm — không thể điều chuyển lớp. "
                "Hãy khôi phục hồ sơ trước."
                % (student.full_name, student.student_code)
            )

        target_class = ClassRepository.get_class_by_id(to_class_id)
        if not target_class:
            raise NotFoundError("Lớp học đích không tồn tại.")

        if target_class.academic_year_id != academic_year_id:
            raise BusinessRuleError(
                "Lớp học đích không thuộc năm học đang thao tác. "
                "Vui lòng chọn lớp cùng năm học với lớp hiện tại của học sinh.")

        current_enrollments = ClassEnrollment.query.filter(
            ClassEnrollment.student_id == student_id,
            ClassEnrollment.status == EnrollmentStatusEnum.DANG_HOC,
        ).all()
        current_enrollment = current_enrollments[0] if current_enrollments else None

        old_class_id = None
        old_class = None
        if current_enrollment:
            old_class_id = current_enrollment.class_id
            if old_class_id == to_class_id:
                raise BusinessRuleError("Học sinh đã ở trong lớp học này rồi.")
            old_class = ClassRepository.get_class_by_id(old_class_id)
        elif from_class_id:

            old_class_id = from_class_id
            old_class = ClassRepository.get_class_by_id(from_class_id)

        if old_class is not None and int(old_class.grade_id) != int(target_class.grade_id):
            old_grade = db.session.get(Grade, old_class.grade_id)
            new_grade = db.session.get(Grade, target_class.grade_id)
            raise BusinessRuleError(
                "Không thể chuyển học sinh từ %s (%s) sang %s (%s) — chuyển lớp "
                "chỉ được phép trong CÙNG khối. Nếu học sinh lên/xuống khối, "
                "vui lòng dùng luồng cập nhật hồ sơ học sinh."
                % (
                    old_class.class_name,
                    old_grade.grade_name if old_grade else old_class.grade_id,
                    target_class.class_name,
                    new_grade.grade_name if new_grade else target_class.grade_id,
                ),
                error="CROSS_GRADE_TRANSFER_NOT_ALLOWED",
            )

        max_size = get_max_class_size()
        target_size = ClassService._count_active_students(target_class.id)
        if target_size + 1 > max_size:
            raise ClassSizeExceededError(
                "Không thể điều chuyển! Lớp %s hiện có %d học sinh, thêm 1 học sinh "
                "sẽ vượt quá sĩ số tối đa cho phép (%d học sinh)!"
                % (target_class.class_name, target_size, max_size),
                current_size=target_size,
                max_size=max_size,
            )

        for enr in current_enrollments:
            enr.status = EnrollmentStatusEnum.DA_CHUYEN
            if transfer_reason:
                enr.transfer_note = transfer_reason

        new_enrollment = ClassEnrollment(
            student_id=student_id,
            class_id=to_class_id,
            academic_year_id=academic_year_id,
            enrollment_date=date.today(),
            status=EnrollmentStatusEnum.DANG_HOC,
            transfer_note=transfer_reason or None,
        )

        db.session.add(new_enrollment)
        db.session.flush()

        if old_class is not None:
            old_class.current_size = count_active_students(old_class.id)
        target_class.current_size = count_active_students(target_class.id)

        write_audit(actor_id, "TRANSFER_STUDENT", {
            "student_id": student.id,
            "student_code": student.student_code,
            "full_name": student.full_name,
            "from_class_id": old_class_id,
            "to_class_id": to_class_id,
            "from_class": old_class.class_name if old_class else None,
            "to_class": target_class.class_name,
            "from_class_new_size": old_class.current_size if old_class else 0,
            "to_class_new_size": target_class.current_size,
            "transfer_reason": transfer_reason or None,
            "academic_year_id": academic_year_id,
        })
        db.session.commit()

        from_class_new_size = old_class.current_size if old_class else 0
        return {
            "student_id": student.id,
            "student_code": student.student_code,
            "from_class_id": old_class_id,
            "to_class_id": to_class_id,
            "from_class": old_class.class_name if old_class else None,
            "to_class": target_class.class_name,
            "from_class_new_size": from_class_new_size,
            "to_class_new_size": target_class.current_size,
            "transfer_reason": transfer_reason,
            "academic_year_id": academic_year_id,
        }

    @staticmethod
    def _count_active_students(class_id):

        return count_active_students(class_id)

    @staticmethod
    def _get_current_academic_year_id():

        try:
            from studentapp.models.academic_year import AcademicYear

            ay = AcademicYear.query.filter_by(is_current=True).first()
            if ay is None:
                ay = AcademicYear.query.order_by(AcademicYear.id.desc()).first()
            return ay.id if ay else None
        except Exception:
            return None
