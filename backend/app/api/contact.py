"""Authenticated contact endpoints with owner-scoped access."""

from typing import Annotated
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

from app.api.ownership import require_owned_resource, validate_supplied_owner
from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.contact import Contact
from app.models.user import User
from app.schemas.contact import ContactCreate, ContactRead, ContactUpdate
from app.schemas.resource_requests import ContactCreateRequest
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
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[Contact]:
    """List the signed-in user's contacts, ordered by name and UUID."""
    async with db.begin():
        contact_service: ContactService = ContactService(db)
        try:
            return await contact_service.get_all_contacts(current_user.id)
        except UserNotFoundError as exc:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=str(exc))
        except (ContactServiceError, UserServiceError) as exc:
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
            )


@router.get("/{id}", response_model=ContactRead)
async def get_contact(
    id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Contact:
    """Retrieve a contact by UUID after checking the signed-in user's ownership."""
    async with db.begin():
        await require_owned_resource(db, Contact, id, current_user.id)
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
    new_contact: ContactCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Contact:
    """Create a contact for the signed-in user, optionally linked to their company."""
    validate_supplied_owner(new_contact.user_id, current_user.id)
    service_data = new_contact.model_dump()
    service_data["user_id"] = current_user.id
    service_input = ContactCreate.model_validate(service_data)
    async with db.begin():
        contact_service: ContactService = ContactService(db)
        try:
            return await contact_service.create_contact(service_input)
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
    id: UUID,
    contact_data: ContactUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Contact:
    """Apply supplied changes; omitted fields remain unchanged.

    A null company ID removes the affiliation. A replacement company must belong to the
    contact owner.
    """
    async with db.begin():
        await require_owned_resource(db, Contact, id, current_user.id)
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
async def delete_contact(
    id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    """Delete a contact and its role associations while retaining the linked roles."""
    async with db.begin():
        await require_owned_resource(db, Contact, id, current_user.id)
        contact_service: ContactService = ContactService(db)
        try:
            await contact_service.delete_contact(id)
        except ContactNotFoundError as exc:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=str(exc))
        except ContactServiceError as exc:
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
            )
