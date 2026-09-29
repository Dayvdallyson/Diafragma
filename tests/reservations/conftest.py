from collections.abc import Iterator

import pytest
from sqlalchemy import Engine, create_engine, text

from diafragma.db.base import Base

RACE_POOL_SIZE = 22


@pytest.fixture
def race_engine(engine: Engine) -> Iterator[Engine]:
    race_engine = create_engine(engine.url, pool_size=RACE_POOL_SIZE, max_overflow=0)
    yield race_engine

    tables = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)
    with race_engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {tables} CASCADE"))
    race_engine.dispose()
