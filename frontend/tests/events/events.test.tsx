import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { beforeEach, expect, it, vi } from "vitest";
import AppRoutes from "@/app/AppRoutes";
import AuthProvider from "@/features/auth/session/AuthProvider";
import { ThemeProvider } from "@/theme/ThemeProvider";
import type { RoleEvent } from "@/features/events/types";
import { jsonResponse, mockApiFetch, signedInSession } from "../auth/fixtures";

const role = {
  id: "role-1", user_id: signedInSession.user.id, company_id: null,
  title: "Platform Engineer", status: "saved", location: null, role_type: null, priority: null,
  listing_url: null, salary_min: null, salary_max: null, salary_currency: null,
  applied_at: null, notes: null, description: null, updated_at: new Date().toISOString(),
};
const event: RoleEvent = {
  id: "event-1", tracked_role_id: role.id, title: "Technical interview",
  event_type: "interview", custom_type_name: null, event_date: "2030-11-20", event_time: "09:30:00",
  status: "scheduled", notes: "Prepare project examples.", location: null, url: null,
};
let events: RoleEvent[];
const post = vi.fn<(options: RequestInit) => Response>();
const patch = vi.fn<(options: RequestInit) => Response>();
const remove = vi.fn<() => Response>();
const upcoming = vi.fn<() => Response>();

beforeEach(() => {
  events = [event];
  upcoming.mockImplementation(() => jsonResponse({
    user_id: role.user_id,
    events: events.filter((item) => ["pending", "scheduled"].includes(item.status)),
  }));
  post.mockImplementation((options) => {
    const created = { ...event, id: "event-new", ...JSON.parse(String(options.body)) };
    events.push(created);
    return jsonResponse(created, 201);
  });
  patch.mockImplementation((options) => {
    const changed = { ...events[0], ...JSON.parse(String(options.body)) };
    events[0] = changed;
    return jsonResponse(changed);
  });
  remove.mockImplementation(() => {
    events = events.filter((item) => item.id !== event.id);
    return new Response(null, { status: 204 });
  });
  mockApiFetch().mockImplementation(async (input, options = {}) => {
    const url = new URL(String(input));
    const method = options.method ?? "GET";
    if (url.pathname === "/auth/me") return jsonResponse(signedInSession);
    if (url.pathname === "/tracked-roles/") return jsonResponse([role]);
    if (url.pathname === "/companies/") return jsonResponse([]);
    if (url.pathname === "/events/upcoming") {
      expect(url.searchParams.get("include_all_types")).toBe("true");
      return upcoming();
    }
    if (url.pathname === "/events/" && method === "GET") {
      expect(url.searchParams.get("tracked_role_id")).toBe(role.id);
      return jsonResponse(events);
    }
    if (url.pathname === "/events/" && method === "POST") return post(options);
    if (url.pathname === "/events/event-1" && method === "PATCH") return patch(options);
    if (url.pathname === "/events/event-1" && method === "DELETE") return remove();
    throw new Error(`Unexpected request ${method} ${url.pathname}`);
  });
});

async function openEvents() {
  render(
    <MemoryRouter initialEntries={["/roles"]}>
      <AuthProvider><AppRoutes /></AuthProvider>
    </MemoryRouter>, { wrapper: ThemeProvider },
  );
  fireEvent.click(await screen.findByRole("button", { name: role.title }));
  const section = within(await screen.findByRole("region", { name: "Role events" }));
  await section.findByText(event.title);
  return section;
}

async function choose(control: HTMLElement, label: string) {
  fireEvent.click(control);
  const option = await screen.findByRole("option", { name: label });
  fireEvent.pointerDown(option, { pointerType: "mouse" });
  fireEvent.mouseUp(option);
  fireEvent.click(option, { detail: 1 });
  await waitFor(() => expect(control.textContent).toContain(label));
}

it("creates custom events for the selected role and refreshes the upcoming list", async () => {
  const section = await openEvents();
  fireEvent.click(section.getByRole("button", { name: "Add event" }));
  const form = within(await screen.findByRole("dialog", { name: "Add event" }));
  fireEvent.change(form.getByRole("textbox", { name: "Event title (required)" }), { target: { value: "Portfolio review" } });
  await choose(form.getByRole("combobox", { name: "Event type (required)" }), "Custom");
  fireEvent.change(form.getByRole("textbox", { name: "Custom type (required)" }), { target: { value: "Portfolio session" } });
  await choose(form.getByRole("combobox", { name: "Status (required)" }), "Scheduled");
  fireEvent.change(form.getByLabelText("Date (required)"), { target: { value: "2030-11-25" } });
  fireEvent.click(form.getByRole("button", { name: "Add event" }));
  await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());

  const options = post.mock.calls[0][0];
  expect(new Headers(options.headers).get("X-CSRF-Token")).toBe(signedInSession.csrf_token);
  expect(JSON.parse(String(options.body))).toMatchObject({
    tracked_role_id: role.id, title: "Portfolio review", event_type: "custom",
    custom_type_name: "Portfolio session", status: "scheduled", event_time: null,
    event_date: "2030-11-25",
  });
  await section.findByText("Portfolio review");
  expect(await screen.findByRole("button", { name: "View Portfolio review for Platform Engineer" })).toBeDefined();
});

it("keeps edits after a failed save, then clears optional fields through PATCH", async () => {
  patch.mockReturnValueOnce(jsonResponse({}, 500));
  const section = await openEvents();
  fireEvent.click(section.getByRole("button", { name: "Edit Technical interview" }));
  const form = within(await screen.findByRole("dialog", { name: "Edit event" }));
  const title = form.getByRole<HTMLInputElement>("textbox", { name: "Event title (required)" });
  fireEvent.change(title, { target: { value: "Final interview" } });
  fireEvent.change(form.getByRole("textbox", { name: "Notes" }), { target: { value: "" } });
  fireEvent.click(form.getByRole("button", { name: "Save event" }));
  expect((await form.findByRole("alert")).textContent).toContain("unavailable");
  expect(title.value).toBe("Final interview");
  fireEvent.click(form.getByRole("button", { name: "Save event" }));
  await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  expect(JSON.parse(String(patch.mock.calls[1][0].body))).toEqual({ title: "Final interview", notes: null });
  await section.findByText("Final interview");
});

it("closes an unchanged event without a write and restores focus to Edit", async () => {
  const section = await openEvents();
  const edit = section.getByRole("button", { name: "Edit Technical interview" });
  fireEvent.click(edit);
  const form = within(await screen.findByRole("dialog", { name: "Edit event" }));
  fireEvent.click(form.getByRole("button", { name: "Save event" }));

  await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  await waitFor(() => expect(document.activeElement).toBe(edit));
  expect(patch).not.toHaveBeenCalled();
  expect(upcoming).toHaveBeenCalledTimes(1);
});

it("keeps an event actionable after completion fails and allows retry", async () => {
  patch.mockReturnValueOnce(jsonResponse({}, 500));
  const section = await openEvents();
  fireEvent.click(section.getByRole("button", { name: "Complete Technical interview" }));

  expect((await section.findByRole("alert")).textContent).toContain("unavailable");
  const retry = section.getByRole<HTMLButtonElement>("button", { name: "Complete Technical interview" });
  expect(retry.disabled).toBe(false);
  expect(upcoming).toHaveBeenCalledTimes(1);
  fireEvent.click(retry);

  await waitFor(() => expect(upcoming).toHaveBeenCalledTimes(2));
  expect(section.queryByRole("alert")).toBeNull();
  expect(patch).toHaveBeenCalledTimes(2);
  await waitFor(() => expect(document.activeElement).toBe(section.getByRole("button", { name: "Add event" })));
});

it("completes events without changing their dates and removes them from upcoming", async () => {
  const section = await openEvents();
  fireEvent.click(section.getByRole("button", { name: "Complete Technical interview" }));
  await waitFor(() => expect(upcoming).toHaveBeenCalledTimes(2));
  expect(JSON.parse(String(patch.mock.calls[0][0].body))).toEqual({ status: "completed" });
  expect(await screen.findByText("Nothing coming up yet.")).toBeDefined();
  await waitFor(() => expect(document.activeElement).toBe(section.getByRole("button", { name: "Add event" })));
  const history = await section.findByText("Completed and closed (1)");
  fireEvent.click(history);
  expect(section.getByText("Completed")).toBeDefined();
});

it("requires delete confirmation and retains an event when the delete fails", async () => {
  remove.mockReturnValueOnce(jsonResponse({}, 500));
  const section = await openEvents();
  fireEvent.click(section.getByRole("button", { name: "Delete Technical interview" }));
  const confirm = within(await screen.findByRole("dialog", { name: "Delete event?" }));
  expect(remove).not.toHaveBeenCalled();
  fireEvent.click(confirm.getByRole("button", { name: "Delete event" }));
  expect((await confirm.findByRole("alert")).textContent).toContain("unavailable");
  fireEvent.click(confirm.getByRole("button", { name: "Delete event" }));
  expect(await section.findByText("No events for this role yet.")).toBeDefined();
  expect(await screen.findByText("Nothing coming up yet.")).toBeDefined();
});
