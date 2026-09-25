from sqlalchemy.orm import Session

from diafragma.db.models import Product
from diafragma.schemas.products.schemas import CreateProductRequest

def create_product(
    session: Session,
    payload: CreateProductRequest,
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
