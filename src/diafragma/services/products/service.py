from uuid import UUID
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from diafragma.db.models import Product
from diafragma.schemas.products.schemas import (
    CreateProductRequest,
    UpdateProductRequest,
)

def create_product(
    payload: CreateProductRequest,
    session: Session,
) -> Product:
    product = Product(
        sku=payload.sku,
        name=payload.name,
        brand=payload.brand,
        category=payload.category,
        description=payload.description,
        specifications=payload.specifications,
        min_rental_days=payload.min_rental_days,
        max_rental_days=payload.max_rental_days,
    )

    session.add(product)
    session.commit()
    session.refresh(product)

    return product

def get_products(
    session: Session,
) -> list[Product]:
    statement = select(Product)
    return list(session.scalars(statement).all())

def get_product(
    id: UUID,
    session: Session,
) -> Product | None:
    return session.get(Product, id)


def update_product(
    id: UUID,
    data: UpdateProductRequest,
):
    ...

def delete_product(
    id: UUID,
    session: Session,
) -> None:
    product = session.get(Product, id)

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    session.delete(product)
    session.commit()
