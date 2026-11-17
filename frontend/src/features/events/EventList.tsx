import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { formatEventWhen, localToday } from "./eventDates";
import { eventStatuses, eventTypes, type RoleEvent } from "./types";

type EventListProps = {
  events: RoleEvent[];
  pending: boolean;
  onEdit: (event: RoleEvent, trigger: HTMLButtonElement) => void;
  onDelete: (event: RoleEvent, trigger: HTMLButtonElement) => void;
  onComplete: (event: RoleEvent) => void;
};

export function EventList({ events, pending, onEdit, onDelete, onComplete }: EventListProps) {
  const today = localToday();
  return (
    <ul className="divide-y">
      {events.map((event) => {
        const open = event.status === "pending" || event.status === "scheduled";
        return (
          <li key={event.id} className="space-y-2 py-3 first:pt-0 last:pb-0">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div className="min-w-0">
                <h4 className="font-medium wrap-anywhere">{event.title}</h4>
                <p className="mt-0.5 text-xs text-muted-foreground">
                  {event.custom_type_name ?? eventTypes[event.event_type]} · {formatEventWhen(event)}
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="outline">{eventStatuses[event.status]}</Badge>
                {open && event.event_date < today && (
                  <span className="text-xs text-muted-foreground">Date passed</span>
                )}
              </div>
            </div>
            {event.location && <p className="text-sm text-muted-foreground wrap-anywhere">{event.location}</p>}
            {event.notes && <p className="reading-width whitespace-pre-wrap wrap-anywhere text-sm text-muted-foreground">{event.notes}</p>}
            <div className="flex flex-wrap items-center gap-1">
              {open && (
                <Button
                  variant="outline"
                  size="sm"
                  disabled={pending}
                  aria-label={`Complete ${event.title}`}
                  onClick={() => onComplete(event)}
                >
                  Mark complete
                </Button>
              )}
              <Button
                variant="ghost"
                size="sm"
                disabled={pending}
                aria-label={`Edit ${event.title}`}
                onClick={(click) => onEdit(event, click.currentTarget)}
              >
                Edit
              </Button>
              <Button
                variant="ghost"
                size="sm"
                disabled={pending}
                aria-label={`Delete ${event.title}`}
                onClick={(click) => onDelete(event, click.currentTarget)}
              >
                Delete
              </Button>
              {event.url && (
                <a
                  href={event.url}
                  target="_blank"
                  rel="noreferrer"
                  className="touch-target inline-flex items-center rounded-md px-2 text-sm text-primary underline underline-offset-4 focus-visible:outline-2 focus-visible:outline-ring"
                >
                  Open link
                </a>
              )}
            </div>
          </li>
        );
      })}
    </ul>
  );
}
