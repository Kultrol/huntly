from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.company import CreateCompany, ReadCompany

# from app.services.company import create_company, get_one_company_by_name

router = APIRouter(prefix="/companies", tags=["companies"])


@router.post("/", response_model=ReadCompany)
def create_new_company(
    company_in: CreateCompany,
    db: Session = Depends(get_db),  # noqa: B008
):
    return create_company(db=db, company_in=company_in)


@router.get("/", response_model=ReadCompany)
def get_company(name: str, db: Session = Depends(get_db)):  # noqa: B008
    return get_one_company_by_name(db=db, company_name=name)
