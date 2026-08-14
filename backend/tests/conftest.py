"""
HospitalOps AI — pytest configuration and shared fixtures.

This conftest applies to all tests in the backend/tests/ directory.

Key concern: The FastAPI app now uses a lifespan that connects to MongoDB at startup.
Unit tests (test_health.py, test_models.py) must not require a real MongoDB connection.

Strategy:
  - For unit tests, mock init_db and init_indexes so the app starts without MongoDB.
  - Integration tests (marked @pytest.mark.integration) use the real database.
    They are skipped automatically if MongoDB is not available.

The 'mock_db_lifecycle' autouse fixture patches the database lifecycle functions
for all non-integration tests, ensuring the existing 10 health tests continue to pass
without any MongoDB dependency.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

# ── Autouse: mock database lifecycle for unit tests ───────────────────────────


@pytest.fixture(autouse=True)
def mock_db_lifecycle(request: pytest.FixtureRequest):
    """
    Automatically mock MongoDB init/shutdown for all tests NOT marked as integration.

    Tests marked @pytest.mark.integration opt out of this fixture and receive
    a real database connection instead (provided by the integration fixture below).

    This keeps unit tests fast and independent of infrastructure.
    """
    if request.node.get_closest_marker("integration"):
        # Integration tests handle their own database setup.
        yield
        return

    # Patch init_db, init_indexes, and close_db so the app lifespan
    # completes without any real MongoDB connection.
    with (
        patch("app.database.client.init_db", new_callable=AsyncMock) as mock_init,
        patch("app.database.client.init_indexes", new_callable=AsyncMock),
        patch("app.database.client.close_db", new_callable=AsyncMock),
    ):
        mock_init.return_value = None
        yield


# ── Integration test database setup ──────────────────────────────────────────


@pytest.fixture(scope="session")
async def integration_db(request: pytest.FixtureRequest):
    """
    Provides a real Motor database connection for integration tests.

    Uses a dedicated test database ('hospitalops_test') to avoid touching
    development or production data.

    Skips automatically if MongoDB is not reachable.
    """
    from app.core.config import get_settings
    from app.database.client import close_db, init_db, init_indexes

    settings = get_settings()

    # Override database name for tests to avoid touching development data.
    test_settings = settings.model_copy(update={"mongodb_database": "hospitalops_test"})

    try:
        await init_db(test_settings)
        await init_indexes()
    except Exception as exc:
        pytest.skip(f"MongoDB not available for integration tests: {exc}")
        return

    yield

    await close_db()
