"""
HospitalOps AI — Database integration tests.

These tests require a real MongoDB connection and are marked
with @pytest.mark.integration. They are automatically SKIPPED
if MongoDB is not available.

Run integration tests explicitly:
    pytest tests/test_database.py -m integration -v

Or with the standard test suite (skipped automatically if no MongoDB):
    pytest tests/ -v

Tests validate:
  - MongoDB connection and authentication
  - Ping (server response)
  - Index creation (idempotent)
  - Test collection create/read/cleanup
  - Application does NOT touch development/production collections

Fixture design:
  Motor AsyncIOMotorClient binds to the running event loop at creation time.
  Using module- or session-scoped async fixtures causes "Future attached to a
  different loop" errors because each test gets its own event loop with
  asyncio_mode="auto" and asyncio_default_fixture_loop_scope="function".

  Solution: use function-scoped pytest_asyncio fixtures so the Motor client
  is created fresh in the same event loop as the test that uses it.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import get_settings

# ── Constants ─────────────────────────────────────────────────────────────────

TEST_DB_NAME = "hospitalops_test"
TEST_COLLECTION = "integration_test_probe"


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture(scope="function", loop_scope="function")
async def test_mongo_client():
    """
    Create a fresh Motor client for each test function.

    Function scope ensures the client is created and closed within the same
    event loop as the test, preventing "Future attached to a different loop"
    errors that arise with module- or session-scoped Motor clients.

    Skips the test if MongoDB is not reachable.
    """
    settings = get_settings()

    client = AsyncIOMotorClient(
        settings.mongodb_uri,
        serverSelectionTimeoutMS=3_000,
        connectTimeoutMS=3_000,
    )

    try:
        await client.admin.command("ping")
    except Exception as exc:
        client.close()
        pytest.skip(f"MongoDB not available: {exc}")
        return

    try:
        yield client
    finally:
        client.close()


@pytest_asyncio.fixture(scope="function", loop_scope="function")
async def test_db(test_mongo_client: AsyncIOMotorClient):  # type: ignore[type-arg]
    """
    Return the integration test database.

    Uses a dedicated 'hospitalops_test' database — never touches development data.
    Drops the test collection after each test so independent tests don't
    interfere with one another.
    """
    db = test_mongo_client[TEST_DB_NAME]

    yield db

    # Per-test cleanup: drop the probe collection so each test starts clean.
    await db.drop_collection(TEST_COLLECTION)


# ── Tests ─────────────────────────────────────────────────────────────────────


@pytest.mark.integration
class TestMongoDBConnection:
    """Tests for basic MongoDB connectivity."""

    async def test_ping_succeeds(self, test_db) -> None:
        """MongoDB should respond to a ping command."""
        result = await test_db.command("ping")
        assert result.get("ok") == 1.0

    async def test_database_name_is_test(self, test_db) -> None:
        """Verify we are operating on the test database, not production."""
        assert test_db.name == TEST_DB_NAME

    async def test_can_list_collections(self, test_db) -> None:
        """Should be able to list collections (even if empty)."""
        collections = await test_db.list_collection_names()
        assert isinstance(collections, list)


@pytest.mark.integration
class TestIndexCreation:
    """Tests for index creation on core collections."""

    async def test_create_index_on_test_collection(self, test_db) -> None:
        """Verify that index creation works on the test database."""
        from pymongo import ASCENDING

        await test_db[TEST_COLLECTION].create_index(
            [("test_field", ASCENDING)],
            name="test_field_idx",
        )

        indexes = await test_db[TEST_COLLECTION].index_information()
        assert "test_field_idx" in indexes

    async def test_index_creation_is_idempotent(self, test_db) -> None:
        """Creating the same index twice should not raise an error."""
        from pymongo import ASCENDING

        for _ in range(2):
            await test_db[TEST_COLLECTION].create_index(
                [("idempotent_field", ASCENDING)],
                name="idempotent_idx",
            )

        indexes = await test_db[TEST_COLLECTION].index_information()
        assert "idempotent_idx" in indexes


@pytest.mark.integration
class TestApplicationIndexes:
    """
    Tests that application indexes can be created via the database client.
    Uses the test database — never touches development data.
    """

    async def test_application_init_indexes_runs(self, test_mongo_client) -> None:  # type: ignore[type-arg]
        """
        init_indexes() should complete without error on the test database.

        Strategy: temporarily point the database client at the test database,
        run init_indexes, then restore state.
        The test_mongo_client fixture is function-scoped, so it is guaranteed
        to run in the same event loop as this test.
        """
        import app.database.client as db_module

        original_db = db_module._database
        original_client = db_module._client

        # Point the application client module at the test database.
        db_module._client = test_mongo_client
        db_module._database = test_mongo_client[TEST_DB_NAME]

        try:
            await db_module.init_indexes()
        finally:
            # Always restore original state regardless of test outcome.
            db_module._client = original_client
            db_module._database = original_db

    async def test_core_collection_indexes_exist_after_init(self, test_mongo_client) -> None:  # type: ignore[type-arg]
        """After init_indexes, all core collections should have their indexes."""
        import app.database.client as db_module

        original_db = db_module._database
        original_client = db_module._client

        db_module._client = test_mongo_client
        db_module._database = test_mongo_client[TEST_DB_NAME]

        try:
            await db_module.init_indexes()

            # Spot check: departments should have a unique code index
            dept_indexes = await test_mongo_client[TEST_DB_NAME]["departments"].index_information()
            assert "departments_code_unique" in dept_indexes

            # Spot check: admissions should have status+admitted_at index
            adm_indexes = await test_mongo_client[TEST_DB_NAME]["admissions"].index_information()
            assert "admissions_status_admitted_at" in adm_indexes

            # Spot check: audit_logs should have entity index
            audit_indexes = await test_mongo_client[TEST_DB_NAME]["audit_logs"].index_information()
            assert "audit_logs_entity" in audit_indexes

        finally:
            db_module._client = original_client
            db_module._database = original_db


@pytest.mark.integration
class TestCrudProbe:
    """Lightweight CRUD probe to verify the database is writable."""

    async def test_insert_and_retrieve_document(self, test_db) -> None:
        """Insert a document and retrieve it by _id."""
        from datetime import UTC, datetime

        doc = {
            "probe_type": "chunk_1_1_validation",
            "inserted_at": datetime.now(tz=UTC),
            "data": "ok",
        }

        result = await test_db[TEST_COLLECTION].insert_one(doc)
        assert result.inserted_id is not None

        retrieved = await test_db[TEST_COLLECTION].find_one({"_id": result.inserted_id})
        assert retrieved is not None
        assert retrieved["probe_type"] == "chunk_1_1_validation"

    async def test_delete_document(self, test_db) -> None:
        """Verify documents can be deleted (cleanup verification)."""
        from datetime import UTC, datetime

        doc = {"cleanup_test": True, "ts": datetime.now(tz=UTC)}
        result = await test_db[TEST_COLLECTION].insert_one(doc)

        delete_result = await test_db[TEST_COLLECTION].delete_one({"_id": result.inserted_id})
        assert delete_result.deleted_count == 1

        retrieved = await test_db[TEST_COLLECTION].find_one({"_id": result.inserted_id})
        assert retrieved is None
