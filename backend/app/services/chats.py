from uuid import UUID
import logging

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import ChatSession
from app.models.message import Message, MessageRole

logger = logging.getLogger(__name__)


async def owned_chat(session: AsyncSession, chat_id: UUID, user_id: UUID) -> ChatSession:
    statement = select(ChatSession).where(ChatSession.id == chat_id, ChatSession.user_id == user_id)
    logger.info("owned_chat executing statement=%s", statement)
    chat = await session.scalar(statement)
    if chat is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")
    return chat


async def add_message(session: AsyncSession, chat: ChatSession, role: str, content: str) -> Message:
    logger.debug("add_message constructing session_id=%s role=%s content_length=%d", chat.id, role, len(content))
    message = Message(session_id=chat.id, role=MessageRole(role), content=content)
    session.add(message)
    await session.flush()
    logger.debug("add_message flushed message_id=%s session_id=%s", message.id, chat.id)
    return message
