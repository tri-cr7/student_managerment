from alembic import op
import sqlalchemy as sa

revision = '2964912fd9ca'
down_revision = None
branch_labels = None
depends_on = None

_CONSTRAINTS = (
    ("uq_students_email", "email"),
    ("uq_students_phone", "phone"),
    ("uq_students_citizen_id", "citizen_id"),
)

def upgrade():

    for _name, column in _CONSTRAINTS:
        _dedupe_column(column)

    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing = {i["name"] for i in inspector.get_indexes("students")}

    for name, column in _CONSTRAINTS:
        if name in existing:
            continue
        op.create_index(name, "students", [column], unique=True)

def downgrade():

    for name, _column in _CONSTRAINTS:
        op.drop_index(name, table_name="students")

def _dedupe_column(column):

    conn = op.get_bind()
    dup_rows = conn.execute(sa.text(
        "SELECT {col} FROM students WHERE {col} IS NOT NULL "
        "GROUP BY {col} HAVING COUNT(*) > 1".format(col=column)
    )).fetchall()
    if not dup_rows:
        return

    dup_values = [row[0] for row in dup_rows]
    conn.execute(sa.text(
        "UPDATE students SET {col} = NULL "
        "WHERE {col} IN :vals AND id NOT IN ("
        "  SELECT MIN(id) FROM students WHERE {col} IN :vals GROUP BY {col}"
        ")".format(col=column).bindparams(sa.bindparam("vals", expanding=True))
    ), {"vals": dup_values})
