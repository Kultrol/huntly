from typing import Any
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.engine import ScalarResult
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.models.contact import Contact
from app.schemas.contact import ContactCreate, ContactUpdate
from app.services.exceptions.contact import (
    ContactCompanyError,
    ContactCreationError,
    ContactDeletionError,
    ContactFetchingError,
    ContactNotFoundError,
    ContactUpdateError,
)
from app.services.user import UserService


class ContactService:
    """Manage contacts and optional company links within the same owner.

    Mutations flush without committing; the caller owns commit and rollback. ID-based
    operations do not authorize access.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db: AsyncSession = db

    async def get_contact(self, id: UUID) -> Contact:
        """Fetch a contact by ID without checking ownership.

        Raise ContactNotFoundError if absent.
        """
        try:
            contact: Contact | None = await self.db.get(Contact, id)
            if contact is None:
                raise ContactNotFoundError(f"Contact with id {id} not found.")
            return contact
        except SQLAlchemyError as exc:
            raise ContactFetchingError(f"Failed to get contact: {id}") from exc

    async def get_all_contacts(self, user_id: UUID) -> list[Contact]:
        """List an existing user's contacts, ordered by name and ID."""
        await UserService(db=self.db).get_user(user_id)
        try:
            stmt: Select[tuple[Contact]] = (
                select(Contact)
                .where(Contact.user_id == user_id)
                .order_by(Contact.name, Contact.id)
            )
            contacts: ScalarResult[Contact] = await self.db.scalars(stmt)
            return list(contacts)
        except SQLAlchemyError as exc:
            raise ContactFetchingError("Failed to get all contacts") from exc

    async def create_contact(self, contact_data: ContactCreate) -> Contact:
        """Create a contact for an existing owner, optionally linked to a company.

        A missing company or one owned by another user raises ContactCompanyError. The
        owner ID must be authorized by the caller.
        """
        await UserService(db=self.db).get_user(contact_data.user_id)
        try:
            if contact_data.company_id is not None:
                stmt: Select[tuple[Company]] = select(Company).where(
                    Company.id == contact_data.company_id,
                    Company.user_id == contact_data.user_id,
                )
                company: Company | None = await self.db.scalar(stmt)
                if company is None:
                    raise ContactCompanyError(
                        "Company must belong to the contact's user."
                    )

            new_contact: Contact = Contact(**contact_data.model_dump())
            self.db.add(new_contact)
            await self.db.flush()
            return new_contact
        except SQLAlchemyError as exc:
            raise ContactCreationError("Failed to create contact") from exc

    async def update_contact(self, id: UUID, contact_data: ContactUpdate) -> Contact:
        """Apply supplied changes and validate any replacement company against the
        contact owner.

        Omitted fields remain unchanged. Explicit null clears nullable fields, including
        company_id.
        """
        contact: Contact = await self.get_contact(id)
        try:
            updated_contact_data: dict[str, Any] = contact_data.model_dump(
                exclude_unset=True
            )

            if contact_data.company_id is not None:
                stmt: Select[tuple[Company]] = select(Company).where(
                    Company.id == contact_data.company_id,
                    Company.user_id == contact.user_id,
                )
                company: Company | None = await self.db.scalar(stmt)
                if company is None:
                    raise ContactCompanyError(
                        "Company must belong to the contact's user."
                    )

            for field, value in updated_contact_data.items():
                setattr(contact, field, value)
            await self.db.flush()
            await self.db.refresh(contact)
            return contact
        except SQLAlchemyError as exc:
            raise ContactUpdateError(f"Failed to update contact: {id}") from exc

    async def delete_contact(self, id: UUID) -> None:
        """Delete a contact and its role associations, retaining companies and roles."""
        contact: Contact = await self.get_contact(id)
        try:
            await self.db.delete(contact)
            await self.db.flush()
        except SQLAlchemyError as exc:
            raise ContactDeletionError(f"Failed to delete contact: {id}") from exc
