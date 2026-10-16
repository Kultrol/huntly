"""HTTP endpoints for companies stored within a user's workspace.

List queries use the supplied user ID as a filter. Record lookups use only the
company ID; these handlers do not authenticate callers. Each handler owns a
transaction, while the service translates errors from its database operations.
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

router: APIRouter = APIRouter(prefix="/companies", tags=["companies"])


@router.get("/", response_model=list[CompanyRead])
async def get_companies(
    user_id: UUID, db: AsyncSession = Depends(get_db)
) -> list[Company]:
    """List companies in the specified user workspace.

    Args:
        user_id: Owner UUID used to filter company records.
        db: Injected database session; this handler opens its transaction.

    Returns:
        list[Company]: ORM companies ordered by display name and UUID, serialized
        by FastAPI as CompanyRead records; empty when no records match.

    Raises:
        SQLAlchemyError: If opening or finishing the transaction fails outside
            the service error translation.
        HTTPException: Status 500 when the company service cannot fetch the list.
    """
    async with db.begin():
        company_service: CompanyService = CompanyService(db)
        try:
            return await company_service.get_all_companies(user_id)
        except CompanyServiceError as exc:
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
            ) from exc


@router.get("/{id}", response_model=CompanyRead)
async def get_company(id: UUID, db: AsyncSession = Depends(get_db)) -> Company:
    """Retrieve a company record by its UUID.

    Args:
        id: UUID of the company to retrieve.
        db: Injected database session; this handler opens its transaction.

    Returns:
        Company: ORM company serialized by FastAPI as CompanyRead.

    Raises:
        SQLAlchemyError: If opening or finishing the transaction fails outside
            the service error translation.
        HTTPException: Status 404 when the company is absent, or status 500 when
            the company service cannot fetch it.
    """
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
    """Create a company within the supplied user workspace.

    Args:
        new_company: Validated owner, display name, and optional company details.
        db: Injected database session; this handler opens its transaction.

    Returns:
        Company: New ORM company serialized as CompanyRead with status 201.

    Raises:
        SQLAlchemyError: If opening or finishing the transaction fails outside
            the service error translation.
        HTTPException: Status 400 when the service finds an existing normalized
            name for this owner, or status 500 when the company service
            cannot create the record.

    Notes:
        Company names are compared after whitespace normalization and case folding.
        The same name may belong to different user workspaces.
    """
    # A company is a workspace record, so matching names in different users
    # represent independent records rather than a shared global company.
    async with db.begin():
        company_service: CompanyService = CompanyService(db)
        try:
            return await company_service.create_company(new_company)
        except CompanyAlreadyExistsError as exc:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST, detail=str(exc)
            ) from exc
        except CompanyServiceError as exc:
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
            ) from exc


@router.delete("/{id}", status_code=HTTP_204_NO_CONTENT)
async def delete_company(id: UUID, db: AsyncSession = Depends(get_db)) -> None:
    """Delete a company while preserving linked contacts and tracked roles.

    Args:
        id: UUID of the company to delete.
        db: Injected database session; this handler opens its transaction.

    Returns:
        None: FastAPI sends an empty response with status 204.

    Raises:
        SQLAlchemyError: If opening or finishing the transaction fails outside
            the service error translation.
        HTTPException: Status 404 when the company is absent, or status 500 when
            the company service cannot fetch or delete it.

    Notes:
        Database foreign keys clear company links on surviving contacts and roles.
    """
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
    """Apply the supplied changes to an existing company.

    Args:
        id: UUID of the company to update.
        company_data: Validated partial update; omitted fields keep their values.
        db: Injected database session; this handler opens its transaction.

    Returns:
        Company: Updated ORM company serialized by FastAPI as CompanyRead.

    Raises:
        SQLAlchemyError: If opening or finishing the transaction fails outside
            the service error translation.
        HTTPException: Status 404 when the company is absent, status 400 when a
            new name duplicates another company for this owner, or status 500
            when the company service cannot fetch or update it.

    Notes:
        Explicit null values clear nullable fields; the company name cannot be null.
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
