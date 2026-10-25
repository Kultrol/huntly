"""SQLAlchemy column types for the plain enums in app.enums."""

from enum import StrEnum

from sqlalchemy import Enum as SQLAlchemyEnum


def enum_type(enum_class: type[StrEnum], name: str) -> SQLAlchemyEnum:
    """Store enum values such as ``full_time`` rather than member names.

    Use a portable check constraint and reject unknown bound strings with
    ``LookupError``.
    """
    return SQLAlchemyEnum(
        enum_class,
        name=name,
        values_callable=lambda members: [member.value for member in members],
        native_enum=False,
        create_constraint=True,
        validate_strings=True,
    )
