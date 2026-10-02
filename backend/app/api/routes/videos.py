from typing import Annotated, Literal

from fastapi import APIRouter, File, Form, HTTPException, Query, Response, UploadFile, status
from sqlalchemy import case, func, or_, select, update
from sqlalchemy.orm import Session, selectinload

from app.api.deps import CurrentUser, DbSession, Storage
from app.models import Video
from app.schemas import Owner, VideoDescription, VideoPage, VideoRead, VideoTitle, ViewCount
from app.services.storage import S3Storage, StoredObject, validate_thumbnail, validate_video

router = APIRouter(prefix="/videos", tags=["Videos"])


# ---------- Utilidades ----------


def to_read(video: Video, storage: S3Storage) -> VideoRead:
    """Convierte el modelo a respuesta generando URLs prefirmadas (los buckets son privados)."""
    s = storage.settings
    return VideoRead(
        id=video.id,
        title=video.title,
        description=video.description,
        video_url=storage.presigned_url(s.s3_videos_bucket, video.video_key),
        thumbnail_url=storage.presigned_url(s.s3_thumbnails_bucket, video.thumbnail_key),
        views=video.views,
        user_id=video.user_id,
        owner=Owner.model_validate(video.owner),
        created_at=video.created_at,
        updated_at=video.updated_at,
    )


def get_video_or_404(db: Session, video_id: int) -> Video:
    video = db.scalar(select(Video).options(selectinload(Video.owner)).where(Video.id == video_id))
    if video is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Video no encontrado")
    return video


def get_owned_video(db: Session, video_id: int, user_id: int) -> Video:
    video = get_video_or_404(db, video_id)
    if video.user_id != user_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo el propietario puede modificar este video")
    return video


def commit_or_cleanup(db: Session, storage: S3Storage, *uploaded: StoredObject) -> None:
    """Confirma la transacción; si falla, borra de S3 lo recién subido (sin archivos huérfanos)."""
    try:
        db.commit()
    except Exception:
        db.rollback()
        for obj in uploaded:
            storage.delete(obj.bucket, obj.key)
        raise


# ---------- Endpoints ----------


@router.post(
    "",
    response_model=VideoRead,
    status_code=status.HTTP_201_CREATED,
    summary="Publicar un video (MP4 + miniatura JPG/PNG)",
)
def create_video(
    current_user: CurrentUser,
    db: DbSession,
    storage: Storage,
    title: Annotated[VideoTitle, Form()],
    video: Annotated[UploadFile, File(description="Archivo MP4 (máx. 100 MB)")],
    thumbnail: Annotated[UploadFile, File(description="Miniatura JPG, JPEG o PNG (máx. 5 MB)")],
    description: Annotated[VideoDescription, Form()] = "",
) -> VideoRead:
    # 1) Validar ambos archivos ANTES de subir nada.
    video_type = validate_video(video)
    thumb_type = validate_thumbnail(thumbnail)

    # 2) Subir a S3 (si la miniatura falla, se borra el video ya subido).
    stored_video = storage.upload_video(video, current_user.id, video_type)
    try:
        stored_thumb = storage.upload_thumbnail(thumbnail, current_user.id, thumb_type)
    except HTTPException:
        storage.delete(stored_video.bucket, stored_video.key)
        raise

    # 3) Guardar los metadatos en RDS.
    entity = Video(
        title=title,
        description=description,
        video_url=stored_video.url,
        video_key=stored_video.key,
        thumbnail_url=stored_thumb.url,
        thumbnail_key=stored_thumb.key,
        user_id=current_user.id,
    )
    db.add(entity)
    commit_or_cleanup(db, storage, stored_video, stored_thumb)
    return to_read(get_video_or_404(db, entity.id), storage)


@router.get("", response_model=VideoPage, summary="Listar videos (catálogo, búsqueda, por usuario)")
def list_videos(
    db: DbSession,
    storage: Storage,
    q: Annotated[str | None, Query(max_length=100, description="Buscar en título/descripción")] = None,
    user_id: Annotated[int | None, Query(description="Filtrar por usuario publicador")] = None,
    sort: Literal["recent", "popular"] = "recent",
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> VideoPage:
    filters = []
    if q and q.strip():
        term = q.strip()
        # autoescape: "%" o "_" escritos por el usuario se buscan literalmente.
        filters.append(
            or_(
                Video.title.icontains(term, autoescape=True),
                Video.description.icontains(term, autoescape=True),
            )
        )
    if user_id is not None:
        filters.append(Video.user_id == user_id)

    total = db.scalar(select(func.count()).select_from(Video).where(*filters)) or 0
    order = (Video.views.desc(),) if sort == "popular" else (Video.created_at.desc(),)
    videos = db.scalars(
        select(Video)
        .options(selectinload(Video.owner))
        .where(*filters)
        .order_by(*order, Video.id.desc())  # id como desempate: paginación estable
        .limit(limit)
        .offset(offset)
    ).all()
    return VideoPage(items=[to_read(v, storage) for v in videos], total=total, limit=limit, offset=offset)


@router.get("/{video_id}", response_model=VideoRead, summary="Detalle de un video")
def read_video(video_id: int, db: DbSession, storage: Storage) -> VideoRead:
    return to_read(get_video_or_404(db, video_id), storage)


@router.get(
    "/{video_id}/recommended",
    response_model=list[VideoRead],
    summary="Videos recomendados",
    description="Prioriza videos del mismo autor y luego los más vistos. Excluye el video actual.",
)
def recommended_videos(
    video_id: int,
    db: DbSession,
    storage: Storage,
    limit: Annotated[int, Query(ge=1, le=20)] = 8,
) -> list[VideoRead]:
    current = get_video_or_404(db, video_id)
    same_author_first = case((Video.user_id == current.user_id, 0), else_=1)
    videos = db.scalars(
        select(Video)
        .options(selectinload(Video.owner))
        .where(Video.id != video_id)
        .order_by(same_author_first, Video.views.desc(), Video.created_at.desc(), Video.id.desc())
        .limit(limit)
    ).all()
    return [to_read(v, storage) for v in videos]


@router.post("/{video_id}/view", response_model=ViewCount, summary="Registrar una reproducción (+1 vista)")
def register_view(video_id: int, db: DbSession) -> ViewCount:
    # UPDATE atómico en la BD: no se pierden vistas con peticiones concurrentes.
    views = db.scalar(
        update(Video).where(Video.id == video_id).values(views=Video.views + 1).returning(Video.views)
    )
    if views is None:
        db.rollback()
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Video no encontrado")
    db.commit()
    return ViewCount(id=video_id, views=views)


@router.put("/{video_id}", response_model=VideoRead, summary="Actualizar título, descripción o miniatura")
def update_video(
    video_id: int,
    current_user: CurrentUser,
    db: DbSession,
    storage: Storage,
    title: Annotated[VideoTitle | None, Form()] = None,
    description: Annotated[VideoDescription | None, Form()] = None,
    thumbnail: Annotated[UploadFile | None, File(description="Nueva miniatura (opcional)")] = None,
) -> VideoRead:
    video = get_owned_video(db, video_id, current_user.id)
    if title is not None:
        video.title = title
    if description is not None:
        video.description = description

    uploaded: list[StoredObject] = []
    old_thumb_key: str | None = None
    if thumbnail is not None and thumbnail.filename:
        stored = storage.upload_thumbnail(thumbnail, current_user.id, validate_thumbnail(thumbnail))
        uploaded.append(stored)
        old_thumb_key = video.thumbnail_key
        video.thumbnail_key, video.thumbnail_url = stored.key, stored.url

    commit_or_cleanup(db, storage, *uploaded)
    if old_thumb_key:  # la miniatura anterior se borra solo cuando la BD ya apunta a la nueva
        storage.delete(storage.settings.s3_thumbnails_bucket, old_thumb_key)
    return to_read(get_video_or_404(db, video_id), storage)


@router.delete(
    "/{video_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar un video (y sus archivos en S3)",
)
def delete_video(video_id: int, current_user: CurrentUser, db: DbSession, storage: Storage) -> Response:
    video = get_owned_video(db, video_id, current_user.id)
    video_key, thumb_key = video.video_key, video.thumbnail_key
    db.delete(video)
    db.commit()
    # Primero la BD (fuente de verdad), luego los archivos.
    storage.delete(storage.settings.s3_videos_bucket, video_key)
    storage.delete(storage.settings.s3_thumbnails_bucket, thumb_key)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
