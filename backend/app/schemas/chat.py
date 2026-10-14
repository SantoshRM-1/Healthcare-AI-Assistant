from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class ChatCreate(BaseModel):
    title: str = Field(default="New conversation", min_length=1, max_length=200)


class ChatUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=200)


class ChatRead(ORMModel):
    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime


class MessageCreate(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=100_000)


class MessageRead(ORMModel):
    id: UUID
    session_id: UUID
    role: str
    content: str
    citations: list[dict] | None = None
    created_at: datetime
