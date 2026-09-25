from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from diafragma.db.dependencies import get_db
from diafragma.schemas.products.schemas import (
    CreateProductRequest,
    ProductResponse,
)
from diafragma.services.products.service import create_product

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
    product = create_product(session, payload)

    return ProductResponse.model_validate(product)
