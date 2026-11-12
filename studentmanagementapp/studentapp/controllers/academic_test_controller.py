"""Trang test thủ công cho Giáo vụ — GET /academic/test (không ảnh hưởng API)."""
from flask import Blueprint, render_template

bp = Blueprint("academic_test", __name__)


@bp.get("/academic/test")
def academic_test_page():
    return render_template("academic_test.html")
