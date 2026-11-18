import { verifyOwner } from "@/api/ownedRecords";
import type { AuthContextValue } from "@/features/auth/session/AuthContext";

export type CompanyFields = {
  name: string;
  website: string | null;
  linkedin_url: string | null;
  location: string | null;
  notes: string | null;
};

export type Company = CompanyFields & { id: string; user_id: string };

type Request = AuthContextValue["request"];

export async function saveCompany(request: Request, userId: string, fields: CompanyFields, original?: Company) {
  // Clearing an optional field sends null. Omit untouched fields on edit.
  const changes = Object.fromEntries(Object.entries(fields).filter(([key, value]) =>
    original ? value !== original[key as keyof CompanyFields] : value !== null,
  ));
  if (original && !Object.keys(changes).length) return original;

  const response = await request(original ? `/companies/${original.id}` : "/companies/", {
    method: original ? "PATCH" : "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(changes),
  });
  const saved: Company = await response.json();
  verifyOwner(saved, userId);
  return saved;
}

export async function deleteCompany(request: Request, id: string) {
  await request(`/companies/${id}`, { method: "DELETE" });
}
