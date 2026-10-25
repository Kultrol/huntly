"""Company endpoints with request-owned transactions.

List queries filter by user ID. Individual operations do not authenticate callers or check
ownership.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import (
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

from app.core.database import get_db
from app.models.company import Company
from app.schemas.company import CompanyCreate, CompanyRead, CompanyUpdate
from app.services.company import CompanyService
from app.services.exceptions.company import (
    CompanyAlreadyExistsError,
    CompanyNotFoundError,
    CompanyServiceError,
)
from app.services.exceptions.user import UserNotFoundError, UserServiceError

router: APIRouter = APIRouter(prefix="/companies", tags=["companies"])


@router.get("/", response_model=list[CompanyRead])
async def get_companies(
    user_id: UUID, db: AsyncSession = Depends(get_db)
) -> list[Company]:
    """List an existing user's companies, ordered by name and UUID."""
    async with db.begin():
        company_service: CompanyService = CompanyService(db)
        try:
            return await company_service.get_all_companies(user_id)
        except UserNotFoundError as exc:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND, detail=str(exc)
            ) from exc
        except (CompanyServiceError, UserServiceError) as exc:
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
            ) from exc


@router.get("/{id}", response_model=CompanyRead)
async def get_company(id: UUID, db: AsyncSession = Depends(get_db)) -> Company:
    """Retrieve a company by UUID."""
    async with db.begin():
        company_service: CompanyService = CompanyService(db)
        try:
            return await company_service.get_company_by_id(id)
        except CompanyNotFoundError as exc:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND, detail=str(exc)
            ) from exc
        except CompanyServiceError as exc:
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
            ) from exc


@router.post("/", response_model=CompanyRead, status_code=HTTP_201_CREATED)
async def create_company(
    new_company: CompanyCreate, db: AsyncSession = Depends(get_db)
) -> Company:
    """Create a company with a normalized name unique to its owner."""
    async with db.begin():
        company_service: CompanyService = CompanyService(db)
        try:
            return await company_service.create_company(new_company)
        except UserNotFoundError as exc:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND, detail=str(exc)
            ) from exc
        except CompanyAlreadyExistsError as exc:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST, detail=str(exc)
            ) from exc
        except (CompanyServiceError, UserServiceError) as exc:
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
            ) from exc


@router.delete("/{id}", status_code=HTTP_204_NO_CONTENT)
async def delete_company(id: UUID, db: AsyncSession = Depends(get_db)) -> None:
    """Delete a company and clear its links on surviving contacts and roles."""
    async with db.begin():
        company_service: CompanyService = CompanyService(db)
        try:
            await company_service.delete_company(id)
        except CompanyNotFoundError as exc:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND, detail=str(exc)
            ) from exc
        except CompanyServiceError as exc:
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
            ) from exc


@router.patch("/{id}", response_model=CompanyRead)
async def update_company(
    id: UUID, company_data: CompanyUpdate, db: AsyncSession = Depends(get_db)
) -> Company:
    """Apply supplied changes; omitted fields remain unchanged.

    Explicit null clears nullable fields. A name must remain unique to its owner.
    """
    async with db.begin():
        company_service: CompanyService = CompanyService(db)
        try:
            return await company_service.update_company(id, company_data)
        except CompanyNotFoundError as exc:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND, detail=str(exc)
            ) from exc
        except CompanyAlreadyExistsError as exc:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST, detail=str(exc)
            ) from exc
        except CompanyServiceError as exc:
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
            ) from exc
