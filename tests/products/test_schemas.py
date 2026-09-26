import pytest
from pydantic import ValidationError

from diafragma.schemas.products.schemas import (
    CreateProductRequest,
    UpdateProductRequest,
)

CREATE_DATA = {
    "sku": "LENS-001",
    "name": "RF 50mm",
    "brand": "Canon",
    "category": "lens",
    "description": "Lente fixa f/1.8",
}


# CATEGORY
@pytest.mark.parametrize("sent", ["camera", "Camera", "CAMERA", " camera  "])
def test_category_is_normalized_to_lowercase(sent):
    payload = CreateProductRequest(**{**CREATE_DATA, "category": sent})

    assert payload.category == "camera"


def test_update_category_is_normalized():
    assert UpdateProductRequest(category="Lens").category == "lens"


@pytest.mark.parametrize("schema", [CreateProductRequest, UpdateProductRequest])
def test_invalid_category_is_rejected(schema):
    data = {**CREATE_DATA, "category": "drone"}

    with pytest.raises(ValidationError):
        schema(**data)


# CREATE
def test_create_defaults():
    payload = CreateProductRequest(**CREATE_DATA)

    assert payload.specifications == {}
    assert (payload.min_rental_days, payload.max_rental_days) == (1, 30)


@pytest.mark.parametrize("missing", ["sku", "name", "brand", "category", "description"])
def test_create_required_field(missing):
    data = {k: v for k, v in CREATE_DATA.items() if k != missing}

    with pytest.raises(ValidationError):
        CreateProductRequest(**data)


def test_create_rejects_min_greater_than_max():
    with pytest.raises(ValidationError):
        CreateProductRequest(**CREATE_DATA, min_rental_days=10, max_rental_days=2)


def test_create_accepts_min_equal_max():
    payload = CreateProductRequest(**CREATE_DATA, min_rental_days=5, max_rental_days=5)
    assert payload.min_rental_days == payload.max_rental_days == 5


# UPDATES
def test_update_accepts_min_lower_than_max():
    payload = UpdateProductRequest(min_rental_days=2, max_rental_days=15)

    assert (payload.min_rental_days, payload.max_rental_days) == (2, 15)


def test_update_rejects_min_greater_than_max():
    with pytest.raises(ValidationError):
        UpdateProductRequest(min_rental_days=5, max_rental_days=3)


@pytest.mark.parametrize("field", ["name", "brand", "description", "min_rental_days"])
def test_update_rejects_explicit_null(field):
    with pytest.raises(ValidationError):
        UpdateProductRequest(**{field: None})


def test_update_uses_same_field_name_as_model():
    payload = UpdateProductRequest(specifications={"iso": 100})

    assert payload.model_dump(exclude_unset=True) == {"specifications": {"iso": 100}}
