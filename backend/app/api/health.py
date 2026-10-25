from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

router: APIRouter = APIRouter(prefix="/health")


@router.get("", response_model=None)
def health() -> dict[str, str]:
    """Report API liveness without checking the database."""
    return {"status": "ok"}


@router.get("/db", response_model=None)
async def db_health(db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    """Check database connectivity, returning 503 on a database failure.

    This check does not verify migrations or application tables.
    """
    try:
        await db.execute(text("SELECT 1"))
        return {"database": "ok"}
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failure.",
        )
