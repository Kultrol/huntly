import { useState, type ReactNode } from "react";
import { BriefcaseBusiness, Building2, ChevronRight, ContactRound, type LucideIcon } from "lucide-react";
import { getErrorMessage } from "@/api/client";
import { Card, CardContent } from "@/components/ui/card";
import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { TooltipProvider } from "@/components/ui/tooltip";
import { useAuth } from "@/features/auth/session/useAuth";
import { DashboardRecords } from "@/features/dashboard/DashboardRecords";
import { DashboardSidebar } from "@/features/dashboard/DashboardSidebar";
import { DashboardThemeToggle } from "@/features/dashboard/DashboardThemeToggle";
import { NextUpCard } from "@/features/dashboard/NextUpCard";
import { useDashboardRecords, type DashboardDataset, type DashboardRole } from "@/features/dashboard/useDashboardRecords";
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
  className?: string;
  children?: ReactNode;
};

function OverviewCard({ label, description, icon: Icon, dataset, className, children }: OverviewCardProps) {
  const value = { loading: "…", ready: dataset.records.length, error: "—" }[dataset.status];
  return (
    <Card className={cn("relative min-w-0 py-3 text-left transition-colors hover:cursor-pointer hover:bg-accent/40 sm:py-4", className)}>
      <ChevronRight aria-hidden="true" className="absolute top-3 right-2.5 size-4 text-muted-foreground md:hidden" />
      <CardContent className="px-2.5 sm:px-4">
        <div className="flex flex-col items-start gap-2 @lg:flex-row @lg:items-center @lg:gap-3">
          <span className="grid size-8 shrink-0 place-items-center rounded-lg bg-accent text-accent-foreground sm:size-9">
            <Icon aria-hidden="true" className="size-4 sm:size-5" />
          </span>
          <p className="text-sm font-medium text-muted-foreground">{label}</p>
        </div>
        <p className="mt-2 text-2xl font-semibold tracking-tight tabular-nums sm:text-3xl">
          {value}
          {dataset.status === "loading" && <span className="sr-only"> Loading</span>}
          {dataset.status === "error" && <span className="sr-only"> Count unavailable</span>}
        </p>
        <p className="mt-0.5 hidden text-xs text-muted-foreground @lg:block">{description}</p>
        {children}
      </CardContent>
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
  const { user, signOut, isPending, error: sessionError } = useAuth();
  const [logoutError, setLogoutError] = useState<string | null>(null);
  const records = useDashboardRecords();

  async function handleLogout() {
    setLogoutError(null);
    try {
      await signOut();
    } catch (error) {
      setLogoutError(getErrorMessage(error));
    }
  }

  // The route guard redirects when a session ends.
  if (!user) return null;

  return (
    <TooltipProvider>
      <SidebarProvider className="[--sidebar-width:14rem]! lg:[--sidebar-width:15rem]!">
        {/* Logout is the only session action on this page. */}
        <DashboardSidebar user={user} onLogout={handleLogout} isLoggingOut={isPending} />
        <main className="min-w-0 flex-1 bg-background">
          <header className="flex h-14 items-center gap-3 border-b bg-card/70 px-4 md:px-6">
            <SidebarTrigger className="size-8" />
            <span className="h-4 border-l" aria-hidden="true" />
            <span className="text-sm font-medium">Dashboard</span>
            <DashboardThemeToggle className="ml-auto" />
          </header>

          <div className="@container space-y-6 px-4 py-5 sm:px-6 sm:py-7 lg:px-8">
            {(logoutError || sessionError) && (
              <p role="alert" className="rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive">
                {logoutError || sessionError}
              </p>
            )}
            <section aria-labelledby="dashboard-heading" className="relative isolate overflow-hidden rounded-xl border bg-linear-to-br from-accent via-card to-card px-5 py-6 sm:px-7 sm:py-8">
              <div className="pointer-events-none absolute -top-30 -right-8 -z-10 size-64 rounded-full border border-primary/10 shadow-[0_0_0_2rem_var(--color-primary-soft)] [--color-primary-soft:color-mix(in_srgb,var(--primary)_4%,transparent)]" aria-hidden="true" />
              <p className="text-xs font-semibold tracking-widest text-accent-foreground uppercase">Job search workspace</p>
              <h1 id="dashboard-heading" className="mt-2 text-3xl font-semibold tracking-tight wrap-anywhere sm:text-4xl">
                Welcome {user.name}
              </h1>
              <p className="mt-2 text-sm text-muted-foreground">See your roles, companies, and contacts at a glance.</p>
            </section>

            <NextUpCard
              events={records.upcomingEvents}
              roles={records.roles.records}
              onRetry={() => records.retry("upcomingEvents")}
            />

            <section aria-labelledby="overview-heading" className="space-y-3">
              <h2 id="overview-heading" className="text-lg font-semibold tracking-tight">Overview</h2>
              <div className="grid grid-cols-2 gap-2.5 sm:gap-4 @2xl:grid-cols-3">
                <OverviewCard
                  label="Roles"
                  description="Opportunities you’re tracking"
                  icon={BriefcaseBusiness}
                  dataset={records.roles}
                  className="col-span-2 @2xl:col-span-1"
                >
                  {records.roles.status === "ready" && <RoleBreakdown roles={records.roles.records} />}
                </OverviewCard>
                <OverviewCard label="Companies" description="Organizations in your tracker" icon={Building2} dataset={records.companies} />
                <OverviewCard label="Contacts" description="People in your network" icon={ContactRound} dataset={records.contacts} />
              </div>
            </section>

            {/* Remount when the account changes so the previous filters do not carry over. */}
            <DashboardRecords
              key={user.id}
              roles={records.roles}
              companies={records.companies}
              contacts={records.contacts}
              retry={records.retry}
            />
          </div>
        </main>
      </SidebarProvider>
    </TooltipProvider>
  );
}
