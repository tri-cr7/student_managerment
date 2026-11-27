from alembic import op
import sqlalchemy as sa

revision = "a1b2c3d4e5f6"
down_revision = "2964912fd9ca"
branch_labels = None
depends_on = None

_TABLE = "score_change_requests"
_COLUMN = "approval_note"

def upgrade():

    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing = {c["name"] for c in inspector.get_columns(_TABLE)}

    if _COLUMN in existing:
        return

    op.add_column(
        _TABLE,
        sa.Column(_COLUMN, sa.String(length=500), nullable=True),
    )

def downgrade():

    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing = {c["name"] for c in inspector.get_columns(_TABLE)}

    if _COLUMN in existing:
        op.drop_column(_TABLE, _COLUMN)
