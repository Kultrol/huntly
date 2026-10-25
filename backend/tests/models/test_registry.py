from sqlalchemy.orm import configure_mappers

from app.core.database import Base
from app.models import (
    Event,
    StatusHistory,
    TrackedRoleContact,
    TrackedRoleContactAssociation,
    TrackedRoleEvent,
    TrackedRoleStatusHistory,
)


# Importing the model package registers all domain tables and resolves relationships.
def test_models_register_all_domain_tables():
    assert set(Base.metadata.tables) == {
        "users",
        "companies",
        "contacts",
        "tracked_roles",
        "status_history",
        "tracked_role_events",
        "event_status_histories",
        "tracked_role_contact_associations",
    }
    configure_mappers()
    assert len(Base.registry.mappers) == 8


# Compatibility names refer to the same classes without creating extra mappings.
def test_model_compatibility_aliases_share_the_same_mapper():
    assert Event is TrackedRoleEvent
    assert TrackedRoleStatusHistory is StatusHistory
    assert TrackedRoleContactAssociation is TrackedRoleContact
