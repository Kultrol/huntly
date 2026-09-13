from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.database import get_db

router = APIRouter(prefix="/health")


@router.get("")
def health():
    return {"status": "ok"}


@router.get("/db")
def db_health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"database": "ok"}
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failure.",
        )
