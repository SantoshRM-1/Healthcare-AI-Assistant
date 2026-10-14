"""Persist vector indexing metadata, report summaries and chat citations."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0004_ai_rag"
down_revision = "0003_report_lease"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("uploaded_reports", sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("uploaded_reports", sa.Column("summary_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("uploaded_reports", sa.Column("summary_generated_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("messages", sa.Column("citations", postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column("messages", "citations")
    op.drop_column("uploaded_reports", "summary_generated_at")
    op.drop_column("uploaded_reports", "summary_data")
    op.drop_column("uploaded_reports", "indexed_at")
