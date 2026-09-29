import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")

from diafragma.auth.security import hash_password
from diafragma.models.users.models import User, UserRole

TEST_PASSWORD = "strong-test-password"

import uuid
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session
from testcontainers.community.postgres import PostgresContainer

import diafragma.models.products.models  # noqa: F401
from diafragma.db.base import Base
from diafragma.db.dependencies import get_db
from diafragma.main import app

POSTGRES_IMAGE = "postgres:18-alpine"


@pytest.fixture
def make_user(session: Session):
    def _make_user(*, password: str = TEST_PASSWORD, **overrides) -> User:
        data = {
            "name": "Test User",
            "email": f"user-{uuid.uuid4().hex[:8]}@test.com",
            "role": UserRole.CUSTOMER,
            "hashed_password": hash_password(password),
        }
        user = User(**(data | overrides))
        session.add(user)
        session.commit()
        return user

    return _make_user


@pytest.fixture
def auth_headers(anon_client: TestClient):
    def _auth_headers(email: str, password: str = TEST_PASSWORD) -> dict[str, str]:
        response = anon_client.post(
            "/auth/token", data={"username": email, "password": password}
        )
        assert response.status_code == 200, response.text
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    return _auth_headers


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    with PostgresContainer(POSTGRES_IMAGE, driver="psycopg") as postgres:
        engine = create_engine(postgres.get_connection_url())

        with engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS btree_gist"))
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
def anon_client(session: Session) -> Iterator[TestClient]:
    app.dependency_overrides[get_db] = lambda: session
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def client(anon_client):
    return anon_client
