import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Principal
from app.models.user import User

logger = logging.getLogger(__name__)


async def get_or_create_user(session: AsyncSession, principal: Principal) -> User:
    statement = select(User).where(User.clerk_id == principal.clerk_id)
    logger.info(
        "get_or_create_user executing statement=%s clerk_user_id=%s in_transaction=%s",
        statement,
        principal.clerk_id,
        session.in_transaction(),
    )
    user = await session.scalar(statement)
    if user is None:
        logger.info("get_or_create_user no row found; creating clerk_user_id=%s", principal.clerk_id)
        user = User(clerk_id=principal.clerk_id, email=principal.email, full_name=principal.full_name)
        session.add(user)
    else:
        # Clerk claims may not contain profile fields; don't overwrite stored values with null.
        if principal.email:
            user.email = principal.email
        if principal.full_name:
            user.full_name = principal.full_name
    await session.flush()
    logger.info(
        "get_or_create_user flushed clerk_user_id=%s db_user_id=%s session_active=%s in_transaction=%s",
        principal.clerk_id,
        user.id,
        session.is_active,
        session.in_transaction(),
    )
    return user
