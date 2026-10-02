from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import CurrentUser, DbSession
from app.models import Comment, Video
from app.schemas import CommentCreate, CommentRead

router = APIRouter(prefix="/videos/{video_id}/comments", tags=["Comentarios"])


def ensure_video_exists(db: Session, video_id: int) -> None:
    if db.get(Video, video_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Video no encontrado")


@router.post(
    "",
    response_model=CommentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Comentar un video (requiere token)",
)
def create_comment(
    video_id: int, payload: CommentCreate, current_user: CurrentUser, db: DbSession
) -> Comment:
    ensure_video_exists(db, video_id)
    comment = Comment(content=payload.content, user_id=current_user.id, video_id=video_id)
    db.add(comment)
    db.commit()
    db.refresh(comment, attribute_names=["author", "created_at"])
    return comment


@router.get("", response_model=list[CommentRead], summary="Comentarios de un video (más recientes primero)")
def list_comments(
    video_id: int,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[Comment]:
    ensure_video_exists(db, video_id)
    return list(
        db.scalars(
            select(Comment)
            .options(selectinload(Comment.author))
            .where(Comment.video_id == video_id)
            .order_by(Comment.created_at.desc(), Comment.id.desc())
            .limit(limit)
            .offset(offset)
        ).all()
    )
