import type { RoleEvent } from "./types";

const dateFormatter = new Intl.DateTimeFormat(undefined, {
  dateStyle: "medium",
  timeZone: "UTC",
});
const timeFormatter = new Intl.DateTimeFormat(undefined, {
  timeStyle: "short",
  timeZone: "UTC",
});

export function formatEventWhen(event: RoleEvent) {
  // Calendar values have no timezone; preserve their written day and time.
  const date = new Date(`${event.event_date}T${event.event_time ?? "00:00:00"}Z`);
  const time = event.event_time ? ` · ${timeFormatter.format(date)}` : "";
  return dateFormatter.format(date) + time;
}

export function localToday() {
  const date = new Date();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${date.getFullYear()}-${month}-${day}`;
}

export function compareEventDates(first: RoleEvent, second: RoleEvent) {
  // Events without a time sort after timed events on the same day.
  return first.event_date.localeCompare(second.event_date)
    || (first.event_time ?? "24").localeCompare(second.event_time ?? "24")
    || first.id.localeCompare(second.id);
}
