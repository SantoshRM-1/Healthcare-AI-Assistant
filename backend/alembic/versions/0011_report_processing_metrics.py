"""Persist report pipeline progress metrics."""
from alembic import op
import sqlalchemy as sa

revision = "0011_report_processing_metrics"
down_revision = "0010_report_error_tracking"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for column in ("chunks_created", "embeddings_created", "vectors_saved"):
        op.add_column("uploaded_reports", sa.Column(column, sa.Integer(), server_default="0", nullable=False))


def downgrade() -> None:
    for column in ("vectors_saved", "embeddings_created", "chunks_created"):
        op.drop_column("uploaded_reports", column)
