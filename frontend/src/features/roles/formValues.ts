import { rolePriorities, roleStatuses, roleTypes } from "./types";
import type { RoleChange, RoleInput, TrackedRole } from "./types";

type RoleFormValues = { [Field in keyof RoleInput]: string };

const dateFormat = new Intl.DateTimeFormat(undefined, { dateStyle: "medium" });

export function formatApplicationDate(value: string | null) {
  return value ? dateFormat.format(new Date(value)) : "—";
}

function dateFieldValue(value: string | null | undefined) {
  if (!value) return "";
  const date = new Date(value);
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${date.getFullYear()}-${month}-${day}`;
}

export function roleFormValues(role?: TrackedRole): RoleFormValues {
  return {
    title: role?.title ?? "",
    status: role?.status ?? "",
    location: role?.location ?? "",
    role_type: role?.role_type ?? "",
    priority: role?.priority ?? "",
    listing_url: role?.listing_url ?? "",
    salary_min: role?.salary_min ?? "",
    salary_max: role?.salary_max ?? "",
    salary_currency: role?.salary_currency ?? "",
    applied_at: dateFieldValue(role?.applied_at),
    description: role?.description ?? "",
    notes: role?.notes ?? "",
  };
}

function readChoice<Choice extends string>(
  value: string | null,
  choices: Record<Choice, string>,
  label: string,
): Choice | null {
  if (value === null) return null;
  if (!Object.hasOwn(choices, value)) throw new Error(`Choose a valid ${label}.`);
  return value as Choice;
}

export function readRoleForm(form: HTMLFormElement, role?: TrackedRole): RoleChange {
  const fields = new FormData(form);
  const rawValue = (key: keyof RoleInput) => String(fields.get(key) ?? "");
  const text = (key: keyof RoleInput) => rawValue(key).trim() || null;

  const title = text("title");
  if (!title) throw new Error("Enter a role title.");
  const status = readChoice(text("status"), roleStatuses, "status");
  if (!status) throw new Error("Choose a status.");

  const listingUrl = text("listing_url");
  if (listingUrl) {
    const url = URL.parse(listingUrl);
    if (!url || (url.protocol !== "http:" && url.protocol !== "https:")) {
      throw new Error("Enter a listing URL that starts with http:// or https://.");
    }
  }

  // Send decimal strings so the API receives the exact amounts entered.
  const salaryMin = text("salary_min");
  const salaryMax = text("salary_max");
  for (const salary of [salaryMin, salaryMax]) {
    if (salary !== null && (!Number.isFinite(Number(salary)) || Number(salary) < 0)) {
      throw new Error("Salary amounts must be zero or greater.");
    }
  }
  if (salaryMin !== null && salaryMax !== null && Number(salaryMin) > Number(salaryMax)) {
    throw new Error("Minimum salary cannot exceed maximum salary.");
  }

  const applicationDate = text("applied_at");
  const originalDate = dateFieldValue(role?.applied_at);
  // Editing another field preserves the original timestamp, including its time of day.
  const appliedAt = (applicationDate ?? "") === originalDate
    ? role?.applied_at ?? null
    : applicationDate ? new Date(`${applicationDate}T00:00:00`).toISOString() : null;

  const data: RoleInput = {
    title,
    status,
    location: text("location"),
    role_type: readChoice(text("role_type"), roleTypes, "role type"),
    priority: readChoice(text("priority"), rolePriorities, "priority"),
    listing_url: listingUrl,
    salary_min: salaryMin,
    salary_max: salaryMax,
    salary_currency: text("salary_currency"),
    applied_at: appliedAt,
    description: text("description"),
    notes: text("notes"),
  };

  if (!role) return { data };
  const initial = roleFormValues(role);
  const changedFields = Object.entries(data).filter(([key, value]) => {
    const field = key as keyof RoleInput;
    return rawValue(field) !== initial[field] && value !== role[field];
  });
  return { id: role.id, data: Object.fromEntries(changedFields) as Partial<RoleInput> };
}
