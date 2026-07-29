"""full domain models cleanup

Revision ID: bb99e7312ea9
Revises: b8cd22a31fee
Create Date: 2026-07-29 13:50:25.228195

Companies previously used INTEGER serial PKs; the ORM now uses UUIDs.
This revision rebuilds companies with UUID ids (preserving names), then
creates contacts, job_applications, interviews, and application_status_history.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "bb99e7312ea9"
down_revision: str | Sequence[str] | None = "b8cd22a31fee"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # gen_random_uuid() is built into modern Postgres (pgcrypto not required on PG13+).
    op.execute(sa.text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))

    # --- companies: INTEGER id → UUID id, add domain columns ---
    op.rename_table("companies", "companies_old")

    op.create_table(
        "companies",
        sa.Column("id", sa.Uuid(), nullable=False, comment="Primary key"),
        sa.Column(
            "name",
            sa.String(length=255),
            nullable=False,
            comment="Company display name",
        ),
        sa.Column(
            "website",
            sa.String(length=255),
            nullable=True,
            comment="Company website URL",
        ),
        sa.Column(
            "linkedin_url",
            sa.String(length=255),
            nullable=True,
            comment="Company LinkedIn URL",
        ),
        sa.Column(
            "location",
            sa.String(length=255),
            nullable=True,
            comment="HQ or primary location",
        ),
        sa.Column(
            "notes",
            sa.Text(),
            nullable=True,
            comment="Free-form notes about the company",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
        sa.UniqueConstraint("website"),
        sa.UniqueConstraint("linkedin_url"),
    )

    op.execute(
        sa.text(
            """
            INSERT INTO companies (id, name)
            SELECT gen_random_uuid(), name
            FROM companies_old
            """
        )
    )
    op.drop_table("companies_old")

    # --- child tables (UUID FKs) ---
    op.create_table(
        "contacts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("phone_number", sa.String(length=32), nullable=True),
        sa.Column("role", sa.String(length=255), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("linkedin_url", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["company_id"], ["companies.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("linkedin_url"),
        sa.UniqueConstraint("phone_number"),
    )
    op.create_index(
        op.f("ix_contacts_company_id"), "contacts", ["company_id"], unique=False
    )

    op.create_table(
        "job_applications",
        sa.Column("id", sa.Uuid(), nullable=False, comment="Primary key"),
        sa.Column(
            "company_id",
            sa.Uuid(),
            nullable=False,
            comment="Owning company (exactly one per application)",
        ),
        sa.Column("job_title", sa.String(length=255), nullable=False),
        sa.Column("job_description", sa.Text(), nullable=True),
        sa.Column("job_url", sa.String(length=512), nullable=True),
        sa.Column("job_type", sa.String(length=32), nullable=False),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("salary_min", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("salary_max", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("priority", sa.String(length=16), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["company_id"], ["companies.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "company_id", "job_title", name="uq_job_applications_company_title"
        ),
        sa.UniqueConstraint("job_url"),
    )
    op.create_index(
        op.f("ix_job_applications_company_id"),
        "job_applications",
        ["company_id"],
        unique=False,
    )

    op.create_table(
        "application_status_history",
        sa.Column("id", sa.Uuid(), nullable=False, comment="Primary key"),
        sa.Column("application_id", sa.Uuid(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            comment="Status recorded at this history point",
        ),
        sa.Column(
            "notes",
            sa.Text(),
            nullable=True,
            comment="Optional notes for this status change",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["application_id"], ["job_applications.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_application_status_history_application_id"),
        "application_status_history",
        ["application_id"],
        unique=False,
    )

    op.create_table(
        "interviews",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("application_id", sa.Uuid(), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("interview_type", sa.String(length=32), nullable=False),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("url_link", sa.String(length=512), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("outcome", sa.String(length=32), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["application_id"], ["job_applications.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_interviews_application_id"),
        "interviews",
        ["application_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_interviews_application_id"), table_name="interviews")
    op.drop_table("interviews")
    op.drop_index(
        op.f("ix_application_status_history_application_id"),
        table_name="application_status_history",
    )
    op.drop_table("application_status_history")
    op.drop_index(
        op.f("ix_job_applications_company_id"), table_name="job_applications"
    )
    op.drop_table("job_applications")
    op.drop_index(op.f("ix_contacts_company_id"), table_name="contacts")
    op.drop_table("contacts")

    op.rename_table("companies", "companies_new")
    op.create_table(
        "companies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    # Downgrade cannot restore original integer ids; reassign serial ids.
    op.execute(
        sa.text(
            """
            INSERT INTO companies (name)
            SELECT name FROM companies_new
            """
        )
    )
    op.drop_table("companies_new")
