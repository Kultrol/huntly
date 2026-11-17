import type { AuthContextValue } from "@/features/auth/session/AuthContext";
import type { RoleChange, TrackedRole } from "./types";

type Request = AuthContextValue["request"];
type CompanySummary = { id: string; name: string; user_id: string };

function verifyOwner(record: { user_id: string }, userId: string) {
  // A different tab can replace the session cookie before this tab refreshes auth.
  if (record.user_id !== userId) {
    throw new Error("Could not verify the account for these records. Try again.");
  }
}

export async function listRoles(request: Request, userId: string, signal: AbortSignal) {
  const response = await request("/tracked-roles/", { signal });
  const roles: TrackedRole[] = await response.json();
  for (const role of roles) verifyOwner(role, userId);
  return roles;
}

export async function listRoleCompanies(request: Request, userId: string, signal: AbortSignal) {
  const response = await request("/companies/", { signal });
  const companies: CompanySummary[] = await response.json();
  for (const company of companies) verifyOwner(company, userId);
  return new Map(companies.map(({ id, name }) => [id, name]));
}

export async function saveRole(
  request: Request,
  userId: string,
  change: RoleChange,
) {
  const editing = "id" in change;
  const response = await request(editing ? `/tracked-roles/${change.id}` : "/tracked-roles/", {
    method: editing ? "PATCH" : "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(change.data),
  });
  const role: TrackedRole = await response.json();
  verifyOwner(role, userId);
  return role;
}

export async function deleteRole(request: Request, id: string) {
  await request(`/tracked-roles/${id}`, { method: "DELETE" });
}
