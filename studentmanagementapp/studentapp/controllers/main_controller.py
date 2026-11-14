"""CONTROLLER view — Giao diện HTML (Login, Dashboard, v.v.)."""
from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_user
from studentapp.repositories import user_repository

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