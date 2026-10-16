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


class CompanyService:
    """Manage companies and their per-user normalized-name uniqueness.

    Attributes:
        db: Session shared with the caller's transaction.

    Notes:
        Mutations flush without committing. The caller must commit successful
        work or roll back a failed transaction. ID-based methods do not check
        ownership; the caller must authorize access to the requested company.
    """

    def __init__(self, db: AsyncSession) -> None:
        """Bind the service to an existing session.

        Args:
            db: Session whose transaction remains the caller's responsibility.

        Returns:
            None.

        Raises:
            None: Binding the session performs no database operation.
        """
        self.db: AsyncSession = db

    async def get_company_by_id(self, id: UUID) -> Company:
        """Fetch a company by identity without an owner filter.

        Args:
            id: Company identifier authorized by the caller.

        Returns:
            The company attached to this service's session.

        Raises:
            CompanyNotFoundError: No company exists with the supplied ID.
            CompanyFetchingError: SQLAlchemy cannot load the company.
        """
        try:
            company: Company | None = await self.db.get(Company, id)
            if company is None:
                raise CompanyNotFoundError(f"Company with id {id} not found.")
            return company
        except SQLAlchemyError as exc:
            raise CompanyFetchingError(f"Failed to get company: {id}") from exc

    async def get_all_companies(self, user_id: UUID | None = None) -> list[Company]:
        """List companies, optionally limiting results to one owner.

        Args:
            user_id: Owner to filter by; None includes every user's companies.

        Returns:
            Companies ordered by display name and ID, or an empty list.

        Raises:
            CompanyFetchingError: SQLAlchemy cannot execute the query.

        Notes:
            Omitting the owner requires the caller to authorize global access.
        """
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
        """Create a company if its normalized name is unused by its owner.

        Args:
            new_company_data: Validated company fields, including its owner.

        Returns:
            The new company after flushing it into the current transaction.

        Raises:
            CompanyAlreadyExistsError: The owner already has a company with
                the same case-folded, whitespace-normalized name.
            CompanyCreationError: SQLAlchemy cannot query or insert the company.

        Notes:
            The pre-check gives a domain error for known duplicates. A concurrent
            insert can still violate the database's unique constraint and surface
            as CompanyCreationError.
        """
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
        """Delete a company while retaining its contacts and tracked roles.

        Args:
            id: Company identifier authorized by the caller.

        Returns:
            None. The deletion is flushed and still requires a caller commit.

        Raises:
            CompanyNotFoundError: No company exists with the supplied ID.
            CompanyFetchingError: The initial company lookup fails.
            CompanyDeletionError: SQLAlchemy cannot delete the company or flush
                the deletion.

        Notes:
            Company foreign keys on retained contacts and roles become null;
            deleting the organization does not erase the user's search records.
        """
        company: Company = await self.get_company_by_id(id=id)
        try:
            await self.db.delete(company)
            await self.db.flush()
        except SQLAlchemyError as exc:
            raise CompanyDeletionError(f"Failed to delete company: {id}") from exc

    async def update_company(self, id: UUID, company_data: CompanyUpdate) -> Company:
        """Apply supplied fields while preserving per-owner name uniqueness.

        Args:
            id: Company identifier authorized by the caller.
            company_data: Validated patch; omitted fields remain unchanged and
                explicit null clears a nullable field.

        Returns:
            The updated company, flushed and refreshed in the current transaction.

        Raises:
            CompanyNotFoundError: No company exists with the supplied ID.
            CompanyFetchingError: The initial company lookup fails.
            CompanyAlreadyExistsError: Another company owned by the same user
                already has the proposed normalized name.
            CompanyUpdateError: SQLAlchemy cannot check, flush, or refresh changes.

        Notes:
            A concurrent rename can still fail the database's unique constraint
            and surface as CompanyUpdateError rather than a duplicate-name error.
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
