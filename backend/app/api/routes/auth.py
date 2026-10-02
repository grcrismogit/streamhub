from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select

from app.api.deps import DbSession
from app.api.routes.users import to_private
from app.core.config import get_settings
from app.core.security import DUMMY_HASH, create_access_token, verify_password
from app.models import User
from app.schemas import Token

router = APIRouter(tags=["Autenticación"])


@router.post(
    "/login",
    response_model=Token,
    summary="Iniciar sesión",
    description=(
        "Formulario OAuth2 estándar (`application/x-www-form-urlencoded`). "
        "En el campo **username** se envía el **correo**."
    ),
    responses={401: {"description": "Credenciales inválidas"}},
)
def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], db: DbSession) -> Token:
    user = db.scalar(select(User).where(User.email == form.username.strip().lower()))

    # Siempre verificamos un hash (real o señuelo) para no revelar si el correo existe.
    valid = verify_password(form.password, user.password_hash if user else DUMMY_HASH)
    if user is None or not valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return Token(
        access_token=create_access_token(user.id),
        expires_in=get_settings().access_token_expire_minutes * 60,
        user=to_private(db, user),
    )
