import { readOwnedRecords, verifyOwner } from "@/api/ownedRecords";
import { useDataset } from "@/api/useDataset";
export type { Dataset as DashboardDataset } from "@/api/useDataset";
import { useAuth } from "@/features/auth/session/useAuth";
import type { RoleStatus, TrackedRole } from "@/features/roles/types";

export type DashboardRoleStatus = RoleStatus;
export type DashboardRole = TrackedRole;

export type DashboardCompany = {
  id: string;
  user_id: string;
  name: string;
  location: string | null;
  website: string | null;
};

export type DashboardContact = {
  id: string;
  user_id: string;
  name: string;
  company_id: string | null;
  role: string | null;
  email: string | null;
  phone_number: string | null;
};

export type DashboardEvent = {
  id: string;
  tracked_role_id: string;
  title: string;
  event_type: "interview" | "application_deadline" | "offer_deadline" | "follow_up";
  event_date: string;
  event_time: string | null;
};

export type DashboardResource = "roles" | "companies" | "contacts" | "upcomingEvents";

function readUpcomingEvents(body: unknown, userId: string): DashboardEvent[] {
  if (typeof body !== "object" || body === null || !("events" in body) || !Array.isArray(body.events)) {
    throw new Error("The server returned an invalid upcoming events list.");
  }
  verifyOwner(body, userId);
  return body.events as DashboardEvent[];
}

// The viewer's local calendar day, not UTC. "Upcoming" means today or later where
// they are. This is read during render, so a tab left open past midnight keeps
// the day on which the page rendered until it reloads.
function localCalendarDate() {
  const today = new Date();
  const month = String(today.getMonth() + 1).padStart(2, "0");
  const day = String(today.getDate()).padStart(2, "0");
  return `${today.getFullYear()}-${month}-${day}`;
}

/** Loads the signed-in user's lists independently so one failure cannot hide the other records. */
export function useDashboardRecords() {
  const auth = useAuth();
  const [roles, retryRoles] = useDataset<DashboardRole>("/tracked-roles/", auth, readOwnedRecords);
  const [companies, retryCompanies] = useDataset<DashboardCompany>("/companies/", auth, readOwnedRecords);
  const [contacts, retryContacts] = useDataset<DashboardContact>("/contacts/", auth, readOwnedRecords);
  const [upcomingEvents, retryUpcomingEvents] = useDataset<DashboardEvent>(
    `/events/upcoming?from_date=${localCalendarDate()}`,
    auth,
    readUpcomingEvents,
  );

  function retry(resource: DashboardResource) {
    const retryResource = {
      roles: retryRoles,
      companies: retryCompanies,
      contacts: retryContacts,
      upcomingEvents: retryUpcomingEvents,
    };
    retryResource[resource]();
  }

  return { roles, companies, contacts, upcomingEvents, retry };
}
