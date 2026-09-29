from tests.reservations.conftest import DAILY_RATE, ENDS_ON, STARTS_ON


def _body(catalog: dict[str, str], **overrides) -> dict:
    return {
        **catalog,
        "starts_on": STARTS_ON.isoformat(),
        "ends_on": ENDS_ON.isoformat(),
        "channel": "web_voice",
        **overrides,
    }


def _headers(auth_headers, make_user, key: str = "key-00000001") -> dict[str, str]:
    return {**auth_headers(make_user().email), "Idempotency-Key": key}


def test_create_returns_pending_reservation_with_total(
    anon_client, catalog, auth_headers, make_user
):
    response = anon_client.post(
        "/reservations", json=_body(catalog), headers=_headers(auth_headers, make_user)
    )

    assert response.status_code == 201, response.text
    data = response.json()
    assert data["status"] == "pending"
    assert data["expires_at"] is not None
    assert data["total_cents"] == 3 * DAILY_RATE


def test_same_key_returns_same_reservation(
    anon_client, catalog, auth_headers, make_user
):
    headers = _headers(auth_headers, make_user)

    first = anon_client.post("/reservations", json=_body(catalog), headers=headers)
    retry = anon_client.post("/reservations", json=_body(catalog), headers=headers)

    assert first.status_code == retry.status_code == 201
    assert first.json()["id"] == retry.json()["id"]


def test_second_customer_gets_409_when_only_unit_is_taken(
    anon_client, catalog, auth_headers, make_user
):
    anon_client.post(
        "/reservations", json=_body(catalog), headers=_headers(auth_headers, make_user)
    )

    response = anon_client.post(
        "/reservations", json=_body(catalog), headers=_headers(auth_headers, make_user)
    )

    assert response.status_code == 409


def test_past_start_date_returns_422(anon_client, catalog, auth_headers, make_user):
    body = _body(catalog, starts_on="2020-01-01", ends_on="2020-01-03")

    response = anon_client.post(
        "/reservations", json=body, headers=_headers(auth_headers, make_user)
    )

    assert response.status_code == 422


def test_missing_idempotency_key_returns_422(
    anon_client, catalog, auth_headers, make_user
):
    response = anon_client.post(
        "/reservations", json=_body(catalog), headers=auth_headers(make_user().email)
    )

    assert response.status_code == 422


def test_create_requires_token(anon_client, catalog):
    response = anon_client.post(
        "/reservations",
        json=_body(catalog),
        headers={"Idempotency-Key": "key-00000001"},
    )

    assert response.status_code == 401


def test_availability_drops_after_reservation(
    anon_client, catalog, auth_headers, make_user
):
    url = f"/products/{catalog['product_id']}/availability"
    params = {"starts_on": STARTS_ON.isoformat(), "ends_on": ENDS_ON.isoformat()}

    before = anon_client.get(url, params=params).json()["available"]
    anon_client.post(
        "/reservations", json=_body(catalog), headers=_headers(auth_headers, make_user)
    )
    after = anon_client.get(url, params=params).json()["available"]

    assert (before, after) == (1, 0)
