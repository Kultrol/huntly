import type { ReactNode } from "react";
import { Link } from "react-router";
import {
  BriefcaseBusiness,
  Building2,
  ChevronRight,
  ContactRound,
  type LucideIcon,
} from "lucide-react";
import { WorkspaceLayout } from "@/components/WorkspaceLayout";
import { Card, CardContent } from "@/components/ui/card";
import { useAuth } from "@/features/auth/session/useAuth";
import { DashboardRecords } from "@/features/dashboard/DashboardRecords";
import { NextUpCard } from "@/features/dashboard/NextUpCard";
import {
  useDashboardRecords,
  type DashboardDataset,
  type DashboardRole,
} from "@/features/dashboard/useDashboardRecords";
import { cn } from "@/lib/utils";

// Summary words for the roles card. These are not the tracker status names
// ("Interview", "Offer") and must stay separate from that map.
const roleBreakdown = [
  { status: "applied", label: "Applied" },
  { status: "interview", label: "Interviews" },
  { status: "offer", label: "Offers" },
] as const;

type OverviewCardProps = {
  label: string;
  description: string;
  icon: LucideIcon;
  dataset: DashboardDataset<unknown>;
  to?: string;
  className?: string;
  children?: ReactNode;
};

function OverviewCard({
  label,
  description,
  icon: Icon,
  dataset,
  to,
  className,
  children,
}: OverviewCardProps) {
  const value = { loading: "…", ready: dataset.records.length, error: "—" }[
    dataset.status
  ];
  return (
    <Card
      className={cn(
        "relative min-w-0 py-4 text-left transition-colors",
        to && "hover:bg-accent/40",
        className,
      )}
    >
      {to && (
        <ChevronRight aria-hidden="true" className="absolute top-3 right-2.5 size-4 text-muted-foreground" />
      )}
      <CardContent className="px-2.5 sm:px-4">
        <div className="flex flex-col items-start gap-2 @lg/workspace:flex-row @lg/workspace:items-center @lg/workspace:gap-3">
          <span className="grid size-8 shrink-0 place-items-center rounded-lg bg-accent text-accent-foreground sm:size-9">
            <Icon aria-hidden="true" className="size-4 sm:size-5" />
          </span>
          <p className="text-sm font-medium text-muted-foreground">{label}</p>
        </div>
        <p className="mt-2 text-2xl font-semibold tracking-tight tabular-nums sm:text-3xl">
          {value}
          {dataset.status === "loading" && (
            <span className="sr-only"> Loading</span>
          )}
          {dataset.status === "error" && (
            <span className="sr-only"> Count unavailable</span>
          )}
        </p>
        <p className="mt-0.5 hidden text-xs text-muted-foreground @lg/workspace:block">
          {description}
        </p>
        {children}
      </CardContent>
      {to && (
        <Link
          to={to}
          aria-label={`View ${label.toLowerCase()}`}
          className="absolute inset-0 rounded-xl focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-ring"
        />
      )}
    </Card>
  );
}

function RoleBreakdown({ roles }: { roles: DashboardRole[] }) {
  return (
    <dl className="mt-3 grid grid-cols-3 gap-2 border-t pt-3">
      {roleBreakdown.map(({ status, label }) => (
        <div key={status}>
          <dt className="text-xs text-muted-foreground">{label}</dt>
          <dd className="mt-0.5 text-sm font-semibold tabular-nums">
            {roles.filter((role) => role.status === status).length}
          </dd>
        </div>
      ))}
    </dl>
  );
}

export default function DashboardPage() {
  const { user, csrfToken } = useAuth();
  const records = useDashboardRecords();
  if (!user) return null;

  return (
    <WorkspaceLayout page="dashboard" title="Dashboard">
      <section
        aria-labelledby="dashboard-heading"
        className="relative isolate overflow-hidden rounded-xl border bg-linear-to-br from-accent via-card to-card px-5 py-6 sm:px-7 sm:py-8"
      >
        <div
          className="pointer-events-none absolute -top-30 -right-8 -z-10 size-64 rounded-full border border-primary/10 shadow-[0_0_0_2rem_var(--color-primary-soft)] [--color-primary-soft:color-mix(in_srgb,var(--primary)_4%,transparent)]"
          aria-hidden="true"
        />
        <p className="text-xs font-semibold tracking-widest text-accent-foreground uppercase">
          Job search workspace
        </p>
        <h1
          id="dashboard-heading"
          className="mt-2 page-title"
        >
          Welcome {user.name}
        </h1>
        <p className="mt-2 text-sm text-muted-foreground">
          See your roles, companies, and contacts at a glance.
        </p>
      </section>

      <NextUpCard
        events={records.upcomingEvents}
        roles={records.roles.records}
        onRetry={() => records.retry("upcomingEvents")}
      />

      <section aria-labelledby="overview-heading" className="space-y-3">
        <h2
          id="overview-heading"
          className="section-title"
        >
          Overview
        </h2>
        <div className="grid grid-cols-2 gap-2.5 sm:gap-4 @2xl/workspace:grid-cols-3">
          <OverviewCard
            label="Roles"
            description="Opportunities you’re tracking"
            icon={BriefcaseBusiness}
            dataset={records.roles}
            to="/roles"
            className="col-span-2 @2xl/workspace:col-span-1"
          >
            {records.roles.status === "ready" && (
              <RoleBreakdown roles={records.roles.records} />
            )}
          </OverviewCard>
          <OverviewCard
            label="Companies"
            description="Organizations in your tracker"
            icon={Building2}
            dataset={records.companies}
          />
          <OverviewCard
            label="Contacts"
            description="People in your network"
            icon={ContactRound}
            dataset={records.contacts}
          />
        </div>
      </section>

      {/* Clear filters and open details when the signed-in session changes. */}
      <DashboardRecords
        key={`${user.id}:${csrfToken}`}
        roles={records.roles}
        companies={records.companies}
        contacts={records.contacts}
        retry={records.retry}
      />
    </WorkspaceLayout>
  );
}
