PASSWORD = "strong-test-password"


def _login(client, email, password):
    return client.post("/auth/token", data={"username": email, "password": password})


def test_login_returns_token(anon_client, make_user):
    user = make_user(password=PASSWORD)

    response = _login(anon_client, user.email, PASSWORD)

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.json()["access_token"]


def test_login_wrong_password_returns_401(anon_client, make_user):
    user = make_user(password=PASSWORD)
    assert _login(anon_client, user.email, "wrong-password").status_code == 401


def test_login_unknown_email_returns_401(anon_client):
    assert _login(anon_client, "nobody@test.com", PASSWORD).status_code == 401


def test_login_user_without_password_returns_401(anon_client, make_user):
    user = make_user(hashed_password=None)
    assert _login(anon_client, user.email, PASSWORD).status_code == 401


def test_login_inactive_user_returns_401(anon_client, make_user):
    user = make_user(password=PASSWORD, is_active=False)
    assert _login(anon_client, user.email, PASSWORD).status_code == 401
