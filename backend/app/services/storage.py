"""Acceso a Amazon S3 (videos y miniaturas).

- Las credenciales NO están en el código: boto3 las obtiene automáticamente
  del IAM Role (Instance Profile) asociado a la instancia EC2.
- Los buckets de medios son PRIVADOS. Para reproducir/mostrar se generan URLs
  prefirmadas de corta duración.
"""

import logging
import uuid
from dataclasses import dataclass
from functools import lru_cache
from typing import BinaryIO

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import HTTPException, UploadFile, status

from app.core.config import get_settings

logger = logging.getLogger(__name__)


# ---------- Validación de archivos ----------


@dataclass(frozen=True)
class FileRule:
    kind: str
    extensions: tuple[str, ...]
    content_types: tuple[str, ...]
    max_bytes: int


def _video_rule() -> FileRule:
    s = get_settings()
    return FileRule("video", (".mp4",), ("video/mp4",), s.max_video_bytes)


def _thumbnail_rule() -> FileRule:
    s = get_settings()
    return FileRule(
        "miniatura", (".jpg", ".jpeg", ".png"), ("image/jpeg", "image/png"), s.max_thumbnail_bytes
    )


def _sniff_type(header: bytes) -> str | None:
    """Detecta el tipo REAL por sus 'magic bytes' (no confiamos en la extensión)."""
    if len(header) >= 12 and header[4:8] == b"ftyp":
        return "video/mp4"
    if header.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    return None


def _file_size(file: BinaryIO) -> int:
    file.seek(0, 2)
    size = file.tell()
    file.seek(0)
    return size


def validate_upload(upload: UploadFile, rule: FileRule) -> str:
    """Valida extensión, tipo real y tamaño. Devuelve el content-type real."""
    filename = (upload.filename or "").lower()
    if not filename.endswith(rule.extensions):
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            f"Formato de {rule.kind} no permitido. Usa: {', '.join(rule.extensions)}",
        )

    size = _file_size(upload.file)
    if size == 0:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"El archivo de {rule.kind} está vacío")
    if size > rule.max_bytes:
        raise HTTPException(
            status.HTTP_413_CONTENT_TOO_LARGE,
            f"El {rule.kind} supera el máximo de {rule.max_bytes // (1024 * 1024)} MB",
        )

    header = upload.file.read(16)
    upload.file.seek(0)
    real_type = _sniff_type(header)
    if real_type not in rule.content_types:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            f"El contenido del archivo no corresponde a un {rule.kind} válido",
        )
    return real_type


def validate_video(upload: UploadFile) -> str:
    return validate_upload(upload, _video_rule())


def validate_thumbnail(upload: UploadFile) -> str:
    return validate_upload(upload, _thumbnail_rule())


# ---------- Cliente S3 ----------


@dataclass(frozen=True)
class StoredObject:
    bucket: str
    key: str
    url: str


class S3Storage:
    def __init__(self) -> None:
        s = get_settings()
        self.settings = s
        # Endpoint REGIONAL explícito (https://s3.<región>.amazonaws.com): evita que las
        # URLs prefirmadas apunten al endpoint global y fallen con "TemporaryRedirect"
        # o "SignatureDoesNotMatch" en buckets recién creados fuera de us-east-1.
        endpoint = s.s3_endpoint_url or f"https://s3.{s.aws_region}.amazonaws.com"
        self.client = boto3.client(
            "s3",
            region_name=s.aws_region,
            endpoint_url=endpoint,
            # Sin credenciales explícitas: en EC2, boto3 usa automáticamente las credenciales
            # temporales del IAM Role. Solo en desarrollo local pueden venir del .env.
            **s.local_aws_credentials(),
            config=Config(
                signature_version="s3v4",
                s3={"addressing_style": "path" if s.s3_endpoint_url else "virtual"},
                retries={"max_attempts": 3, "mode": "standard"},
            ),
        )

    def object_url(self, bucket: str, key: str) -> str:
        if self.settings.s3_endpoint_url:
            return f"{self.settings.s3_endpoint_url.rstrip('/')}/{bucket}/{key}"
        return f"https://{bucket}.s3.{self.settings.aws_region}.amazonaws.com/{key}"

    def upload(self, file: BinaryIO, bucket: str, prefix: str, ext: str, content_type: str) -> StoredObject:
        key = f"{prefix}/{uuid.uuid4().hex}{ext}"
        file.seek(0)
        try:
            # upload_fileobj usa multipart upload automáticamente para archivos grandes.
            self.client.upload_fileobj(
                file,
                bucket,
                key,
                ExtraArgs={
                    "ContentType": content_type,
                    "CacheControl": "public, max-age=31536000, immutable",
                },
            )
        except (BotoCoreError, ClientError) as exc:
            logger.exception("Error subiendo %s a s3://%s", key, bucket)
            raise HTTPException(
                status.HTTP_502_BAD_GATEWAY, "No se pudo guardar el archivo en el almacenamiento"
            ) from exc
        return StoredObject(bucket, key, self.object_url(bucket, key))

    def presigned_url(self, bucket: str, key: str) -> str:
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=self.settings.s3_presigned_expire_seconds,
        )

    def delete(self, bucket: str, key: str) -> None:
        """Borrado 'best effort': si falla se registra, pero no rompe el request."""
        try:
            self.client.delete_object(Bucket=bucket, Key=key)
        except (BotoCoreError, ClientError):
            logger.exception("No se pudo borrar s3://%s/%s", bucket, key)

    # Atajos por bucket
    def upload_video(self, upload: UploadFile, user_id: int, content_type: str) -> StoredObject:
        return self.upload(
            upload.file, self.settings.s3_videos_bucket, f"videos/{user_id}", ".mp4", content_type
        )

    def upload_thumbnail(self, upload: UploadFile, user_id: int, content_type: str) -> StoredObject:
        ext = ".png" if content_type == "image/png" else ".jpg"
        return self.upload(
            upload.file, self.settings.s3_thumbnails_bucket, f"thumbnails/{user_id}", ext, content_type
        )


@lru_cache
def get_storage() -> S3Storage:
    return S3Storage()
