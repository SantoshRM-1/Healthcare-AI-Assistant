"""Persist the current report processing stage."""
from alembic import op
import sqlalchemy as sa

revision = "0009_report_processing_stage"
down_revision = "0008_query_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("uploaded_reports", sa.Column("processing_stage", sa.String(length=40), server_default="queued", nullable=False))


def downgrade() -> None:
    op.drop_column("uploaded_reports", "processing_stage")
