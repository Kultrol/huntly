"""Align the empty legacy schema with Huntly V1.

Revision ID: 22017b5e84d4
Revises: 6ba2d65b164c

Requires empty tables because old records cannot be converted automatically.
Upgrade and downgrade stop if any affected table contains data.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "22017b5e84d4"
down_revision: str | Sequence[str] | None = "6ba2d65b164c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LEGACY_TABLES = (
    "companies",
    "contacts",
    "job_applications",
    "application_status_history",
    "interviews",
)
DOMAIN_TABLES = (
    "users",
    "companies",
    "contacts",
    "tracked_roles",
    "status_history",
    "tracked_role_events",
    "event_status_histories",
    "tracked_role_contact_associations",
)


def _require_empty(tables: tuple[str, ...], direction: str) -> None:
    # Block new rows until the empty check and schema changes are finished.
    op.execute("LOCK TABLE " + ", ".join(tables) + " IN ACCESS EXCLUSIVE MODE")
    for table in tables:
        op.execute(
            f"""
            DO $migration_guard$
            BEGIN
                IF EXISTS (SELECT 1 FROM {table}) THEN
                    RAISE EXCEPTION 'Cannot {direction} populated schema (table {table}). '
                        'This revision requires empty domain tables. Back up the records '
                        'and design an explicit data conversion before retrying.';
                END IF;
            END
            $migration_guard$;
            """
        )


def upgrade() -> None:
    """Upgrade only when every affected domain table is empty."""
    _require_empty(LEGACY_TABLES, "upgrade")

    # Remove empty legacy children before their parent table.
    op.drop_index(
        op.f("ix_application_status_history_application_id"),
        table_name="application_status_history",
    )
    op.drop_table("application_status_history")
    op.drop_index(op.f("ix_interviews_application_id"), table_name="interviews")
    op.drop_table("interviews")
    op.drop_index(op.f("ix_job_applications_company_id"), table_name="job_applications")
    op.drop_table("job_applications")

    # Create the ownership table before adding owner foreign keys.
    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(), nullable=False, comment="User Display Name"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Replace global company uniqueness with owner/name uniqueness.
    op.add_column("companies", sa.Column("user_id", sa.UUID(), nullable=False))
    op.add_column(
        "companies",
        sa.Column(
            "normalized_name",
            sa.String(length=255),
            nullable=False,
            comment="System-generated company name; unique within its user's workspace",
        ),
    )
    op.alter_column(
        "companies",
        "name",
        existing_type=sa.VARCHAR(length=255),
        comment="Company display name",
        existing_comment="Company display name (unique across the tracker)",
        existing_nullable=False,
    )
    op.alter_column(
        "companies",
        "website",
        existing_type=sa.VARCHAR(length=255),
        comment="Company website URL",
        existing_comment="Company website URL; unique when set",
        existing_nullable=True,
    )
    op.alter_column(
        "companies",
        "linkedin_url",
        existing_type=sa.VARCHAR(length=255),
        comment="Company LinkedIn page URL",
        existing_comment="Company LinkedIn page URL; unique when set",
        existing_nullable=True,
    )
    op.drop_constraint(op.f("companies_linkedin_url_key"), "companies", type_="unique")
    op.drop_constraint(op.f("companies_name_key1"), "companies", type_="unique")
    op.drop_constraint(op.f("companies_website_key"), "companies", type_="unique")
    op.create_unique_constraint(
        "uq_company_user_name", "companies", ["user_id", "normalized_name"]
    )
    op.create_foreign_key(
        "fk_companies_user", "companies", "users", ["user_id"], ["id"]
    )

    # Add contact ownership and preserve contacts when a company is deleted.
    op.add_column(
        "contacts",
        sa.Column("user_id", sa.UUID(), nullable=False, comment="FK to users.id"),
    )
    op.alter_column(
        "contacts",
        "company_id",
        existing_type=sa.UUID(),
        nullable=True,
        existing_comment="FK to companies.id; company this person works at / represents",
    )
    op.alter_column(
        "contacts",
        "phone_number",
        existing_type=sa.VARCHAR(length=32),
        comment="Phone number",
        existing_comment="Phone number (E.164-ish room); unique when set",
        existing_nullable=True,
    )
    op.alter_column(
        "contacts",
        "role",
        existing_type=sa.VARCHAR(length=255),
        comment="Professional title (e.g. Senior Technical Recruiter)",
        existing_comment="Job title or relationship (e.g. Recruiter, Eng Manager)",
        existing_nullable=True,
    )
    op.alter_column(
        "contacts",
        "email",
        existing_type=sa.VARCHAR(length=255),
        comment="Email address",
        existing_comment="Email address; unique when set",
        existing_nullable=True,
    )
    op.alter_column(
        "contacts",
        "linkedin_url",
        existing_type=sa.VARCHAR(length=255),
        comment="Personal LinkedIn profile URL",
        existing_comment="Personal LinkedIn profile URL; unique when set",
        existing_nullable=True,
    )
    op.drop_constraint(op.f("contacts_email_key"), "contacts", type_="unique")
    op.drop_constraint(op.f("contacts_linkedin_url_key"), "contacts", type_="unique")
    op.drop_constraint(op.f("contacts_phone_number_key"), "contacts", type_="unique")
    op.drop_constraint(op.f("contacts_company_id_fkey"), "contacts", type_="foreignkey")
    op.create_foreign_key("fk_contacts_user", "contacts", "users", ["user_id"], ["id"])
    op.create_foreign_key(
        "fk_contacts_company",
        "contacts",
        "companies",
        ["company_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Create tracked roles, with explicit status and salary checks.
    op.create_table(
        "tracked_roles",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("company_id", sa.UUID(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "saved",
                "applied",
                "screening",
                "interview",
                "offer",
                "rejected",
                "accepted",
                "withdrawn",
                name="ck_tracked_roles_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
            comment="The status of the role the user wants to track.",
        ),
        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
            comment="A description of the role the user wants to track.",
        ),
        sa.Column(
            "role_type",
            sa.Enum(
                "full_time",
                "part_time",
                "contract",
                "internship",
                "temporary",
                "other",
                name="ck_tracked_roles_role_type",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=True,
            comment="Optional employment arrangement retained alongside the V1 fields",
        ),
        sa.Column(
            "location",
            sa.String(),
            nullable=True,
            comment="The location of the role, so the office, building, or place in which the role is offered from.",
        ),
        sa.Column(
            "source",
            sa.String(),
            nullable=True,
            comment="The source of the role(i.e. a company or job posting).",
        ),
        sa.Column(
            "listing_url",
            sa.String(),
            nullable=True,
            comment="The URL of the listing for the role.",
        ),
        sa.Column(
            "priority",
            sa.Enum(
                "low",
                "medium",
                "high",
                name="ck_tracked_roles_priority",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=True,
            comment="The priority of the role the user wants to track.",
        ),
        sa.Column(
            "notes",
            sa.Text(),
            nullable=True,
            comment="Any notes or comments about the role.",
        ),
        sa.Column(
            "salary_min",
            sa.DECIMAL(),
            nullable=True,
            comment="The minimum salary for the role.",
        ),
        sa.Column(
            "salary_max",
            sa.DECIMAL(),
            nullable=True,
            comment="The maximum salary for the role.",
        ),
        sa.Column(
            "salary_currency",
            sa.String(),
            nullable=True,
            comment="Salary currency when supplied; NULL when unknown",
        ),
        sa.Column(
            "applied_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="The date and time the role was applied for.",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="When this row was first created (DB server default, timezone-aware)",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="When this row was last updated (server default + ORM onupdate)",
        ),
        sa.CheckConstraint("length(trim(title)) > 0", name="ck_tracked_roles_title"),
        sa.CheckConstraint("salary_max >= 0", name="tracked_roles_salary_max_check"),
        sa.CheckConstraint("salary_min >= 0", name="tracked_roles_salary_min_check"),
        sa.CheckConstraint(
            "salary_min IS NULL OR salary_max IS NULL OR salary_min <= salary_max",
            name="ck_tracked_roles_salary_range",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            ondelete="SET NULL",
            name="fk_tracked_roles_company",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_tracked_roles_user"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_tracked_roles_company_id"),
        "tracked_roles",
        ["company_id"],
        unique=False,
    )

    # Create dependent histories, events, and contact associations.
    op.create_table(
        "status_history",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tracked_role_id", sa.UUID(), nullable=False),
        sa.Column(
            "from_status",
            sa.Enum(
                "saved",
                "applied",
                "screening",
                "interview",
                "offer",
                "rejected",
                "accepted",
                "withdrawn",
                name="ck_status_history_from_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=True,
        ),
        sa.Column(
            "to_status",
            sa.Enum(
                "saved",
                "applied",
                "screening",
                "interview",
                "offer",
                "rejected",
                "accepted",
                "withdrawn",
                name="ck_status_history_to_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="When this row was first created (DB server default, timezone-aware)",
        ),
        sa.ForeignKeyConstraint(
            ["tracked_role_id"],
            ["tracked_roles.id"],
            ondelete="CASCADE",
            name="fk_status_history_tracked_role",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "tracked_role_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("tracked_role_id", sa.UUID(), nullable=False),
        sa.Column(
            "event_type",
            sa.Enum(
                "interview",
                "recruiter_screen",
                "assessment",
                "follow_up",
                "application_deadline",
                "offer_deadline",
                "networking",
                "custom",
                name="ck_tracked_role_events_event_type",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
            comment="The type of the event.",
        ),
        sa.Column(
            "custom_type_name",
            sa.String(),
            nullable=True,
            comment="The custom type name of the event.",
        ),
        sa.Column("event_date", sa.Date(), nullable=False),
        sa.Column("event_time", sa.Time(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "scheduled",
                "completed",
                "cancelled",
                "missed",
                name="ck_tracked_role_events_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
            comment="The status of the event.",
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("url", sa.String(), nullable=True),
        sa.Column("location", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="When this row was first created (DB server default, timezone-aware)",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="When this row was last updated (server default + ORM onupdate)",
        ),
        sa.CheckConstraint(
            "(event_type = 'custom' AND custom_type_name IS NOT NULL AND length(trim(custom_type_name)) > 0) OR (event_type <> 'custom' AND custom_type_name IS NULL)",
            name="ck_tracked_role_events_custom_type_name",
        ),
        sa.ForeignKeyConstraint(
            ["tracked_role_id"],
            ["tracked_roles.id"],
            ondelete="CASCADE",
            name="fk_tracked_role_events_tracked_role",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "event_status_histories",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("event_id", sa.UUID(), nullable=False),
        sa.Column(
            "from_status",
            sa.Enum(
                "pending",
                "scheduled",
                "completed",
                "cancelled",
                "missed",
                name="ck_event_status_histories_from_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=True,
            comment="The previous status before the status transition occurred.",
        ),
        sa.Column(
            "to_status",
            sa.Enum(
                "pending",
                "scheduled",
                "completed",
                "cancelled",
                "missed",
                name="ck_event_status_histories_to_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
            comment="The new status after the status transition occurred.",
        ),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="The actual time the status change occurred - user led",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="The timestamp when the status history was created - system generated",
        ),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["tracked_role_events.id"],
            ondelete="CASCADE",
            name="fk_event_status_histories_event",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "tracked_role_contact_associations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "relationship_type",
            sa.Enum(
                "recruiter",
                "hiring_manager",
                "interviewer",
                "referral",
                "team_member",
                "other",
                name="tracked_role_contact_relationship_type",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=True,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("tracked_role_id", sa.UUID(), nullable=False),
        sa.Column("contact_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="When this row was first created (DB server default, timezone-aware)",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="When this row was last updated (server default + ORM onupdate)",
        ),
        sa.ForeignKeyConstraint(
            ["contact_id"],
            ["contacts.id"],
            ondelete="CASCADE",
            name="fk_role_contacts_contact",
        ),
        sa.ForeignKeyConstraint(
            ["tracked_role_id"],
            ["tracked_roles.id"],
            ondelete="CASCADE",
            name="fk_role_contacts_tracked_role",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tracked_role_id", "contact_id", name="unique_tracked_role_contact"
        ),
    )
    op.create_index(
        op.f("ix_tracked_role_contact_associations_contact_id"),
        "tracked_role_contact_associations",
        ["contact_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_tracked_role_contact_associations_tracked_role_id"),
        "tracked_role_contact_associations",
        ["tracked_role_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade only when every affected domain table is empty."""
    _require_empty(DOMAIN_TABLES, "downgrade")

    # Remove empty V1 children before their parents.
    op.drop_table("event_status_histories")
    op.drop_table("tracked_role_events")
    op.drop_index(
        op.f("ix_tracked_role_contact_associations_tracked_role_id"),
        table_name="tracked_role_contact_associations",
    )
    op.drop_index(
        op.f("ix_tracked_role_contact_associations_contact_id"),
        table_name="tracked_role_contact_associations",
    )
    op.drop_table("tracked_role_contact_associations")
    op.drop_table("status_history")
    op.drop_index(op.f("ix_tracked_roles_company_id"), table_name="tracked_roles")
    op.drop_table("tracked_roles")

    # Restore the old contact/company columns and constraints.
    op.drop_constraint("fk_contacts_company", "contacts", type_="foreignkey")
    op.drop_constraint("fk_contacts_user", "contacts", type_="foreignkey")
    op.create_foreign_key(
        op.f("contacts_company_id_fkey"),
        "contacts",
        "companies",
        ["company_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_unique_constraint(
        op.f("contacts_phone_number_key"),
        "contacts",
        ["phone_number"],
        postgresql_nulls_not_distinct=False,
    )
    op.create_unique_constraint(
        op.f("contacts_linkedin_url_key"),
        "contacts",
        ["linkedin_url"],
        postgresql_nulls_not_distinct=False,
    )
    op.create_unique_constraint(
        op.f("contacts_email_key"),
        "contacts",
        ["email"],
        postgresql_nulls_not_distinct=False,
    )
    op.alter_column(
        "contacts",
        "linkedin_url",
        existing_type=sa.VARCHAR(length=255),
        comment="Personal LinkedIn profile URL; unique when set",
        existing_comment="Personal LinkedIn profile URL",
        existing_nullable=True,
    )
    op.alter_column(
        "contacts",
        "email",
        existing_type=sa.VARCHAR(length=255),
        comment="Email address; unique when set",
        existing_comment="Email address",
        existing_nullable=True,
    )
    op.alter_column(
        "contacts",
        "role",
        existing_type=sa.VARCHAR(length=255),
        comment="Job title or relationship (e.g. Recruiter, Eng Manager)",
        existing_comment="Professional title (e.g. Senior Technical Recruiter)",
        existing_nullable=True,
    )
    op.alter_column(
        "contacts",
        "phone_number",
        existing_type=sa.VARCHAR(length=32),
        comment="Phone number (E.164-ish room); unique when set",
        existing_comment="Phone number",
        existing_nullable=True,
    )
    op.alter_column(
        "contacts",
        "company_id",
        existing_type=sa.UUID(),
        nullable=False,
        existing_comment="FK to companies.id; company this person works at / represents",
    )
    op.drop_column("contacts", "user_id")
    op.drop_constraint("fk_companies_user", "companies", type_="foreignkey")
    op.drop_constraint("uq_company_user_name", "companies", type_="unique")
    op.create_unique_constraint(
        op.f("companies_website_key"),
        "companies",
        ["website"],
        postgresql_nulls_not_distinct=False,
    )
    op.create_unique_constraint(
        op.f("companies_name_key1"),
        "companies",
        ["name"],
        postgresql_nulls_not_distinct=False,
    )
    op.create_unique_constraint(
        op.f("companies_linkedin_url_key"),
        "companies",
        ["linkedin_url"],
        postgresql_nulls_not_distinct=False,
    )
    op.alter_column(
        "companies",
        "linkedin_url",
        existing_type=sa.VARCHAR(length=255),
        comment="Company LinkedIn page URL; unique when set",
        existing_comment="Company LinkedIn page URL",
        existing_nullable=True,
    )
    op.alter_column(
        "companies",
        "website",
        existing_type=sa.VARCHAR(length=255),
        comment="Company website URL; unique when set",
        existing_comment="Company website URL",
        existing_nullable=True,
    )
    op.alter_column(
        "companies",
        "name",
        existing_type=sa.VARCHAR(length=255),
        comment="Company display name (unique across the tracker)",
        existing_comment="Company display name",
        existing_nullable=False,
    )
    op.drop_column("companies", "normalized_name")
    op.drop_column("companies", "user_id")

    # Remove the ownership table after all owner foreign keys.
    op.drop_table("users")

    # Recreate empty legacy applications before their dependent tables.
    op.create_table(
        "job_applications",
        sa.Column(
            "id",
            sa.UUID(),
            autoincrement=False,
            nullable=False,
            comment="Primary key (UUID generated in the app via uuid4)",
        ),
        sa.Column(
            "company_id",
            sa.UUID(),
            autoincrement=False,
            nullable=False,
            comment="FK to companies.id; exactly one company owns this application",
        ),
        sa.Column(
            "job_title",
            sa.VARCHAR(length=255),
            autoincrement=False,
            nullable=False,
            comment="Role title (unique per company via composite constraint)",
        ),
        sa.Column(
            "job_description",
            sa.TEXT(),
            autoincrement=False,
            nullable=True,
            comment="Full or pasted job description text",
        ),
        sa.Column(
            "job_url",
            sa.VARCHAR(length=512),
            autoincrement=False,
            nullable=True,
            comment="Canonical job posting URL; unique when set",
        ),
        sa.Column(
            "job_type",
            sa.VARCHAR(length=32),
            autoincrement=False,
            nullable=False,
            comment="Employment type (JobType enum value, e.g. full_time)",
        ),
        sa.Column(
            "location",
            sa.VARCHAR(length=255),
            autoincrement=False,
            nullable=True,
            comment="Job location or remote label (not unique — many jobs share cities)",
        ),
        sa.Column(
            "salary_min",
            sa.NUMERIC(precision=12, scale=2),
            autoincrement=False,
            nullable=True,
            comment="Lower bound of expected or listed pay (Numeric 12,2)",
        ),
        sa.Column(
            "salary_max",
            sa.NUMERIC(precision=12, scale=2),
            autoincrement=False,
            nullable=True,
            comment="Upper bound of expected or listed pay (Numeric 12,2)",
        ),
        sa.Column(
            "applied_at",
            postgresql.TIMESTAMP(timezone=True),
            autoincrement=False,
            nullable=True,
            comment="When you submitted the application; null if still a wishlist item",
        ),
        sa.Column(
            "priority",
            sa.VARCHAR(length=16),
            autoincrement=False,
            nullable=True,
            comment="Personal priority in the tracker (Priority enum value)",
        ),
        sa.Column(
            "notes",
            sa.TEXT(),
            autoincrement=False,
            nullable=True,
            comment="Free-form notes for this application",
        ),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            autoincrement=False,
            nullable=False,
            comment="When this row was first created (DB server default, timezone-aware)",
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            autoincrement=False,
            nullable=False,
            comment="When this row was last updated (server default + ORM onupdate)",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            name=op.f("job_applications_company_id_fkey"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("job_applications_pkey")),
        sa.UniqueConstraint(
            "company_id",
            "job_title",
            name=op.f("uq_job_applications_company_title"),
            postgresql_include=[],
            postgresql_nulls_not_distinct=False,
        ),
        sa.UniqueConstraint(
            "job_url",
            name=op.f("job_applications_job_url_key"),
            postgresql_include=[],
            postgresql_nulls_not_distinct=False,
        ),
    )
    op.create_index(
        op.f("ix_job_applications_company_id"),
        "job_applications",
        ["company_id"],
        unique=False,
    )
    op.create_table(
        "application_status_history",
        sa.Column(
            "id",
            sa.UUID(),
            autoincrement=False,
            nullable=False,
            comment="Primary key (UUID generated in the app via uuid4)",
        ),
        sa.Column(
            "application_id",
            sa.UUID(),
            autoincrement=False,
            nullable=False,
            comment="FK to job_applications.id; application this status event belongs to",
        ),
        sa.Column(
            "status",
            sa.VARCHAR(length=32),
            autoincrement=False,
            nullable=False,
            comment="Pipeline status at this history event (ApplicationStatus enum value)",
        ),
        sa.Column(
            "notes",
            sa.TEXT(),
            autoincrement=False,
            nullable=True,
            comment="Optional context for this status change (rejection reason, etc.)",
        ),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            autoincrement=False,
            nullable=False,
            comment="When this row was first created (DB server default, timezone-aware)",
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            autoincrement=False,
            nullable=False,
            comment="When this row was last updated (server default + ORM onupdate)",
        ),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["job_applications.id"],
            name=op.f("application_status_history_application_id_fkey"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("application_status_history_pkey")),
    )
    op.create_index(
        op.f("ix_application_status_history_application_id"),
        "application_status_history",
        ["application_id"],
        unique=False,
    )
    op.create_table(
        "interviews",
        sa.Column(
            "id",
            sa.UUID(),
            autoincrement=False,
            nullable=False,
            comment="Primary key (UUID generated in the app via uuid4)",
        ),
        sa.Column(
            "application_id",
            sa.UUID(),
            autoincrement=False,
            nullable=False,
            comment="FK to job_applications.id; application this interview belongs to",
        ),
        sa.Column(
            "scheduled_at",
            postgresql.TIMESTAMP(timezone=True),
            autoincrement=False,
            nullable=False,
            comment="Interview start time (timezone-aware)",
        ),
        sa.Column(
            "interview_type",
            sa.VARCHAR(length=32),
            autoincrement=False,
            nullable=False,
            comment="Interview format/focus (InterviewType enum value, e.g. video)",
        ),
        sa.Column(
            "location",
            sa.VARCHAR(length=255),
            autoincrement=False,
            nullable=True,
            comment="Physical location or office name for onsite interviews",
        ),
        sa.Column(
            "url_link",
            sa.VARCHAR(length=512),
            autoincrement=False,
            nullable=True,
            comment="Video call or portal URL for remote interviews",
        ),
        sa.Column(
            "notes",
            sa.TEXT(),
            autoincrement=False,
            nullable=True,
            comment="Prep notes, interviewer names, takeaways, etc.",
        ),
        sa.Column(
            "outcome",
            sa.VARCHAR(length=32),
            autoincrement=False,
            nullable=True,
            comment="Result of this interview only (InterviewOutcome enum value)",
        ),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            autoincrement=False,
            nullable=False,
            comment="When this row was first created (DB server default, timezone-aware)",
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            autoincrement=False,
            nullable=False,
            comment="When this row was last updated (server default + ORM onupdate)",
        ),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["job_applications.id"],
            name=op.f("interviews_application_id_fkey"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("interviews_pkey")),
    )
    op.create_index(
        op.f("ix_interviews_application_id"),
        "interviews",
        ["application_id"],
        unique=False,
    )
