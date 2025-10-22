from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy.pool import StaticPool

from src.api.auth.schemas import RegisterInput
from src.api.user.service import UserService
from src.database import get_session
from src.main import app

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"  # Use in-memory DB for isolation

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

# Ensure the database is created before tests run
SQLModel.metadata.create_all(engine)


@pytest.fixture(scope="function")
def db() -> Generator[Session, None, None]:
    """Creates a new database session for a test."""
    with Session(engine) as session:
        
    
        yield session  # Provide session to the test
        session.rollback()  # Ensure data is cleared after test


def override_get_db():
    """Override FastAPI's database dependency to use test session."""
    with Session(engine) as session:
        yield session


app.dependency_overrides[get_session] = override_get_db


@pytest.fixture(scope="function")
def client() -> Generator[TestClient, None, None]:
    """Provides a FastAPI test client."""
    with TestClient(app) as c:
        yield c
