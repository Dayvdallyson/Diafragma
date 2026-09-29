import threading
from collections.abc import Callable
from uuid import UUID

import pytest
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from diafragma.models.products.models import (
    Product,
    ProductPrice,
    Reservation,
    Store,
    Unit,
    UnitBlock,
)
from diafragma.models.users.models import User
from diafragma.services.reservations.service import (
    UnitUnavailableError,
    create_reservation,
)
from tests.reservations.conftest import ENDS_ON, STARTS_ON, STORE_TIME_ZONE

N_WORKERS = 20
UNAVAILABLE = "unavailable"


@pytest.fixture
def make_catalog(race_engine: Engine) -> Callable[[int], dict[str, UUID]]:

    def _make_catalog(n_units: int) -> dict[str, UUID]:
        with Session(race_engine) as s:
            store = Store(
                name="Loja Teste",
                country="BR",
                city="São Paulo",
                address="Rua Teste, 1",
                time_zone=STORE_TIME_ZONE,
                currency="BRL",
            )
            product = Product(
                sku="RACE-CAM-001",
                name="Câmera Teste",
                brand="Teste",
                category="camera",
                description="Produto para teste de concorrência",
                min_rental_days=1,
                max_rental_days=10,
            )
            user = User(name="Cliente Teste", phone="+5511999990000")
            s.add_all([store, product, user])
            s.flush()
            s.add(
                ProductPrice(
                    product_id=product.id,
                    country="BR",
                    currency="BRL",
                    daily_rate_cents=10_000,
                )
            )
            s.add_all(
                Unit(
                    product_id=product.id,
                    store_id=store.id,
                    serial_number=f"RACE-CAM-001-{i:02}",
                )
                for i in range(n_units)
            )
            s.commit()
            return {
                "user_id": user.id,
                "product_id": product.id,
                "store_id": store.id,
            }

    return _make_catalog


def _reserve_concurrently(
    engine: Engine, keys: list[str], catalog: dict[str, UUID]
) -> list[str]:

    barrier = threading.Barrier(len(keys), timeout=15)
    results = [""] * len(keys)

    def worker(i: int, key: str) -> None:
        with Session(engine) as s:
            barrier.wait()
            try:
                reservation = create_reservation(
                    s,
                    idempotency_key=key,
                    starts_on=STARTS_ON,
                    ends_on=ENDS_ON,
                    channel="phone",
                    **catalog,
                )
                results[i] = str(reservation.id)
            except UnitUnavailableError:
                results[i] = UNAVAILABLE
            except Exception as e:  # noqa: BLE001
                results[i] = f"error: {e!r}"

    threads = [
        threading.Thread(target=worker, args=(i, key)) for i, key in enumerate(keys)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return results


def _count(engine: Engine, model: type) -> int:
    with Session(engine) as s:
        return s.scalar(select(func.count()).select_from(model))


def test_one_unit_one_winner(race_engine: Engine, make_catalog) -> None:
    catalog = make_catalog(n_units=1)
    keys = [f"key-{i}" for i in range(N_WORKERS)]

    results = _reserve_concurrently(race_engine, keys, catalog)

    winners = [r for r in results if r != UNAVAILABLE]
    assert len(winners) == 1, results
    assert results.count(UNAVAILABLE) == N_WORKERS - 1, results
    # losers roll back completely: no orphan reservation left behind
    assert _count(race_engine, Reservation) == 1
    assert _count(race_engine, UnitBlock) == 1


def test_three_units_three_winners(race_engine: Engine, make_catalog) -> None:
    catalog = make_catalog(n_units=3)
    keys = [f"key-{i}" for i in range(N_WORKERS)]

    results = _reserve_concurrently(race_engine, keys, catalog)

    winners = [r for r in results if r != UNAVAILABLE]
    assert len(winners) == 3, results
    assert len(set(winners)) == 3, results
    assert _count(race_engine, UnitBlock) == 3


def test_same_key_creates_one_reservation(race_engine: Engine, make_catalog) -> None:
    catalog = make_catalog(n_units=5)
    keys = ["same-key"] * N_WORKERS

    results = _reserve_concurrently(race_engine, keys, catalog)

    assert len(set(results)) == 1, results
    assert results[0] != UNAVAILABLE and not results[0].startswith("error")
    assert _count(race_engine, Reservation) == 1
    assert _count(race_engine, UnitBlock) == 1
