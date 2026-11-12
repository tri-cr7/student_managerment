"""CONTROLLER report — SD20 báo cáo tổng kết môn (Yêu cầu 4) + export Excel/PDF."""
from flask import Blueprint, jsonify, request, Response
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request

from studentapp.exceptions import AppError
from studentapp.services import report_service
from studentapp.utils.decorators import admin_required

bp = Blueprint("report", __name__, url_prefix="/api/v1/reports")


def _err(e: AppError):
    return jsonify({"error": e.error, "message": e.message}), e.status_code


def _ok(data=None, message="OK", status=200):
    return jsonify({"success": True, "message": message, "data": data}), status


def _need(scope: dict, key: str):
    val = scope.get(key)
    if val in (None, ""):
        from studentapp.exceptions import ValidationError
        raise ValidationError(f"Thiếu query param {key}.")
    return val


@bp.get("/subject-summary")
@admin_required
def subject_summary():
    try:
        data = report_service.subject_summary(
            _need(request.args, "subject_id"), _need(request.args, "semester_id"))
        return _ok(data, "Báo cáo tổng kết môn học.")
    except AppError as e:
        return _err(e)


@bp.get("/chart-data")
@admin_required
def chart_data():
    try:
        data = report_service.chart_data(
            _need(request.args, "subject_id"), _need(request.args, "semester_id"),
            request.args.get("chart_type", "bar"))
        return _ok(data, "Dữ liệu biểu đồ Chart.js.")
    except AppError as e:
        return _err(e)


@bp.get("/grade-summary")
@admin_required
def grade_summary():
    try:
        data = report_service.grade_summary(
            _need(request.args, "grade_id"), _need(request.args, "semester_id"))
        return _ok(data, "Thống kê tổng kết theo khối.")
    except AppError as e:
        return _err(e)


@bp.get("/export/excel")
@admin_required
def export_excel():
    try:
        payload, data = report_service.build_excel(
            _need(request.args, "subject_id"), _need(request.args, "semester_id"))
        name = f"bao-cao-{data['subject_id']}-{data['semester_id']}.xlsx"
        return Response(
            payload,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={name}"})
    except AppError as e:
        return _err(e)


@bp.get("/export/pdf")
@admin_required
def export_pdf():
    try:
        payload, data = report_service.build_pdf(
            _need(request.args, "subject_id"), _need(request.args, "semester_id"))
        name = f"bao-cao-{data['subject_id']}-{data['semester_id']}.pdf"
        return Response(
            payload, mimetype="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={name}"})
    except AppError as e:
        return _err(e)
