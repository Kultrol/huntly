"""Authenticated company endpoints with owner-scoped access."""

from typing import Annotated
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

from app.api.ownership import require_owned_resource, validate_supplied_owner
from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.company import Company
from app.models.user import User
from app.schemas.company import CompanyCreate, CompanyRead, CompanyUpdate
from app.schemas.resource_requests import CompanyCreateRequest
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
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[Company]:
    """List the signed-in user's companies, ordered by name and UUID."""
    async with db.begin():
        company_service: CompanyService = CompanyService(db)
        try:
            return await company_service.get_all_companies(current_user.id)
        except UserNotFoundError as exc:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND, detail=str(exc)
            ) from exc
        except (CompanyServiceError, UserServiceError) as exc:
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
            ) from exc


@router.get("/{id}", response_model=CompanyRead)
async def get_company(
    id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Company:
    """Retrieve a company by UUID after checking the signed-in user's ownership."""
    async with db.begin():
        await require_owned_resource(db, Company, id, current_user.id)
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
    new_company: CompanyCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Company:
    """Create a company for the signed-in user with a name unique to that owner."""
    validate_supplied_owner(new_company.user_id, current_user.id)
    service_data = new_company.model_dump()
    service_data["user_id"] = current_user.id
    service_input = CompanyCreate.model_validate(service_data)
    async with db.begin():
        company_service: CompanyService = CompanyService(db)
        try:
            return await company_service.create_company(service_input)
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
async def delete_company(
    id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    """Delete a company and clear its links on surviving contacts and roles."""
    async with db.begin():
        await require_owned_resource(db, Company, id, current_user.id)
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
    id: UUID,
    company_data: CompanyUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Company:
    """Apply supplied changes; omitted fields remain unchanged.

    Explicit null clears nullable fields. A name must remain unique to its owner.
    """
    async with db.begin():
        await require_owned_resource(db, Company, id, current_user.id)
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
