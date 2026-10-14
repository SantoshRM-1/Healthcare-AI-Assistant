from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Principal, get_principal
from app.db.session import get_session
from app.repositories.users import get_or_create_user
from app.schemas.common import UserRead

router = APIRouter()


@router.get("/me", response_model=UserRead)
async def me(principal: Principal = Depends(get_principal), session: AsyncSession = Depends(get_session)) -> UserRead:
    user = await get_or_create_user(session, principal)
    await session.commit()
    return UserRead.model_validate(user)
