from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError

from diafragma.auth.dependencies import require_admin
from diafragma.db.dependencies import SessionDep
from diafragma.schemas.products.schemas import (
    CreateProductRequest,
    ProductResponse,
    UpdateProductRequest,
)
from diafragma.schemas.reservations.schemas import (
    AvailabilityQuery,
    AvailabilityResponse,
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
from diafragma.services.reservations.service import find_available_units

router = APIRouter(prefix="/products", tags=["products"])


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


@router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
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


@router.patch(
    "/{product_id}",
    response_model=ProductResponse,
    dependencies=[Depends(require_admin)],
)
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


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
def delete(product_id: UUID, session: SessionDep) -> None:
    try:
        delete_product(product_id, session)
    except ProductNotFoundError:
        raise _not_found()


@router.get("/{product_id}/availability", response_model=AvailabilityResponse)
def availability(
    product_id: UUID, query: Annotated[AvailabilityQuery, Query()], session: SessionDep
):
    try:
        get_product(product_id, session)
    except ProductNotFoundError:
        raise _not_found()

    units = find_available_units(
        session, product_id, query.starts_on, query.ends_on, query.store_id
    )

    return AvailabilityResponse(
        product_id=product_id,
        starts_on=query.starts_on,
        ends_on=query.ends_on,
        available=len(units),
        units=units,
    )
