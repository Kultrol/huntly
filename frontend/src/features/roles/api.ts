import { verifyOwner } from "@/api/ownedRecords";
import type { AuthContextValue } from "@/features/auth/session/AuthContext";
import type { RoleChange, TrackedRole } from "./types";

type Request = AuthContextValue["request"];

export async function listRoles(request: Request, userId: string, signal: AbortSignal) {
  const response = await request("/tracked-roles/", { signal });
  const roles: TrackedRole[] = await response.json();
  for (const role of roles) verifyOwner(role, userId);
  return roles;
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
