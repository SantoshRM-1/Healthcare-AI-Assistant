from functools import lru_cache
from urllib.parse import quote, unquote, urlsplit, urlunsplit

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "MedAssist AI API"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/medassist"
    clerk_issuer: str
    clerk_jwks_url: str
    cors_origins: list[str] = ["http://localhost:3000"]
    log_level: str = "INFO"
    cloudinary_cloud_name: str | None = None
    cloudinary_api_key: str | None = None
    cloudinary_api_secret: str | None = None
    report_max_size_mb: int = 20
    report_max_pdf_pages: int = 100
    gemini_api_key: str | None = None
    gemini_timeout_seconds: int = 60
    gemini_chat_model: str = "gemini-2.5-flash"
    gemini_embedding_model: str = "gemini-embedding-001"
    gemini_embedding_dimensions: int = 768
    chroma_persist_directory: str = "./.chroma"
    chroma_http_host: str | None = None
    chroma_http_port: int = 8000
    chroma_ssl: bool = False
    chroma_api_token: str | None = None
    rag_top_k: int = 8
    rag_max_cosine_distance: float = 0.65
    rag_chunk_size_chars: int = 1600
    rag_chunk_overlap_chars: int = 200
    report_processing_max_attempts: int = 5
    whisper_model_size: str = "small"
    whisper_beam_size: int = 3
    voice_max_size_mb: int = 20
    voice_max_duration_seconds: int = 180
    resend_api_key: str | None = None
    email_from: str | None = None
    email_reply_to: str | None = None
    hospital_max_results: int = 10
    export_font_path: str | None = None
    knowledge_admin_clerk_ids: str = ""
    knowledge_ingestion_max_attempts: int = 5
    knowledge_max_document_size_mb: int = 20
    knowledge_max_pdf_pages: int = 250
    knowledge_default_jurisdiction: str = "IN"

    @field_validator("database_url")
    @classmethod
    def use_async_driver(cls, value: str) -> str:
        if not value:
            return value

        normalized = value.strip()
        if normalized.startswith("postgresql://"):
            normalized = normalized.replace("postgresql://", "postgresql+asyncpg://", 1)

        if normalized.startswith("postgresql+asyncpg://"):
            parsed = urlsplit(normalized)
            username = parsed.username
            password = parsed.password
            host = parsed.hostname or "localhost"
            port = f":{parsed.port}" if parsed.port else ""

            userinfo = ""
            if username:
                userinfo += quote(unquote(username), safe="")
            if password is not None:
                userinfo += ":" + quote(unquote(password), safe="")
            if userinfo:
                netloc = f"{userinfo}@{host}{port}"
            else:
                netloc = f"{host}{port}"

            if parsed.path:
                path = parsed.path
            else:
                path = ""

            return urlunsplit((parsed.scheme, netloc, path, parsed.query, parsed.fragment))

        return normalized


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
