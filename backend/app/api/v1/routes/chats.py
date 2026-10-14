from uuid import UUID
import logging

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.auth import Principal, get_principal
from app.db.session import get_session
from app.models.chat import ChatSession
from app.models.message import Message
from app.models.uploaded_report import UploadedReport
from app.repositories.users import get_or_create_user
from app.schemas.chat import ChatCreate, ChatRead, ChatUpdate, MessageCreate, MessageRead
from app.services.chats import add_message, owned_chat
from app.services.report_storage import delete_report_asset
from app.services.vector_store import delete_report_vectors

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("", response_model=list[ChatRead])
async def list_chats(principal: Principal = Depends(get_principal), session: AsyncSession = Depends(get_session)) -> list[ChatRead]:
    user = await get_or_create_user(session, principal)
    result = await session.scalars(select(ChatSession).where(ChatSession.user_id == user.id).order_by(ChatSession.updated_at.desc()))
    await session.commit()
    return [ChatRead.model_validate(chat) for chat in result.all()]


@router.post("", response_model=ChatRead, status_code=status.HTTP_201_CREATED)
async def create_chat(payload: ChatCreate, principal: Principal = Depends(get_principal), session: AsyncSession = Depends(get_session)) -> ChatRead:
    stage = "start"
    logger.info(
        "create_chat request clerk_user_id=%s payload=%s db_session_active=%s in_transaction=%s",
        principal.clerk_id,
        payload.model_dump(),
        session.is_active,
        session.in_transaction(),
    )
    try:
        stage = "resolve_user"
        user = await get_or_create_user(session, principal)
        logger.info(
            "create_chat user resolved clerk_user_id=%s db_user_id=%s db_session_active=%s in_transaction=%s",
            principal.clerk_id,
            user.id,
            session.is_active,
            session.in_transaction(),
        )

        stage = "add_chat"
        chat = ChatSession(user_id=user.id, title=payload.title.strip())
        session.add(chat)
        logger.debug(
            "create_chat added to unit-of-work clerk_user_id=%s db_user_id=%s title_length=%d",
            principal.clerk_id,
            user.id,
            len(chat.title),
        )

        stage = "flush_chat_insert"
        await session.flush()
        logger.info(
            "create_chat insert flushed clerk_user_id=%s db_user_id=%s chat_id=%s",
            principal.clerk_id,
            user.id,
            chat.id,
        )

        stage = "refresh_chat"
        await session.refresh(chat)
        logger.debug(
            "create_chat refreshed chat_id=%s created_at=%s updated_at=%s",
            chat.id,
            chat.created_at,
            chat.updated_at,
        )

        stage = "serialize_response"
        response = ChatRead.model_validate(chat)
        logger.debug(
            "create_chat response validated chat_id=%s response_fields=%s",
            chat.id,
            list(response.model_fields_set),
        )

        stage = "commit"
        logger.info(
            "create_chat committing clerk_user_id=%s db_user_id=%s chat_id=%s in_transaction=%s",
            principal.clerk_id,
            user.id,
            chat.id,
            session.in_transaction(),
        )
        await session.commit()
        logger.info(
            "create_chat committed clerk_user_id=%s db_user_id=%s chat_id=%s",
            principal.clerk_id,
            user.id,
            chat.id,
        )
        return response
    except Exception:
        logger.exception(
            "create_chat failed stage=%s clerk_user_id=%s payload=%s db_session_active=%s in_transaction=%s",
            stage,
            principal.clerk_id,
            payload.model_dump(),
            session.is_active,
            session.in_transaction(),
        )
        if session.in_transaction():
            try:
                await session.rollback()
                logger.warning(
                    "create_chat rolled back stage=%s clerk_user_id=%s",
                    stage,
                    principal.clerk_id,
                )
            except Exception:
                logger.exception(
                    "create_chat rollback failed stage=%s clerk_user_id=%s",
                    stage,
                    principal.clerk_id,
                )
        raise


@router.get("/{chat_id}", response_model=ChatRead)
async def get_chat(chat_id: UUID, principal: Principal = Depends(get_principal), session: AsyncSession = Depends(get_session)) -> ChatRead:
    user = await get_or_create_user(session, principal)
    chat = await owned_chat(session, chat_id, user.id)
    await session.commit()
    return ChatRead.model_validate(chat)


@router.patch("/{chat_id}", response_model=ChatRead)
async def rename_chat(chat_id: UUID, payload: ChatUpdate, principal: Principal = Depends(get_principal), session: AsyncSession = Depends(get_session)) -> ChatRead:
    user = await get_or_create_user(session, principal)
    chat = await owned_chat(session, chat_id, user.id)
    chat.title = payload.title.strip()
    await session.commit()
    await session.refresh(chat)
    return ChatRead.model_validate(chat)


@router.delete("/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat(chat_id: UUID, principal: Principal = Depends(get_principal), session: AsyncSession = Depends(get_session)) -> Response:
    user = await get_or_create_user(session, principal)
    chat = await owned_chat(session, chat_id, user.id)
    reports = await session.scalars(select(UploadedReport).where(UploadedReport.session_id == chat.id, UploadedReport.user_id == user.id))
    for report in reports.all():
        previous_status, previous_indexed_at, previous_started_at = report.processing_status, report.indexed_at, report.processing_started_at
        report.processing_status = "deleting"
        await session.commit()
        try:
            await delete_report_vectors(report.id)
        except Exception as exc:
            logger.exception("Failed to clean report index %s while deleting chat %s", report.id, chat.id)
            report.processing_status = previous_status
            report.indexed_at = previous_indexed_at
            report.processing_started_at = previous_started_at
            await session.commit()
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "A report index could not be removed; retry chat deletion") from exc
        try:
            await delete_report_asset(report.cloudinary_public_id, report.cloudinary_resource_type)
        except Exception as exc:
            logger.exception("Failed to clean report file %s while deleting chat %s", report.id, chat.id)
            report.indexed_at = None
            report.processing_started_at = None
            report.processing_status = "pending"
            await session.commit()
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "A report could not be removed from storage; retry chat deletion") from exc
        await session.delete(report)
        await session.commit()
    await session.delete(chat)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{chat_id}/messages", response_model=list[MessageRead])
async def list_messages(chat_id: UUID, principal: Principal = Depends(get_principal), session: AsyncSession = Depends(get_session)) -> list[MessageRead]:
    user = await get_or_create_user(session, principal)
    chat = await owned_chat(session, chat_id, user.id)
    result = await session.scalars(select(Message).where(Message.session_id == chat.id).order_by(Message.created_at.asc()))
    await session.commit()
    return [MessageRead.model_validate(message) for message in result.all()]


@router.post("/{chat_id}/messages", response_model=MessageRead, status_code=status.HTTP_201_CREATED)
async def create_message(chat_id: UUID, payload: MessageCreate, principal: Principal = Depends(get_principal), session: AsyncSession = Depends(get_session)) -> MessageRead:
    user = await get_or_create_user(session, principal)
    chat = await owned_chat(session, chat_id, user.id)
    message = await add_message(session, chat, payload.role, payload.content)
    await session.commit()
    await session.refresh(message)
    return MessageRead.model_validate(message)
