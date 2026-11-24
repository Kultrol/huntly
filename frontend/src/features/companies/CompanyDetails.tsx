import { Pencil, Trash2 } from "lucide-react";
import { LoadError, LoadingState } from "@/components/feedback/LoadState";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { roleStatuses, type TrackedRole } from "@/features/roles/types";
import type { Company } from "./api";

type CompanyDetailsProps = {
  company: Company;
  roles: TrackedRole[];
  rolesStatus: "loading" | "error" | "ready";
  rolesError?: string;
  onRetryRoles: () => void;
  onEdit: (trigger: HTMLButtonElement) => void;
  onDelete: (trigger: HTMLButtonElement) => void;
};

const sectionHeading = "mb-2 text-xs font-semibold tracking-wider text-muted-foreground uppercase";
const profileLink = "touch-target inline-flex items-center text-sm font-medium text-primary underline underline-offset-4";

export function CompanyDetails({
  company, roles, rolesStatus, rolesError, onRetryRoles, onEdit, onDelete,
}: CompanyDetailsProps) {
  const website = company.website && URL.canParse(company.website) ? new URL(company.website) : null;

  return (
    <div className="@container/profile min-w-0 space-y-4 wrap-anywhere">
      <header>
        <h2 aria-live="polite" className="text-[1.75rem] leading-tight font-bold tracking-tight">{company.name}</h2>
        {company.location && <p className="mt-1 text-sm text-muted-foreground">{company.location}</p>}
        {(website || company.linkedin_url) && (
          <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1">
            {website && (
              <a className={profileLink} href={website.href} target="_blank" rel="noreferrer">
                {website.hostname}
              </a>
            )}
            {company.linkedin_url && (
              <a className={profileLink} href={company.linkedin_url} target="_blank" rel="noreferrer">LinkedIn</a>
            )}
          </div>
        )}
      </header>

      <section className="border-t pt-3">
        <h3 className={sectionHeading}>Tracked roles</h3>
        {rolesStatus === "loading" && <LoadingState message="Loading tracked roles…" />}
        {rolesStatus === "error" && (
          <LoadError message={rolesError || "Could not load tracked roles."} retryLabel="Retry roles" onRetry={onRetryRoles} />
        )}
        {rolesStatus === "ready" && (roles.length ? (
          <ul className="space-y-3">
            {roles.map((role) => (
              <li key={role.id} className="grid items-baseline justify-items-start gap-x-2 gap-y-1 @[16rem]/profile:grid-cols-[minmax(0,1fr)_auto]">
                <span className="text-sm leading-snug font-semibold">{role.title}</span>
                <Badge variant="outline" className="rounded-md bg-card text-muted-foreground">{roleStatuses[role.status]}</Badge>
              </li>
            ))}
          </ul>
        ) : <p className="text-sm text-muted-foreground">No tracked roles yet.</p>)}
      </section>

      {company.notes && (
        <section className="border-t pt-3">
          <h3 className={sectionHeading}>Notes</h3>
          <p className="reading-width text-sm leading-relaxed whitespace-pre-wrap">{company.notes}</p>
        </section>
      )}

      <div className="flex flex-wrap items-center gap-2 border-t pt-3">
        <Button variant="outline" size="sm" aria-label="Edit company" aria-haspopup="dialog" onClick={(event) => onEdit(event.currentTarget)}>
          <Pencil aria-hidden="true" /> Edit
        </Button>
        <Button variant="ghost" size="sm" className="text-destructive" aria-label="Delete company" aria-haspopup="dialog" onClick={(event) => onDelete(event.currentTarget)}>
          <Trash2 aria-hidden="true" /> Delete
        </Button>
      </div>
    </div>
  );
}
