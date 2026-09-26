from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session
from testcontainers.community.postgres import PostgresContainer

import diafragma.db.models  # noqa: F401
from diafragma.db.base import Base
from diafragma.db.dependencies import get_db
from diafragma.main import app

POSTGRES_IMAGE = "postgres:18-alpine"


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    with PostgresContainer(POSTGRES_IMAGE, driver="psycopg") as postgres:
        engine = create_engine(postgres.get_connection_url())

        Base.metadata.create_all(engine)

        yield engine

        engine.dispose()


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    connection = engine.connect()
    transaction = connection.begin()

    session = Session(bind=connection, join_transaction_mode="create_savepoint")

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(session: Session) -> Iterator[TestClient]:
    app.dependency_overrides[get_db] = lambda: session
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
