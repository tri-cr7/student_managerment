"""SERVICE gửi mail — SD17."""
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from flask import current_app

log = logging.getLogger(__name__)


def _cfg(key, default=None):
    try:
        return current_app.config.get(key, default)
    except Exception:
        return default


def _send_smtp(to_email: str, subject: str, html_body: str, text_body: str = "") -> str:
    server = _cfg("MAIL_SERVER", "")
    username = _cfg("MAIL_USERNAME", "")
    password = _cfg("MAIL_PASSWORD", "")
    if not server or not username or not password:
        print(f"\n===== [MAIL-DEV] To: {to_email} | {subject} =====\n{text_body}\n====================================\n")
        log.info("[MAIL-DEV] to=%s subject=%s", to_email, subject)
        return "LOGGED"
    port = int(_cfg("MAIL_PORT", 587) or 587)
    use_tls = bool(_cfg("MAIL_USE_TLS", True))
    sender = _cfg("MAIL_DEFAULT_SENDER") or username
    msg = MIMEMultipart("alternative")
    msg["From"] = sender
    msg["To"] = to_email
    msg["Subject"] = subject
    if text_body:
        msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))
    try:
        with smtplib.SMTP(server, port, timeout=15) as s:
            if use_tls:
                s.starttls()
            s.login(username, password)
            s.sendmail(sender, [to_email], msg.as_string())
        return "SUCCESS"
    except Exception as e:
        log.warning("Gửi mail thất bại to=%s: %s", to_email, e)
        return "FAILED"


ACCOUNT_MAIL_SUBJECT = "[StudentApp] Thông tin tài khoản đăng nhập của bạn"


def account_body(full_name: str, username: str, temp_password: str, role: str):
    text = (
        f"Xin chào {full_name},\n\n"
        f"Giáo vụ đã cấp cho bạn tài khoản hệ thống quản lý sinh viên:\n"
        f"- Tên đăng nhập: {username}\n"
        f"- Mật khẩu tạm thời: {temp_password}\n"
        f"- Vai trò: {role}\n\n"
        f"Vui lòng đăng nhập vào hệ thống\n"
        f"và ĐỔI MẬT KHẨU NGAY ở lần đăng nhập đầu tiên.\n\n"
        f"Trân trọng,\nPhòng Giáo vụ"
    )
    html = (
        f"<p>Xin chào <b>{full_name}</b>,</p>"
        f"<p>Giáo vụ đã cấp cho bạn tài khoản hệ thống quản lý sinh viên:</p>"
        f"<ul><li>Tên đăng nhập: <b>{username}</b></li>"
        f"<li>Mật khẩu tạm thời: <b>{temp_password}</b></li>"
        f"<li>Vai trò: <b>{role}</b></li></ul>"
        f"<p>Vui lòng đăng nhập vào hệ thống và <b>ĐỔI MẬT KHẨU NGAY</b> ở lần đầu tiên.</p>"
        f"<p>Trân trọng,<br/>Phòng Giáo vụ</p>"
    )
    return html, text


def send_account_email(to_email: str, full_name: str, username: str, temp_password: str, role: str) -> str:
    html, text = account_body(full_name, username, temp_password, role)
    return _send_smtp(to_email, ACCOUNT_MAIL_SUBJECT, html, text)


PASSWORD_CHANGED_SUBJECT = "[StudentApp] Mật khẩu của bạn vừa được thay đổi"


def password_changed_body(full_name: str, username: str, when_str: str | None = None, ip: str | None = None):
    when_str = when_str or ""
    ip = ip or "không rõ"
    text = (
        f"Xin chào {full_name},\n\n"
        f"Mật khẩu của tài khoản ({username}) vừa được thay đổi thành công"
        f"{f' lúc {when_str}' if when_str else ''} (IP: {ip}).\n\n"
        f"Nếu KHÔNG phải bạn thực hiện, hãy liên hệ ngay Phòng Giáo vụ "
        f"để được khóa và cấp lại tài khoản!\n\n"
        f"Trân trọng,\nPhòng Giáo vụ"
    )
    html = (
        f"<p>Xin chào <b>{full_name}</b>,</p>"
        f"<p>Mật khẩu của tài khoản (<b>{username}</b>) vừa được thay đổi thành công"
        f"{f' lúc <b>{when_str}</b>' if when_str else ''} (IP: <b>{ip}</b>).</p>"
        f"<p style=\"color:#c62828;\"><b>Nếu KHÔNG phải bạn thực hiện, "
        f"hãy liên hệ ngay Phòng Giáo vụ để được khóa và cấp lại tài khoản!</b></p>"
        f"<p>Trân trọng,<br/>Phòng Giáo vụ</p>"
    )
    return html, text


def send_password_changed_email(
    to_email: str, full_name: str, username: str, when_str: str | None = None, ip: str | None = None
) -> str:
    html, text = password_changed_body(full_name, username, when_str, ip)
    return _send_smtp(to_email, PASSWORD_CHANGED_SUBJECT, html, text)


OTP_SUBJECT = "[StudentApp] Mã OTP đổi/quên mật khẩu của bạn"


def otp_body(full_name: str, username: str, code: str, expire_minutes: int = 5, action: str = "đặt lại mật khẩu"):
    text = (
        f"Xin chào {full_name},\n\n"
        f"Bạn (tài khoản {username}) vừa yêu cầu {action}.\n"
        f"Mã OTP 6 số của bạn (hết hạn sau {expire_minutes} phút, 1 lần dùng):\n\n"
        f"{code}\n\n"
        f"Nhập mã này để xác nhận. Nếu KHÔNG phải bạn, hãy bỏ qua email này "
        f"và liên hệ ngay Phòng Giáo vụ!\n\n"
        f"Trân trọng,\nPhòng Giáo vụ"
    )
    html = (
        f"<p>Xin chào <b>{full_name}</b>,</p>"
        f"<p>Bạn (tài khoản <b>{username}</b>) vừa yêu cầu {action}.</p>"
        f"<p>Mã OTP 6 số (hết hạn sau <b>{expire_minutes} phút</b>, 1 lần dùng):</p>"
        f"<p style=\"font-size:28px;letter-spacing:8px;background:#f5f5f5;padding:14px;"
        f"border-radius:8px;text-align:center;\"><b>{code}</b></p>"
        f"<p style=\"color:#c62828;\"><b>Nếu KHÔNG phải bạn, hãy bỏ qua email này "
        f"và liên hệ ngay Phòng Giáo vụ!</b></p>"
        f"<p>Trân trọng,<br/>Phòng Giáo vụ</p>"
    )
    return html, text


def send_otp_email(
    to_email: str, full_name: str, username: str, code: str, expire_minutes: int = 5, action: str = "đặt lại mật khẩu"
) -> str:
    html, text = otp_body(full_name, username, code, expire_minutes, action)
    return _send_smtp(to_email, OTP_SUBJECT, html, text)
