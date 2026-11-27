import os
import re
import uuid
from datetime import datetime

from studentapp.exceptions import ValidationError

MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024

ALLOWED_ATTACHMENT_TYPES = {
    "image/png": ("IMAGE", ".png"),
    "image/jpeg": ("IMAGE", ".jpg"),
    "image/webp": ("IMAGE", ".webp"),
    "application/pdf": ("PDF", ".pdf"),
}

_MAX_NAME_LEN = 200

_SAFE_CHARS = re.compile(r"[^A-Za-z0-9._-]+")

def _upload_root():

    from flask import current_app

    return current_app.config.get(
        "UPLOAD_FOLDER",
        os.path.join(current_app.root_path, "..", "uploads"),
    )

def _sanitize_filename(name):

    name = os.path.basename(str(name or "").strip())
    name = name.replace("\\", "/").split("/")[-1]

    name = "".join(ch for ch in name if ch.isprintable())
    stem, dot, ext = name.rpartition(".")
    if not dot:
        stem, ext = name, ""
    stem = _SAFE_CHARS.sub("_", stem).strip("._") or "file"
    ext = _SAFE_CHARS.sub("", ext)[:10]
    if len(stem) > _MAX_NAME_LEN:
        stem = stem[:_MAX_NAME_LEN]
    return f"{stem}.{ext}" if ext else stem

def _detect_extension(filename, mimetype):

    _kind, ext = ALLOWED_ATTACHMENT_TYPES.get((mimetype or "").lower(), (None, ""))
    if ext:
        return ext
    lowered = (filename or "").lower()
    for _mime, (_kind2, ext2) in ALLOWED_ATTACHMENT_TYPES.items():
        if lowered.endswith(ext2):
            return ext2
    return ""

def resolve_path(db_path):

    if not db_path:
        return None
    normalized = str(db_path).replace("\\", "/")
    if normalized.startswith("/") or ".." in normalized.split("/"):
        return None
    return os.path.join(_upload_root(), *normalized.split("/"))

def save_attachment(file_storage, teacher_id=None):

    if file_storage is None or not getattr(file_storage, "filename", ""):
        raise ValidationError(
            "Không tìm thấy file tải lên.",
            error="MISSING_FILE",
        )

    original_name = file_storage.filename
    mimetype = (file_storage.mimetype or "").lower()

    kind_and_ext = ALLOWED_ATTACHMENT_TYPES.get(mimetype)
    if kind_and_ext is None:

        ext = _detect_extension(original_name, mimetype)
        matched = next(
            (v for v in ALLOWED_ATTACHMENT_TYPES.values() if v[1] == ext), None
        )
        if matched is None:
            raise ValidationError(
                "Định dạng file không hợp lệ. Chỉ chấp nhận ảnh (PNG, JPEG, WEBP) "
                "hoặc file PDF.",
                error="INVALID_ATTACHMENT_TYPE",
            )
        kind, ext = matched
    else:
        kind, ext = kind_and_ext

    safe_name = _sanitize_filename(original_name)
    stem = safe_name.rpartition(".")[0] or "file"

    now = datetime.now()
    rel_dir = os.path.join(
        "score_requests", str(now.year), f"{now.month:02d}"
    )
    unique = f"{stem}_{uuid.uuid4().hex[:8]}{ext}"
    rel_path = os.path.join(rel_dir, unique)

    db_path = rel_path.replace(os.sep, "/")

    abs_dir = os.path.join(_upload_root(), rel_dir)
    os.makedirs(abs_dir, exist_ok=True)
    abs_path = os.path.join(_upload_root(), rel_path)

    file_storage.save(abs_path)

    size = os.path.getsize(abs_path)
    if size > MAX_ATTACHMENT_BYTES:

        try:
            os.remove(abs_path)
        except OSError:
            pass
        raise ValidationError(
            "Kích thước file vượt quá giới hạn 10 MB.",
            error="FILE_TOO_LARGE",
        )

    return {
        "attachment_path": db_path,
        "attachment_type": kind,
        "attachment_name": safe_name[:_MAX_NAME_LEN],
        "size": size,
    }
