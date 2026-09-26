import uuid
from collections.abc import Callable
from typing import Any

import pytest
from sqlalchemy.orm import Session

from diafragma.db.models import Product

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
