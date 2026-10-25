from typing import Any
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.engine import ScalarResult
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.schemas.company import CompanyCreate, CompanyUpdate
from app.services.exceptions.company import (
    CompanyAlreadyExistsError,
    CompanyCreationError,
    CompanyDeletionError,
    CompanyFetchingError,
    CompanyNotFoundError,
    CompanyUpdateError,
)
from app.services.user import UserService


class CompanyService:
    """Manage companies and per-owner normalized-name uniqueness.

    Mutations flush without committing; the caller owns commit and rollback. ID-based
    operations do not authorize access.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db: AsyncSession = db

    async def get_company_by_id(self, id: UUID) -> Company:
        """Fetch a company by ID without checking ownership.

        Raise CompanyNotFoundError if absent.
        """
        try:
            company: Company | None = await self.db.get(Company, id)
            if company is None:
                raise CompanyNotFoundError(f"Company with id {id} not found.")
            return company
        except SQLAlchemyError as exc:
            raise CompanyFetchingError(f"Failed to get company: {id}") from exc

    async def get_all_companies(self, user_id: UUID | None = None) -> list[Company]:
        """List companies ordered by name and ID, optionally filtered by an existing
        owner.

        Omitting user_id returns companies for all owners; the caller must authorize
        that access.
        """
        if user_id is not None:
            await UserService(db=self.db).get_user(user_id)
        try:
            stmt: Select[tuple[Company]] = select(Company)
            if user_id is not None:
                stmt = stmt.where(Company.user_id == user_id)
            stmt = stmt.order_by(Company.name, Company.id)
            companies: ScalarResult[Company] = await self.db.scalars(stmt)
            return list(companies)
        except SQLAlchemyError as exc:
            raise CompanyFetchingError("Failed to get all companies") from exc

    async def create_company(self, new_company_data: CompanyCreate) -> Company:
        """Create a company with a normalized name unique to an existing owner.

        Known duplicates raise CompanyAlreadyExistsError. A concurrent insert can
        violate the database constraint and raise CompanyCreationError instead.
        """
        await UserService(db=self.db).get_user(new_company_data.user_id)
        try:
            normalized_name: str = " ".join(new_company_data.name.split()).casefold()
            existing_company: Company | None = await self.db.scalar(
                select(Company).where(
                    Company.normalized_name == normalized_name,
                    Company.user_id == new_company_data.user_id,
                )
            )
            if existing_company:
                raise CompanyAlreadyExistsError(
                    f"Company with name {new_company_data.name} already exists."
                )

            new_company: Company = Company(**new_company_data.model_dump())
            self.db.add(new_company)
            await self.db.flush()
            return new_company
        except SQLAlchemyError as exc:
            raise CompanyCreationError("Failed to create company") from exc

    async def delete_company(self, id: UUID) -> None:
        """Delete a company and clear company links on surviving contacts and roles."""
        company: Company = await self.get_company_by_id(id=id)
        try:
            await self.db.delete(company)
            await self.db.flush()
        except SQLAlchemyError as exc:
            raise CompanyDeletionError(f"Failed to delete company: {id}") from exc

    async def update_company(self, id: UUID, company_data: CompanyUpdate) -> Company:
        """Apply supplied changes while preserving per-owner name uniqueness.

        Omitted fields remain unchanged; explicit null clears nullable fields. Known
        duplicate names raise CompanyAlreadyExistsError; a concurrent rename can raise
        CompanyUpdateError instead.
        """
        company: Company = await self.get_company_by_id(id=id)
        try:
            updated_company_data: dict[str, Any] = company_data.model_dump(
                exclude_unset=True
            )
            new_name: str | None = company_data.name
            if "name" in updated_company_data and new_name is not None:
                normalized_name: str = " ".join(new_name.split()).casefold()
                existing_company: Company | None = await self.db.scalar(
                    select(Company).where(
                        Company.user_id == company.user_id,
                        Company.normalized_name == normalized_name,
                        Company.id != id,
                    )
                )
                if existing_company is not None:
                    raise CompanyAlreadyExistsError(
                        f"Company with name {company_data.name} already exists."
                    )
            for field, attr in updated_company_data.items():
                setattr(company, field, attr)
            await self.db.flush()
            await self.db.refresh(company)
            return company
        except SQLAlchemyError as exc:
            raise CompanyUpdateError(
                f"Failed to update company with the following data: {company_data}"
            ) from exc
