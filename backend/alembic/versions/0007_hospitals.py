"""Add normalized hospital directory records."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0007_hospitals"
down_revision = "0006_language_memory"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "hospitals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=240), nullable=False),
        sa.Column("city", sa.String(length=120), nullable=False),
        sa.Column("specialization", sa.String(length=120), nullable=False),
        sa.Column("address", sa.Text(), nullable=False),
        sa.Column("phone", sa.String(length=80), nullable=True),
        sa.Column("website", sa.String(length=500), nullable=True),
        sa.Column("rating", sa.Float(), nullable=True),
    )
    op.create_index("ix_hospitals_city", "hospitals", ["city"])
    op.create_index("ix_hospitals_specialization", "hospitals", ["specialization"])
    op.create_index("ix_hospitals_city_specialization", "hospitals", ["city", "specialization"])
    op.create_unique_constraint("uq_hospitals_name_city_specialty", "hospitals", ["name", "city", "specialization"])


def downgrade() -> None:
    op.drop_constraint("uq_hospitals_name_city_specialty", "hospitals", type_="unique")
    op.drop_index("ix_hospitals_city_specialization", table_name="hospitals")
    op.drop_index("ix_hospitals_specialization", table_name="hospitals")
    op.drop_index("ix_hospitals_city", table_name="hospitals")
    op.drop_table("hospitals")
