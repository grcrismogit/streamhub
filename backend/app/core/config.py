"""Configuración centralizada de la aplicación.

Todos los valores se leen desde variables de entorno (o un archivo .env en
desarrollo). En producción, en EC2, se cargan desde /etc/streamhub/api.env
mediante systemd. NUNCA se escriben credenciales en el código.
"""

from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Orden de prioridad (mayor a menor): variables de entorno del proceso,
        # /etc/streamhub/api.env (EC2) y .env (desarrollo local). Los archivos
        # que no existen se ignoran.
        env_file=(".env", "/etc/streamhub/api.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Aplicación ---
    app_name: str = "StreamHub API"
    environment: str = Field(default="development", pattern="^(development|test|production)$")
    log_level: str = "INFO"
    # Orígenes permitidos por CORS, separados por coma.
    # Ej.: http://streamhub-frontend.s3-website-us-east-1.amazonaws.com,http://localhost:5173
    cors_origins: str = "http://localhost:5173"

    # --- Base de datos (Amazon RDS PostgreSQL) ---
    # Opción A: una URL completa en DATABASE_URL.
    # Opción B: las piezas por separado (recomendado: evita problemas con
    # caracteres especiales en la contraseña).
    database_url: str | None = None
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "streamhub"
    db_user: str = "streamhub"
    db_password: str = ""
    db_sslmode: str = "prefer"  # en RDS usar "require"

    # --- Seguridad / JWT ---
    jwt_secret_key: str = Field(min_length=32)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(default=60, ge=5, le=60 * 24)

    # --- Amazon S3 ---
    aws_region: str = "us-east-1"
    s3_videos_bucket: str
    s3_thumbnails_bucket: str
    # Solo para desarrollo local con un emulador (moto/MinIO). En AWS se deja vacío.
    s3_endpoint_url: str | None = None
    # Credenciales SOLO para el emulador local. En EC2 NO se definen: se usa el IAM Role.
    aws_access_key_id: SecretStr | None = None
    aws_secret_access_key: SecretStr | None = None
    s3_presigned_expire_seconds: int = Field(default=3600, ge=60, le=43200)

    # --- Límites de archivos ---
    max_video_size_mb: int = 100
    max_thumbnail_size_mb: int = 5

    @property
    def sqlalchemy_url(self) -> str | URL:
        if self.database_url:
            return self.database_url
        return URL.create(
            drivername="postgresql+psycopg",
            username=self.db_user,
            password=self.db_password,
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
            query={"sslmode": self.db_sslmode},
        )

    def local_aws_credentials(self) -> dict[str, str]:
        """Credenciales explícitas solo si se definieron (desarrollo local); si no, {}."""
        if self.aws_access_key_id and self.aws_secret_access_key:
            return {
                "aws_access_key_id": self.aws_access_key_id.get_secret_value(),
                "aws_secret_access_key": self.aws_secret_access_key.get_secret_value(),
            }
        return {}

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip().rstrip("/") for o in self.cors_origins.split(",") if o.strip()]

    @property
    def max_video_bytes(self) -> int:
        return self.max_video_size_mb * 1024 * 1024

    @property
    def max_thumbnail_bytes(self) -> int:
        return self.max_thumbnail_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
