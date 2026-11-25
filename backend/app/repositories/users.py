import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Principal
from app.models.user import User

logger = logging.getLogger(__name__)


async def get_or_create_user(session: AsyncSession, principal: Principal) -> User:
    statement = select(User).where(User.clerk_id == principal.clerk_id)
    logger.debug("get_or_create_user executing query in_transaction=%s", session.in_transaction())
    user = await session.scalar(statement)
    if user is None:
        logger.info("get_or_create_user creating local user row")
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
        "get_or_create_user flushed local user row session_active=%s in_transaction=%s",
        session.is_active,
        session.in_transaction(),
    )
    return user
