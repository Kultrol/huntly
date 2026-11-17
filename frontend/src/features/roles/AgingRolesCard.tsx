import { EmptyState } from "@/components/feedback/LoadState";
import { Clock3Icon } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { RoleStatus, TrackedRole } from "./types";

const closedStatuses = new Set<RoleStatus>(["accepted", "rejected", "withdrawn"]);
const millisecondsPerDay = 86_400_000;
const agingThresholdDays = 14;

type AgingRolesCardProps = {
  roles: TrackedRole[];
  onSelect: (id: string) => void;
};

export function AgingRolesCard({ roles, onSelect }: AgingRolesCardProps) {
  const now = Date.now();
  const openRoles = roles.filter((role) => !closedStatuses.has(role.status));
  const agingRoles = openRoles
    .map((role) => ({
      role,
      daysSinceUpdate: Math.floor((now - Date.parse(role.updated_at)) / millisecondsPerDay),
    }))
    .filter(({ daysSinceUpdate }) => daysSinceUpdate >= agingThresholdDays)
    .sort((a, b) => Date.parse(a.role.updated_at) - Date.parse(b.role.updated_at));

  return (
    <Card className="h-full">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Clock3Icon className="size-4 text-muted-foreground" aria-hidden="true" />
          <h2 className="section-title">Aging roles</h2>
        </CardTitle>
        <CardDescription>Open roles without an update for {agingThresholdDays} days.</CardDescription>
      </CardHeader>
      <CardContent>
        {agingRoles.length === 0 ? (
          <EmptyState message={openRoles.length > 0
            ? "All open roles have been updated recently."
            : "No open roles to review."}
          />
        ) : (
          <ul className="divide-y @3xl/workspace:max-h-64 @3xl/workspace:overflow-y-auto">
            {agingRoles.map(({ role, daysSinceUpdate }) => (
              <li key={role.id}>
                <button
                  type="button"
                  aria-label={`${role.title}, ${daysSinceUpdate} days since last update`}
                  onClick={() => onSelect(role.id)}
                  className="touch-target flex w-full items-center justify-between gap-3 rounded-md px-2 py-3 text-left hover:bg-accent focus-visible:outline-2 focus-visible:outline-ring"
                >
                  <span className="min-w-0 truncate font-medium">{role.title}</span>
                  <span className="shrink-0 text-xs text-muted-foreground">{daysSinceUpdate} days</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
