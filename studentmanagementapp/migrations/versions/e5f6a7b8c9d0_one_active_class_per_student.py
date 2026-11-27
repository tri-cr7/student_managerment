from alembic import op
import sqlalchemy as sa

revision = "f6a7b8c9d0e1"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None

_TABLE = "class_enrollments"

_TRIG_INS = "trg_class_enrollments_one_active_ins"
_TRIG_UPD = "trg_class_enrollments_one_active_upd"

_MSG = ("VI PHAM QUY TAT: 1 hoc sinh chi duoc hoc 1 lop tai mot thoi diem "
        "(da ton tai enrollment DANG_HOC cho hoc sinh nay).")

def _is_mysql(conn):
    return conn.dialect.name == "mysql"

def _find_duplicates(conn):

    return conn.execute(sa.text(
        "SELECT student_id, COUNT(*) FROM class_enrollments "
        "WHERE status = 'DANG_HOC' GROUP BY student_id HAVING COUNT(*) > 1"
    )).fetchall()

def upgrade():

    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if _TABLE not in inspector.get_table_names():
        return

    dups = _find_duplicates(conn)
    if dups:
        raise RuntimeError(
            "Khong the them rang buoc '1 hoc sinh - 1 lop': con "
            f"{len(dups)} hoc sinh dang co >1 enrollment DANG_HOC: "
            f"{[r[0] for r in dups][:20]}. "
            "Hay don du lieu truoc (UPDATE class_enrollments SET status='DA_CHUYEN' "
            "cho cac ban ghi thua) roi chay lai migration."
        )

    if _is_mysql(conn):
        conn.execute(sa.text(f"DROP TRIGGER IF EXISTS `{_TRIG_INS}`"))
        conn.execute(sa.text(f"DROP TRIGGER IF EXISTS `{_TRIG_UPD}`"))

        conn.execute(sa.text(f"""
            CREATE TRIGGER `{_TRIG_INS}`
            BEFORE INSERT ON `{_TABLE}`
            FOR EACH ROW
            BEGIN
                IF NEW.status = 'DANG_HOC' THEN
                    IF (SELECT COUNT(*) FROM `{_TABLE}`
                        WHERE student_id = NEW.student_id
                          AND status = 'DANG_HOC') >= 1 THEN
                        SIGNAL SQLSTATE '45000'
                            SET MESSAGE_TEXT = '{_MSG}';
                    END IF;
                END IF;
            END
        """))

        conn.execute(sa.text(f"""
            CREATE TRIGGER `{_TRIG_UPD}`
            BEFORE UPDATE ON `{_TABLE}`
            FOR EACH ROW
            BEGIN
                IF NEW.status = 'DANG_HOC' AND OLD.status <> 'DANG_HOC' THEN
                    IF (SELECT COUNT(*) FROM `{_TABLE}`
                        WHERE student_id = NEW.student_id
                          AND status = 'DANG_HOC'
                          AND id <> NEW.id) >= 1 THEN
                        SIGNAL SQLSTATE '45000'
                            SET MESSAGE_TEXT = '{_MSG}';
                    END IF;
                END IF;
            END
        """))
    else:

        conn.execute(sa.text(f"DROP TRIGGER IF EXISTS `{_TRIG_INS}`"))
        conn.execute(sa.text(f"DROP TRIGGER IF EXISTS `{_TRIG_UPD}`"))

        conn.execute(sa.text(f"""
            CREATE TRIGGER `{_TRIG_INS}`
            BEFORE INSERT ON `{_TABLE}`
            WHEN NEW.status = 'DANG_HOC'
             AND (SELECT COUNT(*) FROM `{_TABLE}`
                  WHERE student_id = NEW.student_id AND status = 'DANG_HOC') >= 1
            BEGIN
                SELECT RAISE(ABORT, '{_MSG}');
            END
        """))

        conn.execute(sa.text(f"""
            CREATE TRIGGER `{_TRIG_UPD}`
            BEFORE UPDATE ON `{_TABLE}`
            WHEN NEW.status = 'DANG_HOC' AND OLD.status <> 'DANG_HOC'
             AND (SELECT COUNT(*) FROM `{_TABLE}`
                  WHERE student_id = NEW.student_id AND status = 'DANG_HOC'
                    AND id <> NEW.id) >= 1
            BEGIN
                SELECT RAISE(ABORT, '{_MSG}');
            END
        """))

def downgrade():

    conn = op.get_bind()
    for name in (_TRIG_INS, _TRIG_UPD):
        try:
            if _is_mysql(conn):
                conn.execute(sa.text(f"DROP TRIGGER IF EXISTS `{name}`"))
            else:
                conn.execute(sa.text(f"DROP TRIGGER IF EXISTS {name}"))
        except Exception:
            pass
