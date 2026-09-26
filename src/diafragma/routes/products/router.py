from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from diafragma.db.dependencies import get_db
from diafragma.schemas.products.schemas import (
    CreateProductRequest,
    ProductResponse,
)
from diafragma.services.products.service import (
    create_product,
    delete_product,
    get_product,
    get_products,
)

router = APIRouter(
    prefix="/products",
    tags=["products"],
)

@router.post(
    "/",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
)
def create(
    payload: CreateProductRequest,
    session: Session = Depends(get_db),
) -> ProductResponse:
    product = create_product(
        payload=payload,
        session=session,
    )
    return ProductResponse.model_validate(product)

@router.get("/", response_model=list[ProductResponse], status_code=status.HTTP_200_OK)
def get_all(session: Session = Depends(get_db)):
    return get_products(session)

@router.get(
    "/{product_id}",
    response_model=ProductResponse,
    status_code=status.HTTP_200_OK,
)
def get(
    id: UUID,
    session: Session = Depends(get_db),
) -> ProductResponse:
    product = get_product(
        id=id,
        session=session,
    )

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    return ProductResponse.model_validate(product)


@router.delete(
    "/",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete(
    id: UUID,
    session: Session = Depends(get_db),
) -> None:
    delete_product(
        id=id,
        session=session,
)
