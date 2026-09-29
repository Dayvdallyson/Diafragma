import uuid

import pytest

from diafragma.models.users.models import UserRole

PRODUCT_PAYLOAD = {
    "sku": "AUTH-001",
    "name": "Canon EOS R6",
    "brand": "Canon",
    "category": "camera",
    "description": "Mirrorless full frame",
    "specifications": {"sensor": "full frame"},
    "min_rental_days": 2,
    "max_rental_days": 10,
}


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("post", "/products"),
        ("patch", f"/products/{uuid.uuid4()}"),
        ("delete", f"/products/{uuid.uuid4()}"),
    ],
)
def test_write_routes_require_token(anon_client, method, path):
    response = anon_client.request(method, path, json={})
    assert response.status_code == 401


def test_list_products_is_public(anon_client):
    assert anon_client.get("/products").status_code == 200


def test_customer_token_returns_403(anon_client, make_user, auth_headers):
    customer = make_user(role=UserRole.CUSTOMER)

    response = anon_client.post(
        "/products", json=PRODUCT_PAYLOAD, headers=auth_headers(customer.email)
    )

    assert response.status_code == 403


def test_admin_token_creates_product(anon_client, make_user, auth_headers):
    admin = make_user(role=UserRole.ADMIN)

    response = anon_client.post(
        "/products", json=PRODUCT_PAYLOAD, headers=auth_headers(admin.email)
    )

    assert response.status_code == 201


def test_invalid_token_returns_401(anon_client):
    response = anon_client.post(
        "/products",
        json=PRODUCT_PAYLOAD,
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401
