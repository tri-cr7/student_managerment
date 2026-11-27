from alembic import op
import sqlalchemy as sa

revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None

_TABLE = "students"
_ENUM_NAME = "studentstatusenum"

_OLD_STATUS = ("DANG_HOC", "THOI_HOC")
_NEW_STATUS = ("DANG_HOC", "THOI_HOC", "BAO_LUU")

_NEW_COLUMNS = (
    ("is_deleted", sa.Boolean()),
    ("deleted_at", sa.TIMESTAMP()),
    ("deleted_by", sa.Integer()),
    ("deleted_reason", sa.String(500)),
)

_INDEX_NAME = "idx_students_deleted"

def _is_mysql(conn):
    return conn.dialect.name == "mysql"

def _existing_columns(conn):
    inspector = sa.inspect(conn)
    return {c["name"] for c in inspector.get_columns(_TABLE)}

def upgrade():

    conn = op.get_bind()
    existing = _existing_columns(conn)

    for name, col_type in _NEW_COLUMNS:
        if name in existing:
            continue
        kwargs = {"nullable": True}
        if name == "is_deleted":

            kwargs = {"nullable": False, "server_default": sa.text("0")}
        op.add_column(_TABLE, sa.Column(name, col_type, **kwargs))

    try:
        op.create_foreign_key(
            "fk_students_deleted_by", _TABLE, "users", ["deleted_by"], ["id"]
        )
    except Exception:
        pass

    indexes = {i["name"] for i in sa.inspect(conn).get_indexes(_TABLE)}
    if _INDEX_NAME not in indexes:
        op.create_index(_INDEX_NAME, _TABLE, ["is_deleted", "status"])

    if "status" in existing:
        _alter_status_enum(conn, _OLD_STATUS, _NEW_STATUS)

def _alter_status_enum(conn, old_values, new_values):

    if _is_mysql(conn):
        op.alter_column(
            _TABLE,
            "status",
            existing_type=sa.Enum(*old_values, name=_ENUM_NAME),
            type_=sa.Enum(*new_values, name=_ENUM_NAME),
            existing_nullable=False,
        )
        return

    with op.batch_alter_table(_TABLE) as batch_op:
        batch_op.alter_column(
            "status",
            existing_type=sa.Enum(*old_values, name=_ENUM_NAME),
            type_=sa.Enum(*new_values, name=_ENUM_NAME),
            existing_nullable=False,
        )

def downgrade():

    conn = op.get_bind()
    existing = _existing_columns(conn)

    if "status" in existing:

        conn.exec_driver_sql(
            "UPDATE `{t}` SET `status` = 'THOI_HOC' WHERE `status` = 'BAO_LUU'".format(
                t=_TABLE
            )
        )
        _alter_status_enum(conn, _NEW_STATUS, _OLD_STATUS)

    indexes = {i["name"] for i in sa.inspect(conn).get_indexes(_TABLE)}
    if _INDEX_NAME in indexes:
        op.drop_index(_INDEX_NAME, table_name=_TABLE)

    try:
        op.drop_constraint("fk_students_deleted_by", _TABLE, type_="foreignkey")
    except Exception:
        pass

    for name, _col_type in reversed(_NEW_COLUMNS):
        if name in _existing_columns(conn):
            op.drop_column(_TABLE, name)
