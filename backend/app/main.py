"""Punto de entrada de la API StreamHub.

Ejecutar en local:  uvicorn app.main:app --reload
Documentación:      http://localhost:8000/docs
"""

import logging

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.deps import DbSession
from app.api.routes import auth, comments, users, videos
from app.core.config import get_settings
from app.schemas import HealthStatus

settings = get_settings()

logging.basicConfig(
    level=settings.log_level.upper(),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description=(
        "API de la plataforma de videos **StreamHub** (React + FastAPI + AWS).\n\n"
        "1. Crea un usuario con `POST /users`.\n"
        "2. Pulsa **Authorize** e ingresa tu correo (como *username*) y contraseña.\n"
        "3. Ya puedes publicar videos y comentar."
    ),
    openapi_tags=[
        {"name": "Usuarios", "description": "Registro y perfiles"},
        {"name": "Autenticación", "description": "Login con JWT"},
        {"name": "Videos", "description": "Catálogo, publicación y gestión de videos"},
        {"name": "Comentarios", "description": "Comentarios por video"},
        {"name": "Sistema", "description": "Salud del servicio"},
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,  # usamos Bearer token, no cookies
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
    max_age=600,
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(videos.router)
app.include_router(comments.router)


@app.get("/health", response_model=HealthStatus, tags=["Sistema"], summary="Estado de la API y la BD")
def health(db: DbSession) -> HealthStatus:
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        logging.getLogger(__name__).exception("Health check: la BD no responde")
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Base de datos no disponible") from exc
    return HealthStatus(status="ok", database="ok")


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    return {"name": settings.app_name, "docs": "/docs"}
