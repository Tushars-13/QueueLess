"""Shared pytest fixtures.

Auth integration tests run against an isolated local PostgreSQL database
(``queueless_test``) so the app's real database is never touched. The test
database is created on demand and migrated to ``head`` once per session, and
the ``users`` table is truncated before every test for isolation.
"""

import asyncio
import os
import subprocess
import sys
from pathlib import Path

import pytest

# Point every app module at the isolated test database BEFORE importing it.
os.environ["DATABASE_NAME"] = "queueless_test"

from sqlalchemy import text  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.db.session import async_session_factory  # noqa: E402

BACKEND_DIR = Path(__file__).resolve().parents[1]
TEST_DATABASE_NAME = "queueless_test"


async def _ensure_test_database() -> None:
    """Create the test database on the local PostgreSQL instance if needed."""
    import asyncpg

    settings = get_settings()
    conn = await asyncpg.connect(
        user=settings.database_user,
        password=settings.database_password,
        host=settings.database_host,
        port=settings.database_port,
        database="postgres",
    )
    try:
        # asyncpg 0.30 runs statements in autocommit by default, so CREATE
        # DATABASE (which cannot run inside a transaction) is safe here.
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", TEST_DATABASE_NAME
        )
        if not exists:
            await conn.execute(f'CREATE DATABASE "{TEST_DATABASE_NAME}"')
    finally:
        await conn.close()


def _migrate_test_database() -> None:
    """Apply all migrations to the test database (idempotent)."""
    env = {**os.environ, "DATABASE_NAME": TEST_DATABASE_NAME}
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=str(BACKEND_DIR),
        env=env,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "Failed to migrate test database:\n"
            f"{result.stdout}\n{result.stderr}"
        )


@pytest.fixture(scope="session", autouse=True)
def prepared_database() -> None:
    """Ensure the test database exists with the schema at ``head``."""
    asyncio.run(_ensure_test_database())
    _migrate_test_database()
    yield


@pytest.fixture(autouse=True)
async def clean_db(prepared_database: None) -> None:
    """Truncate tables before each test for full isolation (FK-safe order)."""
    async with async_session_factory() as session:
        for table in ("business_hours", "businesses", "users"):
            await session.execute(text(f"DELETE FROM {table}"))
        await session.commit()
    yield


@pytest.fixture
def app():
    from app.main import create_app

    return create_app()


@pytest.fixture
async def client(app):
    from httpx import ASGITransport, AsyncClient

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c