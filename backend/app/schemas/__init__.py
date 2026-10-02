"""Esquemas Pydantic: definen exactamente qué entra y qué sale de la API.

Nunca se devuelve un modelo ORM "tal cual": así evitamos filtrar campos
sensibles como password_hash.
"""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints

# ---------- Usuarios ----------

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=80)]
Password = Annotated[str, StringConstraints(min_length=8, max_length=128)]


class UserCreate(BaseModel):
    name: Name
    email: EmailStr
    password: Password


class UserPublic(BaseModel):
    """Datos visibles para cualquier persona."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    created_at: datetime
    video_count: int = 0


class UserPrivate(UserPublic):
    """Datos que solo ve el propio usuario autenticado."""

    email: EmailStr


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"  # noqa: S105 (no es una contraseña)
    expires_in: int
    user: UserPrivate


# ---------- Videos ----------

# Se recortan espacios ANTES de validar la longitud ("   a" no es un título válido).
VideoTitle = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=120)]
VideoDescription = Annotated[str, StringConstraints(strip_whitespace=True, max_length=5000)]


class Owner(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class VideoRead(BaseModel):
    id: int
    title: str
    description: str
    video_url: str = Field(description="URL prefirmada temporal para reproducir el video")
    thumbnail_url: str = Field(description="URL prefirmada temporal de la miniatura")
    views: int
    user_id: int
    owner: Owner
    created_at: datetime
    updated_at: datetime


class VideoPage(BaseModel):
    items: list[VideoRead]
    total: int
    limit: int
    offset: int


class ViewCount(BaseModel):
    id: int
    views: int


# ---------- Comentarios ----------

CommentText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]


class CommentCreate(BaseModel):
    content: CommentText


class CommentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    content: str
    user_id: int
    video_id: int
    created_at: datetime
    author: Owner


class HealthStatus(BaseModel):
    status: str
    database: str
