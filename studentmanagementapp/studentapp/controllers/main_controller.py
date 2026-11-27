from flask import Blueprint, jsonify

from studentapp.services.class_service import ClassService
from studentapp.utils.decorators import login_required_any

bp = Blueprint("catalog_classes", __name__, url_prefix="/api/v1")

@bp.get("/classes/<int:class_id>/students")
@login_required_any
def list_class_students(class_id):

    students = ClassService.get_students_in_class(class_id)
    return jsonify({"success": True, "data": students}), 200
