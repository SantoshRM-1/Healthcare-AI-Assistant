from collections.abc import AsyncIterator
import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

logger = logging.getLogger(__name__)

engine = create_async_engine(settings.database_url, pool_pre_ping=True, pool_size=10, max_overflow=20)
SessionFactory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionFactory() as session:
        logger.debug("database session opened active=%s", session.is_active)
        try:
            yield session
        except Exception:
            logger.exception(
                "database request failed active=%s in_transaction=%s",
                session.is_active,
                session.in_transaction(),
            )
            if session.in_transaction():
                await session.rollback()
            raise
        finally:
            logger.debug(
                "database session closing active=%s in_transaction=%s",
                session.is_active,
                session.in_transaction(),
            )
