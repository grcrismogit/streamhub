"""Fixtures de pruebas: SQLite temporal + S3 simulado con moto (sin tocar AWS)."""

import os

# Las variables deben existir ANTES de importar la app.
os.environ.update(
    {
        "ENVIRONMENT": "test",
        "DATABASE_URL": "sqlite:///./test.db",
        "JWT_SECRET_KEY": "test-secret-key-with-more-than-32-characters",
        "S3_VIDEOS_BUCKET": "test-videos",
        "S3_THUMBNAILS_BUCKET": "test-thumbnails",
        "S3_ENDPOINT_URL": "",  # ignora el emulador local que pueda haber en .env
        "AWS_REGION": "us-east-1",
        "AWS_ACCESS_KEY_ID": "testing",
        "AWS_SECRET_ACCESS_KEY": "testing",
        "AWS_DEFAULT_REGION": "us-east-1",
    }
)

import boto3  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from moto import mock_aws  # noqa: E402
from sqlalchemy import event  # noqa: E402

from app.db.session import engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base  # noqa: E402
from app.services.storage import get_storage  # noqa: E402


@event.listens_for(engine, "connect")
def _enable_sqlite_fk(dbapi_connection, _record):
    dbapi_connection.execute("PRAGMA foreign_keys=ON")


MP4_BYTES = b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom" + b"\x00" * 1024
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 256
JPG_BYTES = b"\xff\xd8\xff\xe0" + b"\x00" * 256


@pytest.fixture(autouse=True)
def _db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture(autouse=True)
def s3():
    with mock_aws():
        get_storage.cache_clear()
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket="test-videos")
        client.create_bucket(Bucket="test-thumbnails")
        yield client
        get_storage.cache_clear()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def register(client: TestClient, email: str = "ana@example.com", name: str = "Ana") -> dict:
    res = client.post("/users", json={"name": name, "email": email, "password": "SuperSecreta123"})
    assert res.status_code == 201, res.text
    return res.json()


def login(client: TestClient, email: str = "ana@example.com") -> dict[str, str]:
    res = client.post("/login", data={"username": email, "password": "SuperSecreta123"})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def upload_video(client: TestClient, headers: dict, title: str = "Mi primer video") -> dict:
    res = client.post(
        "/videos",
        headers=headers,
        data={"title": title, "description": "Descripción de prueba"},
        files={
            "video": ("clip.mp4", MP4_BYTES, "video/mp4"),
            "thumbnail": ("thumb.png", PNG_BYTES, "image/png"),
        },
    )
    assert res.status_code == 201, res.text
    return res.json()
