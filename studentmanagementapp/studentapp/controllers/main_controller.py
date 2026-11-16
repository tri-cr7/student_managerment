"""CONTROLLER view — Giao diện HTML (Login, Dashboard, v.v.)."""
from flask import Blueprint, render_template, request, redirect, url_for, jsonify
from flask_login import login_user
from studentapp.repositories import user_repository
from studentapp.services.class_service import ClassService
from studentapp.utils.decorators import role_required

# Blueprint setup (you can place this in your view or auth controller)
bp = Blueprint("auth_ui", __name__, url_prefix="")


@bp.get('/login')
def login_page():
    """Hiển thị giao diện đăng nhập (GET)."""
    return render_template('login.html')


@bp.post('/login')
def login_action():
    """Xử lý thông tin gửi lên từ form đăng nhập (POST)."""
    username = request.form.get('username')
    password = request.form.get('password')

    # 1. Tìm user theo username
    user = user_repository.get_by_username(username)

    # 2. Kiểm tra mật khẩu và trạng thái tài khoản
    if user and user.check_password(password):
        if not user.is_active or user.is_locked:
            return render_template('login.html', err_msg="Tài khoản đã bị khóa hoặc chưa kích hoạt.")

        # 3. Đăng nhập thành công qua Flask-Login
        login_user(user)
        return redirect(url_for('staff.render_student_ui'))  # Chuyển hướng đến dashboard học sinh
    else:
        # 4. Đăng nhập thất bại, trả về form kèm thông báo lỗi
        return render_template('login.html', err_msg="Tên đăng nhập hoặc mật khẩu không chính xác!")

@bp.get("/classes-ui")
def classes_ui():
    """Hiển thị giao diện quản lý lớp học (HTML)."""
    return render_template("classes.html")

@bp.get("/classes/enroll-ui")
@role_required("STAFF")
def enroll_student_ui():
    """Hiển thị giao diện phân bổ học sinh vào lớp."""
    return render_template("add_student_to_class.html")

@bp.get("/grades")
def list_grades():
    """Item 22: Danh sách khối lớp (All)."""
    grades = ClassService.get_all_grades()
    return jsonify({"success": True, "data": [g.to_dict() for g in grades]}), 200

@bp.get("/grades/<int:grade_id>/classes")
def list_classes_by_grade(grade_id):
    """Item 23: Lấy danh sách lớp thuộc một khối (All)."""
    classes = ClassService.get_classes_by_grade(grade_id)
    return jsonify({"success": True, "data": [c.to_dict() for c in classes]}), 200

@bp.get("/classes")
def list_all_classes():
    """Item 24: Danh sách tất cả các lớp học (All)."""
    classes = ClassService.get_all_classes()
    return jsonify({"success": True, "data": [c.to_dict() for c in classes]}), 200

@bp.get("/classes/<int:class_id>")
def get_class_detail(class_id):
    """Item 25: Chi tiết thông tin lớp học và sĩ số hiện tại (All)."""
    details = ClassService.get_class_detail(class_id)
    return jsonify({"success": True, "data": details}), 200

@bp.get("/classes/<int:class_id>/students")
def list_class_students(class_id):
    """Item 29: Danh sách học sinh trong lớp học (All)."""
    students = ClassService.get_students_in_class(class_id)
    return jsonify({"success": True, "data": students}), 200