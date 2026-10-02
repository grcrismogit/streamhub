from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, DbSession
from app.core.security import hash_password
from app.models import User, Video
from app.schemas import UserCreate, UserPrivate, UserPublic

router = APIRouter(prefix="/users", tags=["Usuarios"])


def count_videos(db: Session, user_id: int) -> int:
    return db.scalar(select(func.count()).select_from(Video).where(Video.user_id == user_id)) or 0


def to_private(db: Session, user: User) -> UserPrivate:
    return UserPrivate(
        id=user.id,
        name=user.name,
        email=user.email,
        created_at=user.created_at,
        video_count=count_videos(db, user.id),
    )


@router.post(
    "",
    response_model=UserPrivate,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar un usuario",
    responses={409: {"description": "El correo ya está registrado"}},
)
def create_user(payload: UserCreate, db: DbSession) -> UserPrivate:
    email = payload.email.lower()
    if db.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "El correo ya está registrado")

    user = User(name=payload.name, email=email, password_hash=hash_password(payload.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:  # carrera: dos registros simultáneos con el mismo correo
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "El correo ya está registrado") from None
    db.refresh(user)
    return to_private(db, user)


@router.get("/me", response_model=UserPrivate, summary="Mi perfil (requiere token)")
def read_me(current_user: CurrentUser, db: DbSession) -> UserPrivate:
    return to_private(db, current_user)


@router.get(
    "/{user_id}",
    response_model=UserPublic,
    summary="Perfil público de un usuario",
    responses={404: {"description": "Usuario no encontrado"}},
)
def read_user(user_id: int, db: DbSession) -> UserPublic:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado")
    return UserPublic(
        id=user.id, name=user.name, created_at=user.created_at, video_count=count_videos(db, user.id)
    )
