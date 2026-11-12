"""CONTROLLER audit — SD15 tra cứu nhật ký hệ thống (JSON API cho Giáo vụ)."""
from flask import Blueprint, jsonify, request, Response

from studentapp.exceptions import AppError
from studentapp.extensions import db
from studentapp.models.audit_log import AuditLog
from studentapp.models.user import User
from studentapp.utils.decorators import admin_required

bp = Blueprint("audit", __name__, url_prefix="/api/v1/admin/audit-logs")


def _err(e: AppError):
    return jsonify({"error": e.error, "message": e.message}), e.status_code


def _ok(data=None, message="OK", status=200):
    return jsonify({"success": True, "message": message, "data": data}), status


def _serialize(log: AuditLog):
    user = db.session.get(User, log.user_id) if log.user_id else None
    return {
        "id": log.id,
        "user_id": log.user_id,
        "user_name": user.full_name if user else None,
        "action": log.action,
        "ip_address": log.ip_address,
        "details": log.details,
        "created_at": log.created_at.isoformat() if log.created_at else None,
    }


@bp.get("")
@admin_required
def list_logs():
    try:
        q = AuditLog.query
        action = request.args.get("action")
        if action not in (None, ""):
            q = q.filter_by(action=str(action).strip().upper())
        try:
            page = max(1, int(request.args.get("page", 1)))
        except (TypeError, ValueError):
            page = 1
        try:
            limit = min(100, max(1, int(request.args.get("limit", 20))))
        except (TypeError, ValueError):
            limit = 20
        total = q.count()
        rows = (q.order_by(AuditLog.id.desc())
                .offset((page - 1) * limit).limit(limit).all())
        return _ok({"total": total, "page": page, "limit": limit,
                    "logs": [_serialize(r) for r in rows]},
                   "Nhật ký hệ thống.")
    except AppError as e:
        return _err(e)


@bp.get("/export")
@admin_required
def export_logs():
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Font
        import io

        q = AuditLog.query
        action = request.args.get("action")
        if action not in (None, ""):
            q = q.filter_by(action=str(action).strip().upper())
        rows = q.order_by(AuditLog.id.desc()).limit(1000).all()
        wb = Workbook()
        ws = wb.active
        ws.title = "Audit logs"
        ws.append(["ID", "User", "Action", "IP", "Created at"])
        for r in rows:
            s = _serialize(r)
            ws.append([s["id"], s["user_name"], s["action"],
                       s["ip_address"], s["created_at"]])
        for row in ws.iter_rows():
            for cell in row:
                cell.alignment = Alignment(horizontal="center")
        ws["A1"].font = Font(bold=True)
        for col, width in zip("ABCDE", (8, 24, 26, 16, 24)):
            ws.column_dimensions[col].width = width
        buf = io.BytesIO()
        wb.save(buf)
        return Response(
            buf.getvalue(),
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=audit-logs.xlsx"})
    except AppError as e:
        return _err(e)


@bp.get("/<int:log_id>")
@admin_required
def detail(log_id):
    try:
        from studentapp.exceptions import NotFoundError

        try:
            lid = int(log_id)
        except (TypeError, ValueError):
            raise NotFoundError("Không tìm thấy vết kiểm toán.")
        row = db.session.get(AuditLog, lid)
        if row is None:
            raise NotFoundError("Không tìm thấy vết kiểm toán.")
        return _ok(_serialize(row), "Chi tiết nhật ký.")
    except AppError as e:
        return _err(e)
