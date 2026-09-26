from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from diafragma.db.dependencies import get_db
from diafragma.schemas.products.schemas import (
    CreateProductRequest,
    ProductResponse,
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

router = APIRouter(prefix="/products", tags=["products"])

SessionDep = Annotated[Session, Depends(get_db)]


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Product not found",
    )


def _sku_conflict() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="Product with this sku already exists",
    )


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create(payload: CreateProductRequest, session: SessionDep):
    try:
        return create_product(payload, session)
    except IntegrityError:
        session.rollback()
        raise _sku_conflict()


@router.get("", response_model=list[ProductResponse])
def get_all(session: SessionDep):
    return get_products(session)


@router.get("/{product_id}", response_model=ProductResponse)
def get(product_id: UUID, session: SessionDep):
    try:
        return get_product(product_id, session)
    except ProductNotFoundError:
        raise _not_found()


@router.patch("/{product_id}", response_model=ProductResponse)
def update(product_id: UUID, payload: UpdateProductRequest, session: SessionDep):
    try:
        return update_product(product_id, payload, session)
    except ProductNotFoundError:
        raise _not_found()
    except InvalidRentalDaysError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )
    except IntegrityError:
        session.rollback()
        raise _sku_conflict()


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(product_id: UUID, session: SessionDep) -> None:
    try:
        delete_product(product_id, session)
    except ProductNotFoundError:
        raise _not_found()
