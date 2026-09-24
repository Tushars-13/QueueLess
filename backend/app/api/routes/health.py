"""Health-check endpoint."""

from typing import Any, Dict

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_db_session

router = APIRouter(tags=["health"])


def _build_status(
    database: str, *, include_detail: bool = False
) -> Dict[str, Any]:
    body: Dict[str, Any] = {
        "status": "ok",
        "app": get_settings().app_name,
        "version": get_settings().app_version,
        "environment": get_settings().app_env,
        "database": database,
    }
    if include_detail:
        body["detail"] = {"database": database}
    return body


@router.get("/health", summary="Check service health")
async def health_check(
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """Liveness probe. Also verifies the database connection."""
    try:
        await db.execute(text("SELECT 1"))
        database = "ok"
    except Exception:
        database = "error"

    if database == "error":
        # The DB dependency will have rolled back the session already.
        return _build_status(database)

    return _build_status(database, include_detail=True)