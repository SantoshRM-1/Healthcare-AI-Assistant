from fastapi import APIRouter

from app.api.v1.routes import ai, chats, memory, platform, reports, users

router = APIRouter()
router.include_router(users.router, prefix="/users", tags=["users"])
router.include_router(chats.router, prefix="/chats", tags=["chats"])
router.include_router(reports.router, prefix="/reports", tags=["reports"])
router.include_router(ai.router, prefix="/ai", tags=["medical-ai"])
router.include_router(memory.router, prefix="/memory", tags=["session-memory"])
router.include_router(platform.ai_router, prefix="/ai", tags=["voice-and-hospitals"])
router.include_router(platform.share_router, prefix="/share", tags=["sharing"])
router.include_router(platform.export_router, prefix="/export", tags=["exports"])
