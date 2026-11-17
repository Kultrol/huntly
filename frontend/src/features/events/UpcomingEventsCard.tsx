import { CalendarDaysIcon } from "lucide-react";
import { EmptyState, LoadError, LoadingState } from "@/components/feedback/LoadState";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { TrackedRole } from "@/features/roles/types";
import { useEvents } from "./useEvents";
import { formatEventWhen } from "./eventDates";

type UpcomingEventsCardProps = {
  userId: string;
  roles: TrackedRole[];
  version: number;
  onSelectRole: (id: string) => void;
};

export function UpcomingEventsCard({ userId, roles, version, onSelectRole }: UpcomingEventsCardProps) {
  const { events, loading, error, retry } = useEvents(userId, null, version);
  const titles = new Map(roles.map((role) => [role.id, role.title]));
  return (
    <Card className="h-full">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <CalendarDaysIcon className="size-4 text-muted-foreground" aria-hidden="true" />
          <h2 className="section-title">Upcoming events</h2>
        </CardTitle>
        <CardDescription>Your next five events, from today onward.</CardDescription>
      </CardHeader>
      <CardContent>
        {loading && <LoadingState message="Loading upcoming events…" />}
        {error && <LoadError message={error} onRetry={retry} retryLabel="Retry upcoming events" />}
        {!loading && !error && events.length === 0 && <EmptyState message="Nothing coming up yet." />}
        {!loading && !error && events.length > 0 && (
          <ul className="divide-y @3xl/workspace:max-h-64 @3xl/workspace:overflow-y-auto">
            {events.map((event) => (
              <li key={event.id}>
                <button
                  type="button"
                  aria-label={`View ${event.title} for ${titles.get(event.tracked_role_id) ?? "its role"}`}
                  onClick={() => onSelectRole(event.tracked_role_id)}
                  className="touch-target flex w-full flex-wrap items-center justify-between gap-2 rounded-md px-2 py-3 text-left hover:bg-accent focus-visible:outline-2 focus-visible:outline-ring"
                >
                  <span className="min-w-0 flex-1">
                    <span className="block truncate font-medium">{event.title}</span>
                    <span className="block truncate text-xs text-muted-foreground">{titles.get(event.tracked_role_id)}</span>
                  </span>
                  <time dateTime={event.event_date} className="text-xs text-muted-foreground">{formatEventWhen(event)}</time>
                </button>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
