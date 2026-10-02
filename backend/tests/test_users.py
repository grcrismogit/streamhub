from tests.conftest import login, register


def test_register_returns_user_without_password(client):
    user = register(client)
    assert user["email"] == "ana@example.com"
    assert user["video_count"] == 0
    assert "password" not in user and "password_hash" not in user


def test_register_duplicate_email_is_409_case_insensitive(client):
    register(client)
    res = client.post(
        "/users", json={"name": "Otra", "email": "ANA@example.com", "password": "SuperSecreta123"}
    )
    assert res.status_code == 409


def test_register_validates_input(client):
    assert (
        client.post("/users", json={"name": "A", "email": "x@y.com", "password": "12345678"}).status_code
        == 422
    )
    assert (
        client.post(
            "/users", json={"name": "Ana", "email": "no-es-correo", "password": "12345678"}
        ).status_code
        == 422
    )
    assert (
        client.post("/users", json={"name": "Ana", "email": "a@b.com", "password": "corta"}).status_code
        == 422
    )


def test_login_success_and_me(client):
    register(client)
    headers = login(client)
    me = client.get("/users/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["name"] == "Ana"


def test_login_wrong_password_and_unknown_email(client):
    register(client)
    assert (
        client.post("/login", data={"username": "ana@example.com", "password": "mala-clave"}).status_code
        == 401
    )
    assert (
        client.post("/login", data={"username": "nadie@example.com", "password": "x" * 10}).status_code == 401
    )


def test_me_requires_valid_token(client):
    assert client.get("/users/me").status_code == 401
    assert client.get("/users/me", headers={"Authorization": "Bearer basura"}).status_code == 401


def test_public_profile_hides_email(client):
    user = register(client)
    res = client.get(f"/users/{user['id']}")
    assert res.status_code == 200
    assert "email" not in res.json()
    assert client.get("/users/9999").status_code == 404


def test_health(client):
    assert client.get("/health").json() == {"status": "ok", "database": "ok"}
