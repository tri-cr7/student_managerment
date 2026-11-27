from alembic import op
import sqlalchemy as sa

revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None

_TABLE = "users"
_COLUMN = "locked_at"

def upgrade():

    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing = {c["name"] for c in inspector.get_columns(_TABLE)}

    if _COLUMN in existing:
        return

    op.add_column(
        _TABLE,
        sa.Column(_COLUMN, sa.TIMESTAMP(), nullable=True),
    )

    op.execute(
        sa.text(
            f"UPDATE {_TABLE} SET {_COLUMN} = CURRENT_TIMESTAMP "
            f"WHERE is_locked = 1 AND {_COLUMN} IS NULL"
        )
    )

def downgrade():

    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing = {c["name"] for c in inspector.get_columns(_TABLE)}

    if _COLUMN in existing:
        op.drop_column(_TABLE, _COLUMN)
