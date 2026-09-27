import threading
from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta
from uuid import UUID

import pytest
from psycopg import errors as pg_errors
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.dialects.postgresql import Range
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from diafragma.db.base import Base
from diafragma.models.products.models import (
    Maintenance,
    Product,
    Store,
    Unit,
    UnitBlock,
)

N_WORKERS = 20

CONFLICT_ERRORS = (pg_errors.ExclusionViolation, pg_errors.DeadlockDetected)


@pytest.fixture
def race_engine(engine: Engine) -> Iterator[Engine]:
    race_engine = create_engine(engine.url, pool_size=N_WORKERS + 2, max_overflow=0)
    yield race_engine
    race_engine.dispose()


@pytest.fixture
def unit_id(race_engine: Engine) -> Iterator[UUID]:
    with Session(race_engine) as s:
        store = Store(
            name="Loja Teste",
            country="BR",
            city="São Paulo",
            address="Rua Teste, 1",
            time_zone="America/Sao_Paulo",
            currency="BRL",
        )
        product = Product(
            sku="RACE-CAM-001",
            name="Câmera Teste",
            brand="Teste",
            category="camera",
            description="Produto para teste de concorrência",
        )
        s.add_all([store, product])
        s.flush()
        unit = Unit(
            product_id=product.id, store_id=store.id, serial_number="RACE-CAM-001-01"
        )
        s.add(unit)
        s.commit()
        created_id = unit.id

    yield created_id

    tables = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)
    with race_engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {tables} CASCADE"))


def _block_concurrently(
    engine: Engine, unit_id: UUID, periods: list[Range[date]]
) -> list[str]:

    barrier = threading.Barrier(len(periods), timeout=15)
    results: list[str] = [""] * len(periods)

    def worker(i: int, period: Range[date]) -> None:
        with Session(engine) as s:
            maintenance = Maintenance(
                unit_id=unit_id, reason=f"race-{i}", starts_at=datetime.now(UTC)
            )
            s.add(maintenance)
            s.flush()
            barrier.wait()
            try:
                s.add(
                    UnitBlock(
                        unit_id=unit_id, period=period, maintenance_id=maintenance.id
                    )
                )
                s.commit()
                results[i] = "ok"
            except DBAPIError as e:
                s.rollback()
                results[i] = (
                    "conflict"
                    if isinstance(e.orig, CONFLICT_ERRORS)
                    else f"error: {type(e.orig).__name__}"
                )

    threads = [
        threading.Thread(target=worker, args=(i, p)) for i, p in enumerate(periods)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return results


def test_same_period_only_one_wins(race_engine: Engine, unit_id: UUID) -> None:
    period = Range(date(2026, 10, 1), date(2026, 10, 5), bounds="[)")

    results = _block_concurrently(race_engine, unit_id, [period] * N_WORKERS)

    assert results.count("ok") == 1
    assert results.count("conflict") == N_WORKERS - 1


def test_back_to_back_periods_all_win(race_engine: Engine, unit_id: UUID) -> None:
    start = date(2026, 11, 1)
    periods = [
        Range(start + timedelta(days=i), start + timedelta(days=i + 1), bounds="[)")
        for i in range(N_WORKERS)
    ]

    results = _block_concurrently(race_engine, unit_id, periods)

    assert results == ["ok"] * N_WORKERS
