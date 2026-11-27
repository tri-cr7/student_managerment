from flask import request

from studentapp.extensions import db
from studentapp.models.audit_log import AuditLog

_IP_MAX_LEN = 45

def client_ip() -> str | None:

    try:
        forwarded = request.headers.get("X-Forwarded-For", "")
        if forwarded:
            first = forwarded.split(",")[0].strip()
            if first:
                return first[:_IP_MAX_LEN]
        return (request.remote_addr or None)[:_IP_MAX_LEN]
    except Exception:

        return None

def write_audit(user_id, action: str, details=None, ip: str | None = None) -> AuditLog:

    try:
        uid = int(user_id) if user_id is not None else None
    except (TypeError, ValueError):
        uid = None

    if ip is None:
        ip = client_ip()

    log = AuditLog(user_id=uid, action=action, details=details or {}, ip_address=ip)
    db.session.add(log)
    return log
