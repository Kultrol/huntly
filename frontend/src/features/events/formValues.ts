import { eventStatuses, eventTypes, type EventInput, type RoleEvent } from "./types";

export function readEventForm(form: HTMLFormElement): EventInput {
  const fields = new FormData(form);
  const text = (name: keyof EventInput) => String(fields.get(name) ?? "").trim();
  const title = text("title");
  const type = text("event_type");
  const status = text("status");
  const date = text("event_date");
  const customType = type === "custom" ? text("custom_type_name") : null;

  if (!title || !date) throw new Error("Enter an event title and date.");
  if (!Object.hasOwn(eventTypes, type) || !Object.hasOwn(eventStatuses, status)) {
    throw new Error("Choose an event type and status.");
  }

  if (type === "custom") {
    const normalized = customType?.toLowerCase().replace(/[\s_-]+/g, " ");
    if (!normalized) throw new Error("Enter a custom event type.");
    if (Object.keys(eventTypes).some((key) => key.replaceAll("_", " ") === normalized)) {
      throw new Error("Choose the existing event type or enter a different custom label.");
    }
  }

  const url = text("url");
  if (url && !["http:", "https:"].includes(URL.parse(url)?.protocol ?? "")) {
    throw new Error("Enter a link that starts with http:// or https://.");
  }

  return {
    title,
    event_type: type as EventInput["event_type"],
    status: status as EventInput["status"],
    custom_type_name: customType,
    event_date: date,
    event_time: text("event_time") || null,
    location: text("location") || null,
    url: url || null,
    notes: text("notes") || null,
  };
}

export function changedEventFields(data: EventInput, original: RoleEvent): Partial<EventInput> {
  return Object.fromEntries(
    Object.entries(data).filter(([key, value]) => value !== original[key as keyof EventInput]),
  );
}
