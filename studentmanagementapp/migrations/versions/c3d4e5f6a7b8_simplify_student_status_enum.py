from alembic import op
import sqlalchemy as sa

revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None

_TABLE = "students"
_COLUMN = "status"

_OLD_VALUES = ("DANG_HOC", "THOI_HOC", "CHUYEN_TRUONG", "TOT_NGHIEP")
_NEW_VALUES = ("DANG_HOC", "THOI_HOC")

def _current_enum_values(conn):

    try:
        return {
            row[0]
            for row in conn.exec_driver_sql(
                "SELECT COLUMN_TYPE FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s "
                "AND COLUMN_NAME = %s",
                (_TABLE, _COLUMN),
            )
        }
    except Exception:
        return None

def _is_mysql(conn):
    return conn.dialect.name == "mysql"

def upgrade():

    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if _COLUMN not in {c["name"] for c in inspector.get_columns(_TABLE)}:
        return

    if _is_mysql(conn):

        conn.exec_driver_sql(
            "UPDATE `{t}` SET `{c}` = 'THOI_HOC' "
            "WHERE `{c}` IN ('CHUYEN_TRUONG', 'TOT_NGHIEP')".format(t=_TABLE, c=_COLUMN)
        )
        op.alter_column(
            _TABLE,
            _COLUMN,
            existing_type=sa.Enum(*_OLD_VALUES, name="studentstatusenum"),
            type_=sa.Enum(*_NEW_VALUES, name="studentstatusenum"),
            existing_nullable=False,
        )
        return

    op.execute(
        sa.text(
            "UPDATE {t} SET {c} = 'THOI_HOC' "
            "WHERE {c} IN ('CHUYEN_TRUONG', 'TOT_NGHIEP')".format(t=_TABLE, c=_COLUMN)
        )
    )
    with op.batch_alter_table(_TABLE) as batch_op:
        batch_op.alter_column(
            _COLUMN,
            existing_type=sa.Enum(*_OLD_VALUES, name="studentstatusenum"),
            type_=sa.Enum(*_NEW_VALUES, name="studentstatusenum"),
            existing_nullable=False,
        )

def downgrade():

    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if _COLUMN not in {c["name"] for c in inspector.get_columns(_TABLE)}:
        return

    if _is_mysql(conn):
        op.alter_column(
            _TABLE,
            _COLUMN,
            existing_type=sa.Enum(*_NEW_VALUES, name="studentstatusenum"),
            type_=sa.Enum(*_OLD_VALUES, name="studentstatusenum"),
            existing_nullable=False,
        )
        return

    op.execute(
        sa.text(
            "UPDATE {t} SET {c} = 'THOI_HOC' "
            "WHERE {c} = 'THOI_HOC'".format(t=_TABLE, c=_COLUMN)
        )
    )
    with op.batch_alter_table(_TABLE) as batch_op:
        batch_op.alter_column(
            _COLUMN,
            existing_type=sa.Enum(*_NEW_VALUES, name="studentstatusenum"),
            type_=sa.Enum(*_OLD_VALUES, name="studentstatusenum"),
            existing_nullable=False,
        )
