from studentapp.extensions import db
from studentapp.models.student import Student

def not_deleted(query):

    return query.filter(Student.is_deleted.is_(False))

def get_by_id(student_id):
    try:
        sid = int(student_id)
    except (TypeError, ValueError):
        return None
    return db.session.get(Student, sid)

def get_by_id_including_deleted(student_id):

    return get_by_id(student_id)

def get_by_code(student_code):
    code = (student_code or "").strip()
    if not code:
        return None
    return not_deleted(Student.query.filter_by(student_code=code)).first()

def search_students(keyword, student_ids=None, limit=20):

    try:
        lim = max(1, min(int(limit or 20), 50))
    except (TypeError, ValueError):
        lim = 20
    q = not_deleted(Student.query)
    if student_ids is not None:
        ids = [int(i) for i in (student_ids or [])]
        if not ids:
            return []
        q = q.filter(Student.id.in_(ids))
    kw = (keyword or "").strip()
    if kw:
        like = "%%%s%%" % kw
        q = q.filter(db.or_(Student.full_name.ilike(like), Student.student_code.ilike(like)))
    return q.order_by(Student.full_name).limit(lim).all()

def list_by_ids(student_ids):
    ids = [int(i) for i in (student_ids or [])]
    if not ids:
        return []
    return not_deleted(Student.query.filter(Student.id.in_(ids))).order_by(Student.id).all()
