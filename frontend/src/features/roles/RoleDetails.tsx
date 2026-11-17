import type { ReactNode } from "react";
import { Badge } from "@/components/ui/badge";
import { formatApplicationDate } from "./formValues";
import { rolePriorities, roleStatuses, roleTypes, type TrackedRole } from "./types";

const numberFormat = new Intl.NumberFormat(undefined, { maximumFractionDigits: 20 });

function formatSalary({ salary_min: min, salary_max: max, salary_currency: currency }: TrackedRole) {
  const lower = min === null ? null : numberFormat.format(Number(min));
  const upper = max === null ? null : numberFormat.format(Number(max));
  if (lower === null && upper === null) return currency;
  const range = lower && upper ? `${lower}–${upper}` : lower ? `${lower}+` : `Up to ${upper}`;
  return currency ? `${range} ${currency}` : range;
}

function Detail({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="min-w-0">
      <dt className="mb-1 text-xs font-medium text-muted-foreground">{label}</dt>
      <dd className="wrap-anywhere">{children ?? "—"}</dd>
    </div>
  );
}

export function RoleDetails({ role, companyName }: { role: TrackedRole; companyName?: string }) {
  return (
    <div className="min-w-0 space-y-5">
      <dl className="grid grid-cols-2 gap-x-4 gap-y-5">
        <Detail label="Status"><Badge variant="secondary">{roleStatuses[role.status]}</Badge></Detail>
        <Detail label="Company">{companyName ?? (role.company_id ? "Unavailable" : null)}</Detail>
        <Detail label="Role type">{role.role_type && roleTypes[role.role_type]}</Detail>
        <Detail label="Priority">{role.priority && rolePriorities[role.priority]}</Detail>
        <Detail label="Location">{role.location}</Detail>
        <Detail label="Application date">{formatApplicationDate(role.applied_at)}</Detail>
        <Detail label="Last updated">{formatApplicationDate(role.updated_at)}</Detail>
        <Detail label="Annual salary">{formatSalary(role)}</Detail>
        <Detail label="Listing">
          {role.listing_url && (
            <a className="text-primary underline underline-offset-4" href={role.listing_url} target="_blank" rel="noreferrer">
              Open job listing
            </a>
          )}
        </Detail>
      </dl>
      {role.description && (
        <section className="space-y-1.5 border-t pt-4">
          <h3 className="font-medium">Description</h3>
          <p className="reading-width whitespace-pre-wrap wrap-anywhere text-muted-foreground">{role.description}</p>
        </section>
      )}
      {role.notes && (
        <section className="space-y-1.5 border-t pt-4">
          <h3 className="font-medium">Notes</h3>
          <p className="reading-width whitespace-pre-wrap wrap-anywhere text-muted-foreground">{role.notes}</p>
        </section>
      )}
    </div>
  );
}

