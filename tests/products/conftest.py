import uuid
from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from diafragma.auth.dependencies import require_admin
from diafragma.main import app
from diafragma.models.products.models import Product
from diafragma.models.users.models import User, UserRole


@pytest.fixture
def client(client: TestClient):
    fake_admin = User(name="Admin Test", email="admin@test.com", role=UserRole.ADMIN)
    app.dependency_overrides[require_admin] = lambda: fake_admin
    yield client
    app.dependency_overrides.pop(require_admin, None)


@pytest.fixture
def make_product(session: Session) -> Callable[..., Product]:
    def _make_product(**overrides: Any) -> Product:
        data = {
            "sku": f"SKU-{uuid.uuid4().hex[:8]}",
            "name": "Canon EOS R6",
            "brand": "Canon",
            "category": "camera",
            "description": "Mirrorless full frame",
            "specifications": {"sensor": "full frame", "megapixels": 20},
            "min_rental_days": 2,
            "max_rental_days": 10,
        }
        product = Product(**(data | overrides))
        session.add(product)
        session.commit()
        return product

    return _make_product


@pytest.fixture
def product(make_product) -> Product:
    return make_product(sku="CAM-001")
