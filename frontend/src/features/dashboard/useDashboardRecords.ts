import { useCallback, useEffect, useState } from "react";
import { getErrorMessage } from "@/api/client";
import type { AuthContextValue } from "@/features/auth/session/AuthContext";
import { useAuth } from "@/features/auth/session/useAuth";

export type DashboardRoleStatus =
  | "saved"
  | "applied"
  | "screening"
  | "interview"
  | "offer"
  | "rejected"
  | "accepted"
  | "withdrawn";

export type DashboardRole = {
  id: string;
  user_id: string;
  title: string;
  company_id: string | null;
  location: string | null;
  role_type: string | null;
  status: DashboardRoleStatus;
  applied_at: string | null;
};

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

export type DashboardDataset<T> =
  | { status: "loading"; records: T[]; error: null }
  | { status: "ready"; records: T[]; error: null }
  | { status: "error"; records: T[]; error: string };

const loadingDataset: DashboardDataset<never> = { status: "loading", records: [], error: null };

type DashboardResult<T> = {
  path: string;
  sessionKey: string;
  version: number;
  dataset: DashboardDataset<T>;
};

function verifyOwner(value: unknown, userId: string) {
  // A different tab can replace the session cookie before this tab refreshes auth.
  if (typeof value !== "object" || value === null || !("user_id" in value) || value.user_id !== userId) {
    throw new Error("Could not verify the account for these records. Try again.");
  }
}

function readOwnedRecords<T>(body: unknown, userId: string): T[] {
  if (!Array.isArray(body)) throw new Error("The server returned an invalid records list.");
  for (const record of body) verifyOwner(record, userId);
  return body as T[];
}

function readUpcomingEvents(body: unknown, userId: string): DashboardEvent[] {
  if (typeof body !== "object" || body === null || !("events" in body) || !Array.isArray(body.events)) {
    throw new Error("The server returned an invalid upcoming events list.");
  }
  verifyOwner(body, userId);
  return body.events as DashboardEvent[];
}

function useDashboardDataset<T>(
  path: string,
  { user, csrfToken, request }: AuthContextValue,
  readRecords: (body: unknown, userId: string) => T[],
) {
  const userId = user?.id;
  const sessionKey = userId ? `${userId}:${csrfToken ?? ""}` : null;
  const [version, setVersion] = useState(0);
  const [result, setResult] = useState<DashboardResult<T> | null>(null);

  useEffect(() => {
    if (userId === undefined || sessionKey === null) return;
    const controller = new AbortController();

    async function fetchDataset(key: string, expectedOwner: string) {
      let dataset: DashboardDataset<T>;
      try {
        const response = await request(path, { signal: controller.signal });
        const records = readRecords(await response.json(), expectedOwner);
        dataset = { status: "ready", records, error: null };
      } catch (error) {
        dataset = { status: "error", records: [], error: getErrorMessage(error) };
      }

      if (!controller.signal.aborted) setResult({ path, sessionKey: key, version, dataset });
    }

    void fetchDataset(sessionKey, userId);
    return () => controller.abort();
  }, [path, readRecords, request, sessionKey, userId, version]);

  // Hide results from an earlier session or attempt before the next request starts.
  const dataset = result?.sessionKey === sessionKey && result.version === version && result.path === path
    ? result.dataset
    : loadingDataset;
  const retry = useCallback(() => setVersion((currentVersion) => currentVersion + 1), []);

  return [dataset, retry] as const;
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
  const [roles, retryRoles] = useDashboardDataset<DashboardRole>("/tracked-roles/", auth, readOwnedRecords);
  const [companies, retryCompanies] = useDashboardDataset<DashboardCompany>("/companies/", auth, readOwnedRecords);
  const [contacts, retryContacts] = useDashboardDataset<DashboardContact>("/contacts/", auth, readOwnedRecords);
  const [upcomingEvents, retryUpcomingEvents] = useDashboardDataset<DashboardEvent>(
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
