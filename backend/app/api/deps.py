"""Dependencias reutilizables: sesión de BD, usuario autenticado, storage."""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models import User
from app.services.storage import S3Storage, get_storage

# tokenUrl apunta a /login: así el botón "Authorize" de /docs funciona.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login", auto_error=False)

DbSession = Annotated[Session, Depends(get_db)]
Storage = Annotated[S3Storage, Depends(get_storage)]


def get_current_user(db: DbSession, token: Annotated[str | None, Depends(oauth2_scheme)]) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No autenticado o sesión expirada",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise unauthorized
    sub = decode_access_token(token)
    if sub is None or not sub.isdigit():
        raise unauthorized
    user = db.get(User, int(sub))
    if user is None:
        raise unauthorized
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
