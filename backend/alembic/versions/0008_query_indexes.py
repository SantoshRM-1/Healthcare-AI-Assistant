"""Add indexes for chat history and report worker query paths."""
from alembic import op

revision = "0008_query_indexes"
down_revision = "0007_hospitals"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_chat_sessions_user_updated", "chat_sessions", ["user_id", "updated_at"])
    op.create_index("ix_messages_session_created", "messages", ["session_id", "created_at"])
    op.create_index("ix_uploaded_reports_session_upload_date", "uploaded_reports", ["session_id", "upload_date"])
    op.create_index("ix_uploaded_reports_status_upload_date", "uploaded_reports", ["processing_status", "upload_date"])
    op.create_index("ix_recommendation_history_session_created", "recommendation_history", ["session_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_recommendation_history_session_created", table_name="recommendation_history")
    op.drop_index("ix_uploaded_reports_status_upload_date", table_name="uploaded_reports")
    op.drop_index("ix_uploaded_reports_session_upload_date", table_name="uploaded_reports")
    op.drop_index("ix_messages_session_created", table_name="messages")
    op.drop_index("ix_chat_sessions_user_updated", table_name="chat_sessions")
