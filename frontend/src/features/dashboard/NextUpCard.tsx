import { CalendarDays, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { DashboardDataset, DashboardEvent, DashboardRole } from "./useDashboardRecords";

const eventTypeLabels: Record<DashboardEvent["event_type"], string> = {
  interview: "Interview",
  application_deadline: "Application deadline",
  offer_deadline: "Offer deadline",
  follow_up: "Follow-up",
};

// Event dates and times are calendar values without a time zone. Format their
// components in UTC so the browser never shifts the displayed day or time.
const dateFormat = new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeZone: "UTC" });
const timeFormat = new Intl.DateTimeFormat(undefined, { timeStyle: "short", timeZone: "UTC" });

type NextUpCardProps = {
  events: DashboardDataset<DashboardEvent>;
  roles: DashboardRole[];
  onRetry: () => void;
};

export function NextUpCard({ events, roles, onRetry }: NextUpCardProps) {
  const roleTitles = new Map(roles.map((role) => [role.id, role.title]));

  return (
    <section aria-labelledby="next-up-heading">
      <Card className="gap-3">
        <CardHeader className="flex items-center gap-3">
          <span className="grid size-9 shrink-0 place-items-center rounded-lg bg-accent text-accent-foreground">
            <CalendarDays aria-hidden="true" className="size-5" />
          </span>
          <div>
            <CardTitle><h2 id="next-up-heading" className="text-lg font-semibold">Next up</h2></CardTitle>
            <CardDescription>Upcoming interviews, deadlines, and follow-ups.</CardDescription>
          </div>
        </CardHeader>
        <CardContent>
          {events.status === "loading" && <p role="status" className="text-muted-foreground">Loading upcoming events…</p>}
          {events.status === "error" && (
            <div className="flex flex-wrap items-center gap-2">
              <p role="alert" className="text-muted-foreground">{events.error}</p>
              <Button variant="outline" size="sm" onClick={onRetry}>Retry upcoming events</Button>
            </div>
          )}
          {events.status === "ready" && (
            events.records.length === 0 ? (
              <p className="border-t pt-3 text-muted-foreground">Nothing scheduled for today or later.</p>
            ) : (
              <ul role="list" className="divide-y border-t">
                {events.records.map((event) => {
                  const time = event.event_time?.slice(0, 5);
                  const dateTime = time ? `${event.event_date}T${time}` : event.event_date;
                  const formattedEvent = new Date(`${event.event_date}T${time ?? "00:00"}:00Z`);
                  const roleTitle = roleTitles.get(event.tracked_role_id);

                  return (
                    <li
                      key={event.id}
                      className="flex items-center gap-2 px-2 py-2.5 text-left transition-colors hover:cursor-pointer hover:bg-accent/40 sm:gap-3"
                    >
                      <div className="min-w-0 flex-1 wrap-anywhere">
                        <p className="font-medium">{event.title}</p>
                        <p className="mt-0.5 text-xs text-muted-foreground">
                          {eventTypeLabels[event.event_type]}{roleTitle && ` · ${roleTitle}`}
                        </p>
                      </div>
                      <time dateTime={dateTime} className="shrink-0 text-right text-xs text-muted-foreground tabular-nums">
                        <span className="block">{dateFormat.format(formattedEvent)}</span>
                        {time && <span className="mt-0.5 block">{timeFormat.format(formattedEvent)}</span>}
                      </time>
                      <ChevronRight aria-hidden="true" className="size-4 shrink-0 text-muted-foreground md:hidden" />
                    </li>
                  );
                })}
              </ul>
            )
          )}
        </CardContent>
      </Card>
    </section>
  );
}
