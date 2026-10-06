# Huntly V1 Domain Specification

## 1. Purpose

This document defines the V1 domain model and business rules for Huntly.

Huntly is a multi-user web application for tracking job and career opportunities throughout their lifecycle, from initial interest through application, interviews, offers, rejection, withdrawal, or acceptance.

Each authenticated user operates within their own private Huntly workspace. Data belonging to one user must not be visible to or mutable by another user.

The V1 domain contains the following primary entities and associations:

- `User`
- `TrackedRole`
- `Company`
- `Event`
- `TrackedRoleStatusHistory`
- `EventStatusHistory`
- `Contact`
- `TrackedRoleContact`

---

# 2. Common Entity Behavior

Unless otherwise specified, persistent entities have:

- `id` — UUID, required, system-generated
- `created_at` — datetime, required, system-generated
- `updated_at` — datetime, required, system-maintained

History entities are append-only records and therefore do not require `updated_at`.

User ownership applies throughout the domain.

A user may only query, modify, associate, or delete entities that belong to that user.

---

# 3. User Ownership

A `User` represents an authenticated Huntly account.

The authentication mechanism itself is outside the scope of this domain specification.

The following entities belong directly to a user:

- `TrackedRole`
- `Company`
- `Contact`

Therefore, each contains a required `user_id`.

Other entities inherit ownership through their parent relationships:

```text
Event
→ TrackedRole
→ User

TrackedRoleStatusHistory
→ TrackedRole
→ User

EventStatusHistory
→ Event
→ TrackedRole
→ User

TrackedRoleContact
→ TrackedRole / Contact
→ User
```

A `TrackedRoleContact` association may only be created when the `TrackedRole` and `Contact` belong to the same user.

Company normalization, duplicate detection, autocomplete, and all other lookups must be scoped to the authenticated user.

---

# 4. TrackedRole

A `TrackedRole` represents a job or career opportunity that a user wants to track.

A tracked role may exist before the user has formally applied.

## Attributes

- `user_id` — required → `ForeignKey[User]`
- `title` — required → `string`
- `status` — required → `TrackedRoleStatus`
- `description` — optional → `Text | Null`
- `company_id` — optional → `ForeignKey[Company] | Null`
- `location` — optional → `string | Null`
- `source` — optional → `string | Null`
- `listing_url` — optional → `string | Null`
- `priority` — optional → `Priority | Null`
- `notes` — optional → `Text | Null`
- `salary_min` — optional → `Decimal | Null`
- `salary_max` — optional → `Decimal | Null`
- `salary_currency` — optional → `string | Null`
- `applied_at` — optional → `datetime | Null`

## Relationships

A `TrackedRole`:

- belongs to one `User`;
- optionally belongs to one `Company`;
- has zero or more `Events`;
- has zero or more `TrackedRoleStatusHistory` records;
- may be associated with zero or more `Contacts` through `TrackedRoleContact`.

## Required Creation Data

Creating a `TrackedRole` requires:

- `title`
- `status`

No default status exists.

The user must explicitly choose a valid canonical status.

The title must remain meaningful after whitespace normalization. Empty or whitespace-only titles are invalid.

## Company Behavior

A company is optional.

If no company is supplied:

```text
company_id = NULL
```

The frontend may display this as `Unknown Company`, `Unassigned`, or similar language, but no artificial "Unknown Company" record is created.

If the user selects an existing company, the existing `Company.id` is assigned.

If the user enters a genuinely new company, Huntly creates that `Company` and associates the new record with the `TrackedRole`.

## Update Behavior

Updating a `TrackedRole` is partial.

An omitted optional field retains its existing value.

An explicitly cleared nullable field becomes `NULL`.

For example:

```text
field omitted
→ leave unchanged

field explicitly set to null
→ clear existing value
```

Updating a company may:

- associate an existing Company;
- create and associate a new Company;
- remove the current Company association.

## Canonical Statuses

`TrackedRoleStatus` contains:

```text
SAVED
APPLIED
SCREENING
INTERVIEW
OFFER
ACCEPTED
REJECTED
WITHDRAWN
```

Statuses represent broad lifecycle stages.

Huntly does not enforce a rigid transition graph. Users may skip stages when reality requires it.

For example:

```text
SAVED → APPLIED → REJECTED
```

and:

```text
APPLIED → INTERVIEW
```

are both valid.

## Initial Status History

Creating a `TrackedRole` creates an initial `TrackedRoleStatusHistory` record:

```text
from_status = NULL
to_status   = initial TrackedRole.status
```

Its `occurred_at` value defaults to the creation/effective time but may be backdated by the user to reflect historical data.

## Status Changes

Changing to a different status creates a new history record.

Assigning the existing status again does not create a duplicate history entry.

Status history is append-only.

Users may backdate a status transition when entering historical information.

## Applied Date

If a role is created with:

```text
status = APPLIED
```

then:

```text
applied_at = effective date/time of the initial APPLIED status
```

If an existing role enters `APPLIED` for the first time:

```text
applied_at = effective date/time of that transition
```

The user may correct this value.

If a role is imported or created directly at a later stage such as:

```text
SCREENING
INTERVIEW
OFFER
```

Huntly must not invent an application date.

Instead:

```text
applied_at = NULL
```

and the user may optionally provide it.

Later status transitions do not overwrite `applied_at`.

For example:

```text
APPLIED → SAVED → APPLIED
```

does not replace the original application date unless the user explicitly edits it.

## Priority

Priority represents the user's perceived importance of the opportunity.

Canonical values:

```text
LOW
MEDIUM
HIGH
```

Priority is optional.

`NULL` means the user has not assigned a priority.

## Salary Rules

Salary values use decimal semantics.

The backend should preserve salary values using `Decimal`, with an appropriate exact decimal/numeric representation in PostgreSQL.

Rules:

```text
salary_min >= 0
salary_max >= 0

if both are present:
salary_min <= salary_max
```

One-sided ranges are allowed.

For example:

```text
salary_min = 90000
salary_max = NULL
```

may represent "$90,000+".

## Duplicate Behavior

Duplicate `TrackedRoles` are permitted.

Two legitimate job postings may share:

- company;
- title;
- location;
- or other similar information.

Huntly should therefore detect and warn about possible duplicates rather than enforce a uniqueness constraint.

Possible duplicate signals may include:

- identical listing URL;
- same Company and normalized title;
- same normalized title without a known Company.

Duplicate checking must only consider the current user's data.

The database should be queried for likely matches rather than requiring the entire dataset to be loaded into application memory.

The user ultimately decides whether to create the potentially duplicate record.

## Deletion

Deleting a `TrackedRole` deletes:

```text
TrackedRole
├── TrackedRoleStatusHistory
├── Events
│   └── EventStatusHistory
└── TrackedRoleContact associations
```

Deleting a `TrackedRole` does not delete:

- associated `Contacts`;
- associated `Company`.

---

# 5. Company

A `Company` represents an organization associated with one or more tracked roles or contacts belonging to a user.

## Attributes

- `user_id` — required → `ForeignKey[User]`
- `name` — required → `string`
- `normalized_name` — required → `string`, system-controlled
- `website` — optional → `string | Null`
- `linkedin_url` — optional → `string | Null`
- `location` — optional → `string | Null`
- `notes` — optional → `Text | Null`

## Relationships

A `Company`:

- belongs to one `User`;
- may have zero or more `TrackedRoles`;
- may have zero or more `Contacts`.

## Name Normalization

`normalized_name` is generated by Huntly and must not be directly controlled by the user.

V1 normalization handles obvious formatting differences such as:

- leading/trailing whitespace;
- case differences;
- optionally repeated internal whitespace.

For example:

```text
"Ryder"
" ryder "
"RYDER"
```

should normalize to the same value.

V1 does not automatically equate semantically similar but textually different names such as:

```text
Ryder
Ryder System
Ryder System, Inc.
```

Such matching may be suggested later but must not silently merge Companies.

## Company Uniqueness

Company uniqueness is user-scoped.

Conceptually:

```text
UNIQUE(user_id, normalized_name)
```

Therefore, the same user cannot create duplicate normalized Company records, but separate users may each independently create a Company named `Ryder`.

If a user attempts to create an existing normalized Company, Huntly should surface the existing Company instead of creating a duplicate.

## Deletion

Deleting a Company does not delete its TrackedRoles or Contacts.

Instead:

```text
TrackedRole.company_id → NULL
Contact.company_id     → NULL
```

The user should receive confirmation before Company deletion.

---

# 6. Event

An `Event` represents a dated occurrence, deadline, action, or activity associated with exactly one `TrackedRole`.

Events may represent past or future activity.

## Attributes

- `tracked_role_id` — required → `ForeignKey[TrackedRole]`
- `title` — required → `string`
- `event_type` — required → `EventType`
- `custom_type_name` — conditionally required → `string | Null`
- `event_date` — required → `Date`
- `event_time` — optional → `Time | Null`
- `status` — required → `EventStatus`
- `notes` — optional → `Text | Null`
- `url` — optional → `string | Null`
- `location` — optional → `string | Null`

## Relationships

An `Event`:

- belongs to exactly one `TrackedRole`;
- has zero or more `EventStatusHistory` records.

An Event cannot exist independently of a TrackedRole.

## Canonical Event Statuses

```text
PENDING
SCHEDULED
COMPLETED
CANCELLED
MISSED
```

No default status exists.

The user must explicitly provide a valid Event status during creation.

Huntly must not automatically mark a past-due Event as `MISSED`.

A past Event whose status remains unresolved may be surfaced to the user for review.

## Canonical Event Types

```text
INTERVIEW
RECRUITER_SCREEN
ASSESSMENT
FOLLOW_UP
APPLICATION_DEADLINE
OFFER_DEADLINE
NETWORKING
CUSTOM
```

Canonical Event types allow Huntly to support filtering and specialized behavior.

Examples include:

```text
INTERVIEW
→ powers upcoming interview views

APPLICATION_DEADLINE
→ powers closing-soon views

OFFER_DEADLINE
→ powers offer-deadline views

FOLLOW_UP
→ powers action/reminder views
```

## Custom Event Types

If:

```text
event_type = CUSTOM
```

then:

```text
custom_type_name
```

is required.

If:

```text
event_type != CUSTOM
```

then:

```text
custom_type_name = NULL
```

Custom type names must not duplicate or trivially reproduce canonical Event types after normalization.

For example:

```text
"Interview"
" interview "
"INTERVIEW"
```

cannot be used as custom Event types.

Specific descriptions belong in the Event title instead.

For example:

```text
event_type = INTERVIEW
title      = "Final Technical Interview"
```

## Date and Time

`event_date` is required.

`event_time` is optional.

This preserves the semantic difference between:

```text
Application Deadline
October 10
```

and:

```text
Technical Interview
October 10 at 2:30 PM
```

Huntly must not invent an artificial time when the user only knows a date.

Users may create or backdate Events representing historical activity.

## Initial Status History

Creating an Event creates an initial `EventStatusHistory` record:

```text
from_status = NULL
to_status   = initial Event.status
```

The effective time may reflect when the real-world status began rather than when Huntly learned about it.

## Deletion

Deleting an Event deletes:

```text
Event
└── EventStatusHistory
```

It does not delete or otherwise affect the parent `TrackedRole`.

---

# 7. TrackedRoleStatusHistory

A `TrackedRoleStatusHistory` represents one status transition in the lifecycle of a `TrackedRole`.

Each row represents one transition.

## Attributes

- `tracked_role_id` — required → `ForeignKey[TrackedRole]`
- `from_status` — optional → `TrackedRoleStatus | Null`
- `to_status` — required → `TrackedRoleStatus`
- `occurred_at` — required → `datetime`
- `created_at` — required → `datetime`, system-generated

## Meaning of Timestamps

`occurred_at` represents when the real-world status transition occurred.

`created_at` represents when Huntly recorded the transition.

For example:

```text
occurred_at = September 10
created_at  = September 13
```

means the transition happened on September 10 but was entered into Huntly on September 13.

## History Rules

History records are append-only.

The initial status record uses:

```text
from_status = NULL
```

Subsequent transitions use the previous and new statuses.

Example:

```text
NULL      → SAVED
SAVED     → APPLIED
APPLIED   → SCREENING
SCREENING → INTERVIEW
```

---

# 8. EventStatusHistory

An `EventStatusHistory` represents one status transition in the lifecycle of an Event.

## Attributes

- `event_id` — required → `ForeignKey[Event]`
- `from_status` — optional → `EventStatus | Null`
- `to_status` — required → `EventStatus`
- `occurred_at` — required → `datetime`
- `created_at` — required → `datetime`, system-generated

## History Rules

History records are append-only.

The initial Event status uses:

```text
from_status = NULL
```

For example:

```text
NULL      → SCHEDULED
SCHEDULED → COMPLETED
```

As with TrackedRole history:

- `occurred_at` represents the real-world effective time;
- `created_at` represents when Huntly recorded the change.

---

# 9. Contact

A `Contact` represents a person relevant to the user's job search.

Contacts may exist independently of any particular TrackedRole.

## Attributes

- `user_id` — required → `ForeignKey[User]`
- `name` — required → `string`
- `email` — optional → `string | Null`
- `phone_number` — optional → `string | Null`
- `notes` — optional → `Text | Null`
- `company_id` — optional → `ForeignKey[Company] | Null`
- `linkedin_url` — optional → `string | Null`
- `role` — optional → `string | Null`

`role` represents the person's professional title when known, such as:

```text
Senior Technical Recruiter
Engineering Manager
Software Engineer
```

## Relationships

A Contact:

- belongs to one User;
- optionally belongs to one Company;
- may be associated with zero or more TrackedRoles through `TrackedRoleContact`.

A Contact belongs to at most one Company in Huntly V1.

## Minimum Data

Only `name` is required.

If the user provides no additional identifying information, Huntly may warn that the Contact could be difficult to distinguish later.

The warning does not prevent creation.

## Company Inference

When a Contact is created from within a TrackedRole that has a Company, Huntly may suggest that Company.

Huntly must not automatically assert that the Contact works for that Company.

The user may confirm, replace, or clear the Company association.

---

# 10. TrackedRoleContact

`TrackedRoleContact` represents the relationship between a Contact and a TrackedRole.

This is an association with domain information of its own rather than a purely invisible many-to-many join.

## Attributes

- `tracked_role_id` — required → `ForeignKey[TrackedRole]`
- `contact_id` — required → `ForeignKey[Contact]`
- `relationship_type` — optional → `RelationshipType | Null`
- `notes` — optional → `Text | Null`

For Huntly V1, one primary relationship type is stored per Contact/TrackedRole association.

## Canonical Relationship Types

```text
RECRUITER
HIRING_MANAGER
INTERVIEWER
REFERRAL
TEAM_MEMBER
OTHER
```

The relationship type is optional because the user may know a Contact is relevant without knowing that person's precise role in the opportunity.

`Contact.role` and `TrackedRoleContact.relationship_type` represent different concepts.

Example:

```text
Contact.role
= "Senior Technical Recruiter"

TrackedRoleContact.relationship_type
= RECRUITER
```

The first describes who the person is professionally.

The second describes how that person relates to the specific opportunity.

A given `(tracked_role_id, contact_id)` pair should not be duplicated.

---

# 11. Status Requirements

`TrackedRole.status` and `Event.status` are required and have no default value.

Creation requires the user to explicitly provide a valid canonical status.

Huntly may suggest interface choices, but the domain does not silently assign an initial status.

Every successful creation creates the corresponding initial status-history record.

---

# 12. Multi-User Data Isolation

Every read and mutation must operate inside the authenticated user's ownership boundary.

This applies to:

- TrackedRole queries;
- Company autocomplete;
- Company normalization and duplicate checks;
- TrackedRole duplicate detection;
- Contacts;
- Events;
- histories;
- associations;
- updates;
- deletes.

A user must never be able to associate one user's entity with another user's entity, even if a UUID is manually supplied to the API.

Ownership validation is therefore a domain rule, not merely a frontend concern.

---

# 13. V1 Design Principles

Huntly V1 follows several general principles:

**Explicit over inferred.**  
Huntly should not invent application dates, statuses, event outcomes, Company associations, or other real-world facts.

**Flexible without becoming semantically ambiguous.**  
Canonical statuses and Event types provide structure, while optional fields and custom Events allow users to choose their preferred level of detail.

**Historical data is first-class.**  
Users may backfill old TrackedRoles, Events, and status transitions.

**Warn rather than unnecessarily block.**  
Potential duplicate TrackedRoles and incomplete records should generally produce useful warnings rather than prevent legitimate user behavior.

**Preserve valuable data when relationships disappear.**  
Deleting a Company removes associations rather than destroying TrackedRoles or Contacts. Deleting a TrackedRole removes its dependent histories, Events, and associations but preserves independently valuable Companies and Contacts.

**Every user's data is private to that user.**
