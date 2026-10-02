from tests.conftest import login, register, upload_video


def test_create_and_list_comments(client):
    register(client)
    headers = login(client)
    video = upload_video(client, headers)

    res = client.post(
        f"/videos/{video['id']}/comments", headers=headers, json={"content": "  ¡Buen video!  "}
    )
    assert res.status_code == 201
    body = res.json()
    assert body["content"] == "¡Buen video!"  # se recortan espacios
    assert body["author"]["name"] == "Ana"

    client.post(f"/videos/{video['id']}/comments", headers=headers, json={"content": "Segundo"})
    comments = client.get(f"/videos/{video['id']}/comments").json()
    assert [c["content"] for c in comments] == ["Segundo", "¡Buen video!"]  # recientes primero


def test_comment_requires_auth_and_valid_content(client):
    register(client)
    headers = login(client)
    video = upload_video(client, headers)
    url = f"/videos/{video['id']}/comments"
    assert client.post(url, json={"content": "hola"}).status_code == 401
    assert client.post(url, headers=headers, json={"content": "   "}).status_code == 422
    assert client.post(url, headers=headers, json={"content": "x" * 1001}).status_code == 422


def test_comment_on_missing_video_is_404(client):
    register(client)
    headers = login(client)
    assert client.post("/videos/999/comments", headers=headers, json={"content": "hola"}).status_code == 404
    assert client.get("/videos/999/comments").status_code == 404
