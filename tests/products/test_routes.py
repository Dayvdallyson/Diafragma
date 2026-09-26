import uuid

VALID_PAYLOAD = {
    "sku": "LENS-001",
    "name": "RF 50mm",
    "brand": "Canon",
    "category": "lens",
    "description": "Lente fixa f/1.8",
    "min_rental_days": 1,
    "max_rental_days": 5,
}

# POST

def test_create_returns_201_and_body(client):
    response = client.post("/products", json=VALID_PAYLOAD)

    assert response.status_code == 201
    body = response.json()
    assert body["sku"] == "LENS-001"
    assert body["specifications"] == {}
    uuid.UUID(body["id"])
    assert body["created_at"]


def test_create_accepts_capitalized_category(client):
    response = client.post("/products", json={**VALID_PAYLOAD, "category": "Camera"})

    assert response.status_code == 201
    assert response.json()["category"] == "camera"


def test_create_invalid_category_returns_422(client):
    response = client.post("/products", json={**VALID_PAYLOAD, "category": "drone"})

    assert response.status_code == 422


def test_create_missing_required_field_returns_422(client):
    payload = {k: v for k, v in VALID_PAYLOAD.items() if k != "description"}

    response = client.post("/products", json=payload)

    assert response.status_code == 422


def test_create_invalid_rental_days_returns_422(client):
    payload = {**VALID_PAYLOAD, "min_rental_days": 10, "max_rental_days": 2}

    response = client.post("/products", json=payload)

    assert response.status_code == 422


def test_create_zero_rental_days_returns_422(client):
    response = client.post("/products", json={**VALID_PAYLOAD, "min_rental_days": 0})

    assert response.status_code == 422


def test_create_duplicate_sku_returns_409(client, product):
    response = client.post("/products", json={**VALID_PAYLOAD, "sku": product.sku})

    assert response.status_code == 409


# GET (products)

def test_list_products(client, product):
    response = client.get("/products")

    assert response.status_code == 200
    assert [p["id"] for p in response.json()] == [str(product.id)]


def test_list_products_empty(client):
    response = client.get("/products")

    assert response.status_code == 200
    assert response.json() == []


# GET (product)

def test_get_product(client, product):
    response = client.get(f"/products/{product.id}")

    assert response.status_code == 200
    assert response.json()["name"] == "Canon EOS R6"


def test_get_product_not_found_returns_404(client):
    response = client.get(f"/products/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Product not found"}


def test_get_product_invalid_uuid_returns_422(client):
    response = client.get("/products/nao-e-um-uuid")

    assert response.status_code == 422


# PATCH

def test_patch_partial_update(client, product):
    response = client.patch(f"/products/{product.id}", json={"name": "Canon EOS R6 II"})

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Canon EOS R6 II"
    assert body["brand"] == "Canon"
    assert body["specifications"] == {"sensor": "full frame", "megapixels": 20}


def test_patch_accepts_capitalized_category(client, product):
    response = client.patch(f"/products/{product.id}", json={"category": "Audio"})

    assert response.status_code == 200
    assert response.json()["category"] == "audio"


def test_patch_invalid_category_returns_422(client, product):
    response = client.patch(f"/products/{product.id}", json={"category": "drone"})

    assert response.status_code == 422


def test_patch_explicit_null_returns_422(client, product):
    response = client.patch(f"/products/{product.id}", json={"name": None})

    assert response.status_code == 422


def test_patch_empty_body_changes_nothing(client, product):
    response = client.patch(f"/products/{product.id}", json={})

    assert response.status_code == 200
    assert response.json()["name"] == "Canon EOS R6"


def test_patch_not_found_returns_404(client):
    response = client.patch(f"/products/{uuid.uuid4()}", json={"name": "X"})

    assert response.status_code == 404


def test_patch_invalid_rental_days_returns_422(client, product):
    response = client.patch(f"/products/{product.id}", json={"min_rental_days": 11})

    assert response.status_code == 422
    assert "min_rental_days" in response.json()["detail"]


def test_patch_duplicate_sku_returns_409(client, product, make_product):
    other = make_product(sku="CAM-002")

    response = client.patch(f"/products/{other.id}", json={"sku": product.sku})

    assert response.status_code == 409


# DELETE

def test_delete_returns_204(client, product):
    response = client.delete(f"/products/{product.id}")

    assert response.status_code == 204
    assert client.get(f"/products/{product.id}").status_code == 404


def test_delete_not_found_returns_404(client):
    response = client.delete(f"/products/{uuid.uuid4()}")

    assert response.status_code == 404
