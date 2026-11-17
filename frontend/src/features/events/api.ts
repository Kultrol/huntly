import type { AuthContextValue } from "@/features/auth/session/AuthContext";
import type { EventInput, RoleEvent } from "./types";

type Request = AuthContextValue["request"];

export async function listRoleEvents(request: Request, roleId: string, signal: AbortSignal) {
  const response = await request(`/events/?tracked_role_id=${encodeURIComponent(roleId)}`, { signal });
  const events: RoleEvent[] = await response.json();
  if (events.some((event) => event.tracked_role_id !== roleId)) {
    throw new Error("Could not verify the role for these events. Try again.");
  }
  return events;
}

export async function listUpcomingEvents(
  request: Request,
  userId: string,
  fromDate: string,
  signal: AbortSignal,
) {
  const response = await request(`/events/upcoming?from_date=${fromDate}&include_all_types=true`, { signal });
  const body: { user_id: string; events: RoleEvent[] } = await response.json();
  if (body.user_id !== userId) {
    throw new Error("Could not verify the account for these events. Try again.");
  }
  return body.events;
}

export async function saveEvent(request: Request, roleId: string, data: Partial<EventInput>, id?: string) {
  const response = await request(id ? `/events/${id}` : "/events/", {
    method: id ? "PATCH" : "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(id ? data : { ...data, tracked_role_id: roleId }),
  });
  const saved: RoleEvent = await response.json();
  if (saved.tracked_role_id !== roleId) throw new Error("The event belongs to a different role. Refresh and try again.");
  return saved;
}

export async function deleteEvent(request: Request, id: string) {
  await request(`/events/${id}`, { method: "DELETE" });
}
