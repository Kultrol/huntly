"""Contact endpoints with request-owned transactions.

List queries filter by user ID. Individual operations do not authenticate callers or check
ownership.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import (
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

from app.core.database import get_db
from app.models.contact import Contact
from app.schemas.contact import ContactCreate, ContactRead, ContactUpdate
from app.services.contact import ContactService
from app.services.exceptions.contact import (
    ContactCompanyError,
    ContactNotFoundError,
    ContactServiceError,
)
from app.services.exceptions.user import UserNotFoundError, UserServiceError

router: APIRouter = APIRouter(prefix="/contacts", tags=["contacts"])


@router.get("/", response_model=list[ContactRead])
async def get_all_contacts(
    user_id: UUID, db: AsyncSession = Depends(get_db)
) -> list[Contact]:
    """List an existing user's contacts, ordered by name and UUID."""
    async with db.begin():
        contact_service: ContactService = ContactService(db)
        try:
            return await contact_service.get_all_contacts(user_id)
        except UserNotFoundError as exc:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=str(exc))
        except (ContactServiceError, UserServiceError) as exc:
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
            )


@router.get("/{id}", response_model=ContactRead)
async def get_contact(id: UUID, db: AsyncSession = Depends(get_db)) -> Contact:
    """Retrieve a contact by UUID."""
    async with db.begin():
        contact_service: ContactService = ContactService(db)
        try:
            return await contact_service.get_contact(id)
        except ContactNotFoundError as exc:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=str(exc))
        except ContactServiceError as exc:
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
            )


@router.post("/", response_model=ContactRead, status_code=HTTP_201_CREATED)
async def create_contact(
    new_contact: ContactCreate, db: AsyncSession = Depends(get_db)
) -> Contact:
    """Create a contact, optionally linked to a company owned by the same user."""
    async with db.begin():
        contact_service: ContactService = ContactService(db)
        try:
            return await contact_service.create_contact(new_contact)
        except UserNotFoundError as exc:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=str(exc))
        except ContactCompanyError as exc:
            raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(exc))
        except (ValidationError, ValueError) as exc:
            raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(exc))
        except (ContactServiceError, UserServiceError) as exc:
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
            )


@router.patch("/{id}", response_model=ContactRead)
async def update_contact(
    id: UUID, contact_data: ContactUpdate, db: AsyncSession = Depends(get_db)
) -> Contact:
    """Apply supplied changes; omitted fields remain unchanged.

    A null company ID removes the affiliation. A replacement company must belong to the
    contact owner.
    """
    async with db.begin():
        contact_service: ContactService = ContactService(db)
        try:
            return await contact_service.update_contact(id, contact_data)
        except ContactNotFoundError as exc:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=str(exc))
        except ContactCompanyError as exc:
            raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(exc))
        except (ValidationError, ValueError) as exc:
            raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(exc))
        except ContactServiceError as exc:
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
            )


@router.delete("/{id}", status_code=HTTP_204_NO_CONTENT)
async def delete_contact(id: UUID, db: AsyncSession = Depends(get_db)) -> None:
    """Delete a contact and its role associations while retaining the linked roles."""
    async with db.begin():
        contact_service: ContactService = ContactService(db)
        try:
            await contact_service.delete_contact(id)
        except ContactNotFoundError as exc:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=str(exc))
        except ContactServiceError as exc:
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
            )
