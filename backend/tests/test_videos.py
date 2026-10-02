from app.core.config import get_settings
from tests.conftest import JPG_BYTES, MP4_BYTES, PNG_BYTES, login, register, upload_video


def _keys(s3, bucket):
    return [o["Key"] for o in s3.list_objects_v2(Bucket=bucket).get("Contents", [])]


def test_create_video_stores_files_in_s3_and_returns_presigned_urls(client, s3):
    register(client)
    video = upload_video(client, login(client))
    assert video["views"] == 0
    assert video["owner"]["name"] == "Ana"
    assert "X-Amz-Signature" in video["video_url"]
    assert "X-Amz-Signature" in video["thumbnail_url"]
    assert len(_keys(s3, "test-videos")) == 1
    assert len(_keys(s3, "test-thumbnails")) == 1


def test_create_video_requires_auth(client):
    res = client.post(
        "/videos",
        data={"title": "Sin token"},
        files={"video": ("a.mp4", MP4_BYTES, "video/mp4"), "thumbnail": ("t.png", PNG_BYTES, "image/png")},
    )
    assert res.status_code == 401


def test_rejects_invalid_files(client, s3):
    register(client)
    headers = login(client)
    # Extensión incorrecta
    res = client.post(
        "/videos",
        headers=headers,
        data={"title": "Video avi"},
        files={
            "video": ("a.avi", MP4_BYTES, "video/x-msvideo"),
            "thumbnail": ("t.png", PNG_BYTES, "image/png"),
        },
    )
    assert res.status_code == 415
    # Extensión .mp4 pero contenido falso
    res = client.post(
        "/videos",
        headers=headers,
        data={"title": "Falso"},
        files={
            "video": ("a.mp4", b"esto no es un mp4" * 10, "video/mp4"),
            "thumbnail": ("t.png", PNG_BYTES, "image/png"),
        },
    )
    assert res.status_code == 415
    # Miniatura GIF
    res = client.post(
        "/videos",
        headers=headers,
        data={"title": "Gif"},
        files={
            "video": ("a.mp4", MP4_BYTES, "video/mp4"),
            "thumbnail": ("t.gif", b"GIF89a" + b"\0" * 50, "image/gif"),
        },
    )
    assert res.status_code == 415
    assert _keys(s3, "test-videos") == []  # nada se subió


def test_rejects_too_large_video(client, monkeypatch):
    register(client)
    headers = login(client)
    monkeypatch.setattr(get_settings(), "max_video_size_mb", 0)  # todo archivo > 0 MB
    res = client.post(
        "/videos",
        headers=headers,
        data={"title": "Pesado"},
        files={"video": ("a.mp4", MP4_BYTES, "video/mp4"), "thumbnail": ("t.png", PNG_BYTES, "image/png")},
    )
    assert res.status_code == 413


def test_list_search_filter_and_pagination(client):
    ana = register(client)
    headers = login(client)
    upload_video(client, headers, "Receta de ceviche")
    upload_video(client, headers, "Tutorial de FastAPI")
    register(client, "luis@example.com", "Luis")
    upload_video(client, login(client, "luis@example.com"), "Viaje a Galápagos")

    page = client.get("/videos").json()
    assert page["total"] == 3
    assert page["items"][0]["title"] == "Viaje a Galápagos"  # más reciente primero

    assert client.get("/videos", params={"q": "fastapi"}).json()["total"] == 1
    assert client.get("/videos", params={"user_id": ana["id"]}).json()["total"] == 2
    assert len(client.get("/videos", params={"limit": 2}).json()["items"]) == 2
    assert client.get("/videos", params={"limit": 999}).status_code == 422


def test_detail_views_and_recommended(client):
    register(client)
    headers = login(client)
    v1 = upload_video(client, headers, "Video uno")
    v2 = upload_video(client, headers, "Video dos")

    assert client.get(f"/videos/{v1['id']}").json()["title"] == "Video uno"
    assert client.get("/videos/9999").status_code == 404

    assert client.post(f"/videos/{v1['id']}/view").json()["views"] == 1
    assert client.post(f"/videos/{v1['id']}/view").json()["views"] == 2
    assert client.get(f"/videos/{v1['id']}").json()["views"] == 2
    assert client.post("/videos/9999/view").status_code == 404

    rec = client.get(f"/videos/{v1['id']}/recommended").json()
    assert [v["id"] for v in rec] == [v2["id"]]  # excluye el actual


def test_update_only_owner(client, s3):
    register(client)
    owner = login(client)
    video = upload_video(client, owner)
    register(client, "intruso@example.com", "Intruso")
    intruder = login(client, "intruso@example.com")

    assert (
        client.put(f"/videos/{video['id']}", headers=intruder, data={"title": "Hackeado"}).status_code == 403
    )
    assert client.put(f"/videos/{video['id']}", data={"title": "Sin token"}).status_code == 401

    res = client.put(
        f"/videos/{video['id']}",
        headers=owner,
        data={"title": "Título nuevo", "description": "Nueva descripción"},
        files={"thumbnail": ("nueva.jpg", JPG_BYTES, "image/jpeg")},
    )
    assert res.status_code == 200, res.text
    assert res.json()["title"] == "Título nuevo"
    thumbs = _keys(s3, "test-thumbnails")
    assert len(thumbs) == 1 and thumbs[0].endswith(".jpg")  # la miniatura vieja se borró


def test_delete_video_removes_db_row_comments_and_s3_files(client, s3):
    register(client)
    headers = login(client)
    video = upload_video(client, headers)
    client.post(f"/videos/{video['id']}/comments", headers=headers, json={"content": "Hola"})

    register(client, "otro@example.com", "Otro")
    assert (
        client.delete(f"/videos/{video['id']}", headers=login(client, "otro@example.com")).status_code == 403
    )

    assert client.delete(f"/videos/{video['id']}", headers=headers).status_code == 204
    assert client.get(f"/videos/{video['id']}").status_code == 404
    assert client.get(f"/videos/{video['id']}/comments").status_code == 404
    assert _keys(s3, "test-videos") == []
    assert _keys(s3, "test-thumbnails") == []


def test_profile_counts_videos(client):
    user = register(client)
    headers = login(client)
    upload_video(client, headers)
    upload_video(client, headers)
    assert client.get("/users/me", headers=headers).json()["video_count"] == 2
    assert client.get(f"/users/{user['id']}").json()["video_count"] == 2


def test_presigned_urls_use_regional_virtual_hosted_endpoint(client):
    """Evita el endpoint global (redirecciones 307 en buckets nuevos fuera de us-east-1)."""
    register(client)
    video = upload_video(client, login(client))
    assert video["video_url"].startswith("https://test-videos.s3.us-east-1.amazonaws.com/videos/")
    assert video["thumbnail_url"].startswith("https://test-thumbnails.s3.us-east-1.amazonaws.com/thumbnails/")


def test_title_is_trimmed_before_validation(client):
    register(client)
    headers = login(client)
    files = {"video": ("a.mp4", MP4_BYTES, "video/mp4"), "thumbnail": ("t.png", PNG_BYTES, "image/png")}
    res = client.post("/videos", headers=headers, data={"title": "   ab   "}, files=files)
    assert res.status_code == 422  # "ab" tiene menos de 3 caracteres
    res = client.post("/videos", headers=headers, data={"title": "  Hola mundo  "}, files=files)
    assert res.json()["title"] == "Hola mundo"
    video_id = res.json()["id"]
    assert client.put(f"/videos/{video_id}", headers=headers, data={"title": "    "}).status_code == 422


def test_search_treats_wildcards_literally_and_validates_sort(client):
    register(client)
    headers = login(client)
    upload_video(client, headers, "Descuento 50% hoy")
    upload_video(client, headers, "Otro video")
    assert client.get("/videos", params={"q": "%"}).json()["total"] == 1
    assert client.get("/videos", params={"q": "_"}).json()["total"] == 0
    assert client.get("/videos", params={"sort": "popular"}).status_code == 200
    assert client.get("/videos", params={"sort": "random"}).status_code == 422
