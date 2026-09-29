import json
import sys
from datetime import date
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from diafragma.db.dependencies import get_db
from diafragma.models.products.models import Product, ProductPrice, Store, Unit

PRODUCT_FIELDS = (
    "sku",
    "name",
    "brand",
    "category",
    "description",
    "specifications",
    "min_rental_days",
    "max_rental_days",
)


def seed_stores(session: Session, stores: list[dict]) -> tuple[dict[str, Store], int]:
    by_key, created = {}, 0
    for s in stores:
        store = session.scalar(
            select(Store).where(Store.name == s["name"], Store.city == s["city"])
        )
        if store is None:
            store = Store(**{k: v for k, v in s.items() if k != "key"})
            session.add(store)
            created += 1
        by_key[s["key"]] = store
    session.flush()
    return by_key, created


def seed_product(
    session: Session, data: dict, stores: dict[str, Store]
) -> dict[str, int]:
    counts = {"products": 0, "prices": 0, "units": 0}

    product = session.scalar(select(Product).where(Product.sku == data["sku"]))
    if product is None:
        product = Product(**{k: data[k] for k in PRODUCT_FIELDS})
        session.add(product)
        session.flush()
        counts["products"] += 1

    for price in data.get("prices", []):
        exists = session.scalar(
            select(ProductPrice.id).where(
                ProductPrice.product_id == product.id,
                ProductPrice.country == price["country"],
                ProductPrice.currency == price["currency"],
                ProductPrice.valid_until.is_(None),
            )
        )
        if exists is None:
            session.add(ProductPrice(product_id=product.id, **price))
            counts["prices"] += 1

    for u in data.get("units", []):
        exists = session.scalar(
            select(Unit.id).where(Unit.serial_number == u["serial_number"])
        )
        if exists is None:
            session.add(
                Unit(
                    product_id=product.id,
                    store_id=stores[u["store"]].id,
                    serial_number=u["serial_number"],
                    condition=u["condition"],
                    status=u["status"],
                    acquired_at=date.fromisoformat(u["acquired_at"])
                    if u.get("acquired_at")
                    else None,
                )
            )
            counts["units"] += 1

    return counts


def main() -> int:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "produtos.json")
    data = json.loads(path.read_text(encoding="utf-8"))

    db = get_db()
    session: Session = next(db)
    try:
        stores, stores_created = seed_stores(session, data["stores"])
        totals = {"products": 0, "prices": 0, "units": 0}
        for product in data["products"]:
            for k, v in seed_product(session, product, stores).items():
                totals[k] += v
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        db.close()

    print(
        f"Criados -> lojas: {stores_created} | produtos: {totals['products']} | "
        f"preços: {totals['prices']} | unidades: {totals['units']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
