"""Shared JSON helpers."""
from flask import jsonify


def ok(data=None, message="OK", status=200):
    return jsonify({"success": True, "message": message, "data": data}), status


def err(error="BAD_REQUEST", message="Lỗi.", status=400):
    return jsonify({"error": error, "message": message}), status


def fail(message="Lỗi.", status=400):
    return err("BAD_REQUEST", message, status)


def paginated(items, total, page, limit, message="OK"):
    return jsonify({
        "success": True,
        "message": message,
        "data": {"total": total, "page": page, "limit": limit, "data": items},
    }), 200
