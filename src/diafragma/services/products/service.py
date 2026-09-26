from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from diafragma.db.models import Product
from diafragma.schemas.products.schemas import (
    CreateProductRequest,
    UpdateProductRequest,
)

class ProductNotFoundError(Exception):
    pass


class InvalidRentalDaysError(Exception):
    pass


def create_product(payload: CreateProductRequest, session: Session) -> Product:
    product = Product(**payload.model_dump())
    session.add(product)
    session.commit()
    return product


def get_products(session: Session) -> list[Product]:
    stmt = select(Product).order_by(Product.name)
    return list(session.scalars(stmt))


def get_product(product_id: UUID, session: Session) -> Product:
    product = session.get(Product, product_id)
    if product is None:
        raise ProductNotFoundError(product_id)
    return product


def update_product(
    product_id: UUID,
    payload: UpdateProductRequest,
    session: Session,
) -> Product:
    product = get_product(product_id, session)

    values = payload.model_dump(exclude_unset=True)

    min_days = values.get("min_rental_days", product.min_rental_days)
    max_days = values.get("max_rental_days", product.max_rental_days)
    if min_days > max_days:
        raise InvalidRentalDaysError(
            f"min_rental_days ({min_days}) cannot be greater than "
            f"max_rental_days ({max_days})"
        )

    for field, value in values.items():
        setattr(product, field, value)
    session.commit()
    return product


def delete_product(product_id: UUID, session: Session) -> None:
    product = get_product(product_id, session)
    session.delete(product)
    session.commit()
