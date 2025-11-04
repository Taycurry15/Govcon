"""Pytest configuration and fixtures."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from govcon.models.base import Base
from govcon.utils.config import Settings


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Test settings with overrides."""
    settings = Settings(
        postgres_url="sqlite:///./test.db",
        testing=True,
        debug=True,
        agent_tracing_enabled=False,
    )
    return settings


@pytest.fixture(scope="function")
def db_session(test_settings: Settings) -> Session:
    """Create a test database session."""
    engine = create_engine(test_settings.postgres_url)
    Base.metadata.create_all(engine)

    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    yield session

    session.close()
    Base.metadata.drop_all(engine)


@pytest.fixture
def mock_opportunity_data() -> dict:
    """Mock opportunity data for testing."""
    return {
        "solicitation_number": "TEST-2024-001",
        "title": "Cybersecurity Services",
        "description": "Provide comprehensive cybersecurity monitoring and response services",
        "agency": "Department of Veterans Affairs",
        "office": "Office of Information Technology",
        "naics_code": "541512",
        "psc_code": "D310",
        "set_aside": "SDVOSB",
        "estimated_value": 1000000.0,
    }
