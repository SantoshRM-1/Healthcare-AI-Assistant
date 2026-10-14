from functools import lru_cache

from google import genai
from google.genai import types

from app.core.config import settings


def require_gemini_key() -> str:
    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured")
    return settings.gemini_api_key


@lru_cache
def gemini_client() -> genai.Client:
    return genai.Client(
        api_key=require_gemini_key(),
        http_options=types.HttpOptions(timeout=settings.gemini_timeout_seconds * 1000),
    )


@lru_cache
def gemini_async_client():
    return gemini_client().aio
