"""Pure validators."""
import re

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^[0-9+\-\s]{7,15}$")

SPECIAL_CHARS = set("!@#$%^&*()-_=+[]{};:,.<>?/|~")


def is_email(v):
    return bool(v and EMAIL_RE.match(v.strip()))


def is_phone(v):
    return bool(v and PHONE_RE.match(v.strip()))


def is_score(v):
    try:
        return 0 <= float(v) <= 10
    except (TypeError, ValueError):
        return False


def is_strong_password(v: str) -> tuple[bool, str]:
    v = v or ""
    if len(v) < 8:
        return False, "Mật khẩu phải từ 8 ký tự trở lên."
    if not any(c.islower() for c in v):
        return False, "Mật khẩu phải có ít nhất 1 chữ thường (a-z)."
    if not any(c.isupper() for c in v):
        return False, "Mật khẩu phải có ít nhất 1 chữ HOA (A-Z)."
    if not any(c.isdigit() for c in v):
        return False, "Mật khẩu phải có ít nhất 1 chữ số (0-9)."
    if not any(c in SPECIAL_CHARS for c in v):
        return False, "Mật khẩu phải có ít nhất 1 ký tự đặc biệt (!@#$%...)."
    return True, "OK"
