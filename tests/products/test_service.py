import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from diafragma.db.models import Product
from diafragma.schemas.products.schemas import (
    CreateProductRequest,
    UpdateProductRequest,
)
from diafragma.services.products.service import (
    InvalidRentalDaysError,
    ProductNotFoundError,
    create_product,
    delete_product,
    get_product,
    get_products,
    update_product,
)

CREATE_DATA = {
    "sku": "LENS-001",
    "name": "RF 50mm",
    "brand": "Canon",
    "category": "Lens",
    "description": "Lente fixa f/1.8",
    "specifications": {"aperture": "f/1.8"},
    "min_rental_days": 1,
    "max_rental_days": 5,
}


# create


def test_create_product_persists_all_fields(session):
    product = create_product(CreateProductRequest(**CREATE_DATA), session)

    session.expire_all()
    saved = session.get(Product, product.id)
    assert saved.sku == "LENS-001"
    assert saved.category == "lens"
    assert saved.specifications == {"aperture": "f/1.8"}
    assert saved.max_rental_days == 5


def test_create_product_generates_id_and_created_at(session):
    product = create_product(CreateProductRequest(**CREATE_DATA), session)

    assert product.id.version == 7
    assert product.created_at is not None


def test_create_product_duplicate_sku_raises_integrity_error(session, product):
    payload = CreateProductRequest(**{**CREATE_DATA, "sku": product.sku})

    with pytest.raises(IntegrityError):
        create_product(payload, session)


# get


def test_get_product_returns_product(session, product):
    assert get_product(product.id, session).id == product.id


def test_get_product_not_found(session):
    with pytest.raises(ProductNotFoundError):
        get_product(uuid.uuid4(), session)


def test_get_products_ordered_by_name(session, make_product):
    make_product(name="Zeta")
    make_product(name="Alfa")

    names = [p.name for p in get_products(session)]

    assert names == ["Alfa", "Zeta"]


# update


def test_update_only_changes_sent_fields(session, product):
    update_product(product.id, UpdateProductRequest(name="Canon EOS R6 II"), session)

    session.expire_all()
    saved = session.get(Product, product.id)
    assert saved.name == "Canon EOS R6 II"
    assert saved.sku == "CAM-001"
    assert saved.brand == "Canon"
    assert (saved.min_rental_days, saved.max_rental_days) == (2, 10)


def test_update_replaces_specifications_entirely(session, product):
    update_product(
        product.id, UpdateProductRequest(specifications={"iso_max": 102400}), session
    )

    session.expire_all()
    assert session.get(Product, product.id).specifications == {"iso_max": 102400}


def test_update_normalizes_category(session, product):
    update_product(product.id, UpdateProductRequest(category="LIGHTING"), session)

    session.expire_all()
    assert session.get(Product, product.id).category == "lighting"


def test_update_returns_product(session, product):
    result = update_product(product.id, UpdateProductRequest(name="Novo"), session)

    assert isinstance(result, Product)
    assert result.name == "Novo"


def test_update_not_found(session):
    with pytest.raises(ProductNotFoundError):
        update_product(uuid.uuid4(), UpdateProductRequest(name="X"), session)


@pytest.mark.parametrize(
    "payload",
    [
        {"min_rental_days": 11},
        {"max_rental_days": 1},
    ],
)
def test_update_invalid_rental_days_against_current_values(session, product, payload):
    with pytest.raises(InvalidRentalDaysError):
        update_product(product.id, UpdateProductRequest(**payload), session)

    session.expire_all()
    saved = session.get(Product, product.id)
    assert (saved.min_rental_days, saved.max_rental_days) == (2, 10)


@pytest.mark.parametrize(
    "payload, expected",
    [
        ({"min_rental_days": 10}, (10, 10)),
        ({"max_rental_days": 2}, (2, 2)),
        ({"min_rental_days": 20, "max_rental_days": 30}, (20, 30)),
    ],
)
def test_update_valid_rental_days(session, product, payload, expected):
    update_product(product.id, UpdateProductRequest(**payload), session)

    session.expire_all()
    saved = session.get(Product, product.id)
    assert (saved.min_rental_days, saved.max_rental_days) == expected


def test_update_duplicate_sku_raises_integrity_error(session, product, make_product):
    other = make_product(sku="CAM-002")

    with pytest.raises(IntegrityError):
        update_product(other.id, UpdateProductRequest(sku="CAM-001"), session)


# delete


def test_delete_product(session, product):
    product_id = product.id

    delete_product(product_id, session)

    assert session.get(Product, product_id) is None


def test_delete_product_not_found(session):
    with pytest.raises(ProductNotFoundError):
        delete_product(uuid.uuid4(), session)
