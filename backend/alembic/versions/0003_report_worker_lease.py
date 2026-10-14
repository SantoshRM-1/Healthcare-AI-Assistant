"""Add processing lease timestamp for recoverable OCR work."""
from alembic import op
import sqlalchemy as sa

revision = "0003_report_lease"
down_revision = "0002_reports"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("uploaded_reports", sa.Column("processing_started_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("uploaded_reports", "processing_started_at")
