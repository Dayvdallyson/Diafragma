from collections.abc import Iterator
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session

from diafragma.db.base import Base
from diafragma.models.products.models import Product, ProductPrice, Store, Unit

DAILY_RATE = 10_000
RACE_POOL_SIZE = 22
STORE_TIME_ZONE = "America/Sao_Paulo"
STARTS_ON = datetime.now(ZoneInfo(STORE_TIME_ZONE)).date() + timedelta(days=30)
ENDS_ON = STARTS_ON + timedelta(days=3)


@pytest.fixture
def race_engine(engine: Engine) -> Iterator[Engine]:
    race_engine = create_engine(engine.url, pool_size=RACE_POOL_SIZE, max_overflow=0)
    yield race_engine

    tables = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)
    with race_engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {tables} CASCADE"))
    race_engine.dispose()


@pytest.fixture
def catalog(session: Session) -> dict[str, str]:
    store = Store(
        name="Store Test",
        country="BR",
        city="São Paulo",
        address="Street 1",
        time_zone=STORE_TIME_ZONE,
        currency="BRL",
    )
    product = Product(
        sku="CAM-001",
        name="Câmera",
        brand="Teste",
        category="camera",
        description="-",
        min_rental_days=1,
        max_rental_days=10,
    )
    session.add_all([store, product])
    session.flush()
    session.add(
        ProductPrice(
            product_id=product.id,
            country="BR",
            currency="BRL",
            daily_rate_cents=DAILY_RATE,
        )
    )
    session.add(Unit(product_id=product.id, store_id=store.id, serial_number="SN-1"))
    session.commit()
    return {"product_id": str(product.id), "store_id": str(store.id)}
