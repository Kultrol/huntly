import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, useLocation } from "react-router";
import { beforeEach, expect, it, vi } from "vitest";
import AppRoutes from "@/app/AppRoutes";
import AuthProvider from "@/features/auth/session/AuthProvider";
import { ThemeProvider } from "@/theme/ThemeProvider";
import type { TrackedRole } from "@/features/roles/types";
import { createDeferredResponse, jsonResponse, mockApiFetch, signedInSession } from "../auth/fixtures";

const recordMetadata = {
  user_id: signedInSession.user.id,
  created_at: "2026-11-01T12:00:00Z",
  updated_at: "2026-11-02T12:00:00Z",
  notes: null,
};

const northstar = {
  ...recordMetadata,
  id: "northstar",
  name: "Northstar Labs",
  normalized_name: "northstar labs",
  location: "Boston",
  website: "https://northstar.example/",
  linkedin_url: null,
};

const meridian = {
  ...northstar,
  id: "meridian",
  name: "Meridian Studio",
  normalized_name: "meridian studio",
  location: "Austin",
  website: null,
};

const frontendRole = {
  ...recordMetadata,
  id: "frontend-engineer",
  title: "Frontend Engineer",
  status: "interview",
  company_id: northstar.id,
  role_type: "full_time",
  location: "Boston",
  applied_at: "2026-11-01T12:00:00Z",
  priority: null,
  description: null,
  source: null,
  listing_url: null,
  salary_min: null,
  salary_max: null,
  salary_currency: null,
} satisfies TrackedRole & { source: null };

const dataRole: TrackedRole = {
  ...frontendRole,
  id: "data-engineer",
  title: "Data Engineer",
  status: "saved",
  company_id: meridian.id,
  location: "Austin",
  applied_at: null,
};

const jordan = {
  ...recordMetadata,
  id: "jordan",
  name: "Jordan Lee",
  company_id: northstar.id,
  role: "Recruiter",
  email: "jordan@northstar.example",
  phone_number: null,
  linkedin_url: null,
};

const morgan = {
  ...jordan,
  id: "morgan",
  name: "Morgan Chen",
  company_id: meridian.id,
  role: "Hiring Manager",
  email: null,
};

const upcomingEvents = [
  {
    id: "northstar-interview",
    tracked_role_id: frontendRole.id,
    title: "Technical interview",
    event_type: "interview",
    event_date: "2030-02-12",
    event_time: "10:30:00",
  },
  {
    id: "northstar-follow-up",
    tracked_role_id: frontendRole.id,
    title: "Follow up with Jordan",
    event_type: "follow_up",
    event_date: "2030-02-13",
    event_time: null,
  },
  {
    id: "meridian-deadline",
    tracked_role_id: dataRole.id,
    title: "Submit portfolio",
    event_type: "application_deadline",
    event_date: "2030-02-15",
    event_time: null,
  },
];

const dashboardResponses = {
  "/auth/me": signedInSession,
  "/tracked-roles/": [frontendRole, dataRole],
  "/companies/": [northstar, meridian],
  "/contacts/": [jordan, morgan],
  "/events/upcoming": { user_id: signedInSession.user.id, events: upcomingEvents },
};

type DashboardPath = keyof typeof dashboardResponses;
let responseOverrides: Partial<Record<DashboardPath, () => Response | Promise<Response>>>;
let currentRoles: TrackedRole[];
let currentEvents: typeof upcomingEvents;
const patchRole = vi.fn<(id: string, options: RequestInit) => Response | Promise<Response>>();
const postRole = vi.fn<(options: RequestInit) => Response | Promise<Response>>();
const removeRole = vi.fn<(id: string) => Response>();

beforeEach(() => {
  responseOverrides = {};
  currentRoles = [frontendRole, dataRole];
  currentEvents = [...upcomingEvents];
  postRole.mockReset().mockImplementation((options) => {
    const created = {
      ...frontendRole,
      ...JSON.parse(String(options.body)),
      id: "created-role",
      company_id: null,
    };
    currentRoles = [...currentRoles, created];
    return jsonResponse(created, 201);
  });
  patchRole.mockReset().mockImplementation((id, options) => {
    const saved = { ...currentRoles.find((role) => role.id === id)!, ...JSON.parse(String(options.body)) };
    currentRoles = currentRoles.map((role) => role.id === id ? saved : role);
    return jsonResponse(saved);
  });
  removeRole.mockReset().mockImplementation((id) => {
    currentRoles = currentRoles.filter((role) => role.id !== id);
    currentEvents = currentEvents.filter((event) => event.tracked_role_id !== id);
    return new Response(null, { status: 204 });
  });
  mockApiFetch().mockImplementation(async (input, options = {}) => {
    const url = new URL(String(input));
    const path = url.pathname as DashboardPath;
    const method = options.method ?? "GET";
    if (path === "/tracked-roles/" && method === "POST") return postRole(options);
    if (path.startsWith("/tracked-roles/") && method === "PATCH") {
      return patchRole(path.split("/").at(-1)!, options);
    }
    if (path.startsWith("/tracked-roles/") && method === "DELETE") {
      return removeRole(path.split("/").at(-1)!);
    }
    if ((options?.method ?? "GET") !== "GET" || !Object.hasOwn(dashboardResponses, path)) {
      throw new Error(`Unexpected dashboard request ${options?.method ?? "GET"} ${path}`);
    }
    if (path === "/events/upcoming" && !/^\d{4}-\d{2}-\d{2}$/.test(url.searchParams.get("from_date") ?? "")) {
      throw new Error("The upcoming events request must include a calendar date.");
    }
    if (responseOverrides[path]) return responseOverrides[path]();
    if (path === "/tracked-roles/") return jsonResponse(currentRoles);
    if (path === "/events/upcoming") return jsonResponse({ user_id: signedInSession.user.id, events: currentEvents });
    return jsonResponse(dashboardResponses[path]);
  });
});

function DashboardLocation() {
  const { pathname, search, hash } = useLocation();
  return <span data-testid="dashboard-location" hidden>{pathname + search + hash}</span>;
}

function renderDashboard() {
  return render(
    <MemoryRouter initialEntries={["/dashboard"]}>
      <DashboardLocation />
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </MemoryRouter>,
    { wrapper: ThemeProvider },
  );
}

async function openFrontendRole() {
  const trigger = await screen.findByRole("button", { name: "View Frontend Engineer" });
  fireEvent.click(trigger);
  const dialog = await screen.findByRole("dialog", { name: "Frontend Engineer" });
  return { trigger, dialog: within(dialog) };
}

it("creates a role from the dashboard, keeps failed drafts, and refreshes the filtered tracker", async () => {
  const pendingSave = createDeferredResponse();
  postRole.mockReturnValueOnce(pendingSave.promise);
  renderDashboard();
  await screen.findByRole("row", { name: /Frontend Engineer/ });
  fireEvent.change(screen.getByLabelText("Filter roles"), { target: { value: "Developer" } });
  const addRole = screen.getByRole("button", { name: "Add role" });
  expect(addRole.hasAttribute("aria-disabled")).toBe(false);
  fireEvent.click(addRole);
  const form = within(await screen.findByRole("dialog", { name: "Add role" }));
  const title = form.getByRole<HTMLInputElement>("textbox", { name: "Role title (required)" });
  expect(document.activeElement).toBe(title);
  expect(form.getByRole("button", { name: "Company" }).getAttribute("aria-disabled")).toBe("true");

  fireEvent.submit(title.form!);
  expect(form.getByRole("alert").textContent).toBe("Enter a role title.");
  expect(postRole).not.toHaveBeenCalled();
  fireEvent.change(title, { target: { value: "  Frontend Developer  " } });
  fireEvent.click(form.getByRole("combobox", { name: "Status (required)" }));
  const applied = await screen.findByRole("option", { name: "Applied" });
  fireEvent.pointerDown(applied, { pointerType: "mouse" });
  fireEvent.mouseUp(applied);
  fireEvent.click(applied, { detail: 1 });
  fireEvent.change(form.getByRole("textbox", { name: "Location" }), { target: { value: "Miami" } });
  fireEvent.click(form.getByRole("button", { name: "Add role" }));
  expect(form.getByRole<HTMLButtonElement>("button", { name: "Saving…" }).disabled).toBe(true);
  expect(form.getByRole<HTMLButtonElement>("button", { name: "Cancel" }).disabled).toBe(true);
  expect(form.queryByRole("button", { name: "Close" })).toBeNull();

  await act(async () => pendingSave.resolve(jsonResponse({}, 500)));
  expect((await form.findByRole("alert")).textContent).toContain("unavailable");
  expect(title.value.trim()).toBe("Frontend Developer");
  fireEvent.click(form.getByRole("button", { name: "Add role" }));
  const details = within(await screen.findByRole("dialog", { name: "Frontend Developer" }));
  expect(details.getByText("Miami")).toBeDefined();
  expect(details.getByRole("button", { name: "Edit role" })).toBeDefined();
  expect(details.getByRole("button", { name: "Delete role" })).toBeDefined();
  expect(postRole).toHaveBeenCalledTimes(2);
  const options = postRole.mock.calls[1][0];
  expect(new Headers(options.headers).get("X-CSRF-Token")).toBe(signedInSession.csrf_token);
  expect(options.credentials).toBe("include");
  const payload = JSON.parse(String(options.body));
  expect(payload).toMatchObject({ title: "Frontend Developer", status: "applied", location: "Miami" });
  expect(payload).not.toHaveProperty("company_id");
  expect(payload).not.toHaveProperty("user_id");
  fireEvent.click(details.getByRole("button", { name: "Close" }));

  await screen.findByRole("row", { name: /Frontend Developer/ });
  expect(screen.queryByRole("row", { name: /Frontend Engineer/ })).toBeNull();
  expect(screen.getByLabelText<HTMLInputElement>("Filter roles").value).toBe("Developer");
  expect(await screen.findByText("Showing 1 of 3")).toBeDefined();
  const overview = within(screen.getByRole("region", { name: "Overview" }));
  expect(overview.getByText("Applied", { selector: "dt" }).nextElementSibling?.textContent).toBe("1");
  const rolesCard = screen.getByRole("link", { name: "View roles" }).closest('[data-slot="card"]')!;
  expect(within(rolesCard as HTMLElement).getByText("3")).toBeDefined();
  await waitFor(() => expect(document.activeElement).toBe(addRole));
  expect(screen.getByTestId("dashboard-location").textContent).toBe("/dashboard");
});

it("opens Add role from an empty tracker and cancels without saving", async () => {
  currentRoles = [];
  currentEvents = [];
  renderDashboard();
  await screen.findByText("No roles yet.");
  const addRole = screen.getByRole("button", { name: "Add role" });
  fireEvent.click(addRole);
  let form = within(await screen.findByRole("dialog", { name: "Add role" }));
  fireEvent.change(form.getByRole("textbox", { name: "Role title (required)" }), { target: { value: "Discard this draft" } });
  fireEvent.click(form.getByRole("button", { name: "Cancel" }));
  await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  await waitFor(() => expect(document.activeElement).toBe(addRole));
  expect(postRole).not.toHaveBeenCalled();

  fireEvent.click(addRole);
  form = within(await screen.findByRole("dialog", { name: "Add role" }));
  expect(form.getByRole<HTMLInputElement>("textbox", { name: "Role title (required)" }).value).toBe("");
});

it("opens role details from a tracker row and returns focus without navigating", async () => {
  currentRoles[0] = {
    ...frontendRole,
    priority: "high",
    salary_min: "90000",
    salary_currency: "USD",
    description: "Build accessible interfaces.",
    notes: "Discuss the team structure.",
  };
  renderDashboard();
  const row = await screen.findByRole("row", { name: /Frontend Engineer/ });
  const trigger = within(row).getByRole("button", { name: "View Frontend Engineer" });
  expect(trigger.tagName).toBe("BUTTON");
  expect(trigger.getAttribute("aria-haspopup")).toBe("dialog");

  // Clicking a data cell works as well as activating the role title.
  fireEvent.click(within(row).getByText("Boston"));
  const dialog = within(await screen.findByRole("dialog", { name: "Frontend Engineer" }));
  expect(dialog.getByText("Northstar Labs")).toBeDefined();
  expect(dialog.getByText("Full-time")).toBeDefined();
  expect(dialog.getByText("High")).toBeDefined();
  expect(dialog.getByText(`${new Intl.NumberFormat().format(90000)}+ USD`)).toBeDefined();
  expect(dialog.getByText("Build accessible interfaces.")).toBeDefined();
  expect(dialog.getByText("Discuss the team structure.")).toBeDefined();
  fireEvent.click(dialog.getByRole("button", { name: "Close" }));

  await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  await waitFor(() => expect(document.activeElement).toBe(trigger));
  expect(screen.getByTestId("dashboard-location").textContent).toBe("/dashboard");
});

it("returns to role details after cancelling or saving an unchanged edit", async () => {
  renderDashboard();
  const { dialog } = await openFrontendRole();
  fireEvent.click(dialog.getByRole("button", { name: "Edit role" }));
  let editor = within(await screen.findByRole("dialog", { name: "Edit role" }));
  const title = editor.getByRole<HTMLInputElement>("textbox", { name: "Role title (required)" });
  expect(document.activeElement).toBe(title);
  fireEvent.change(title, { target: { value: "Discard this draft" } });
  fireEvent.click(editor.getByRole("button", { name: "Cancel" }));

  const details = within(await screen.findByRole("dialog", { name: "Frontend Engineer" }));
  expect(document.activeElement).toBe(details.getByRole("button", { name: "Edit role" }));
  fireEvent.click(details.getByRole("button", { name: "Edit role" }));
  editor = within(await screen.findByRole("dialog", { name: "Edit role" }));
  expect(editor.getByRole<HTMLInputElement>("textbox", { name: "Role title (required)" }).value).toBe(frontendRole.title);
  fireEvent.click(editor.getByRole("button", { name: "Save changes" }));
  await screen.findByRole("dialog", { name: "Frontend Engineer" });
  expect(patchRole).not.toHaveBeenCalled();
});

it("keeps failed edits, then updates role details, tracker filters, counts, and event titles", async () => {
  const pendingSave = createDeferredResponse();
  patchRole.mockReturnValueOnce(pendingSave.promise);
  renderDashboard();
  await screen.findByRole("button", { name: "View Frontend Engineer" });
  fireEvent.change(screen.getByLabelText("Filter roles"), { target: { value: "Northstar" } });
  const { dialog } = await openFrontendRole();
  fireEvent.click(dialog.getByRole("button", { name: "Edit role" }));
  const editor = within(await screen.findByRole("dialog", { name: "Edit role" }));
  const title = editor.getByRole<HTMLInputElement>("textbox", { name: "Role title (required)" });
  fireEvent.change(title, { target: { value: "Senior Frontend Engineer" } });
  fireEvent.click(editor.getByRole("combobox", { name: "Status (required)" }));
  const offer = await screen.findByRole("option", { name: "Offer" });
  fireEvent.pointerDown(offer, { pointerType: "mouse" });
  fireEvent.mouseUp(offer);
  fireEvent.click(offer, { detail: 1 });
  fireEvent.click(editor.getByRole("button", { name: "Save changes" }));
  expect(editor.getByRole<HTMLButtonElement>("button", { name: "Saving…" }).disabled).toBe(true);
  expect(editor.getByRole<HTMLButtonElement>("button", { name: "Cancel" }).disabled).toBe(true);
  expect(editor.queryByRole("button", { name: "Close" })).toBeNull();

  await act(async () => pendingSave.resolve(jsonResponse({}, 500)));
  expect((await editor.findByRole("alert")).textContent).toContain("unavailable");
  expect(title.value).toBe("Senior Frontend Engineer");
  fireEvent.click(editor.getByRole("button", { name: "Save changes" }));
  const details = within(await screen.findByRole("dialog", { name: "Senior Frontend Engineer" }));
  expect(details.getByText("Offer")).toBeDefined();
  const [id, options] = patchRole.mock.calls[1];
  expect(id).toBe(frontendRole.id);
  expect(new Headers(options.headers).get("X-CSRF-Token")).toBe(signedInSession.csrf_token);
  expect(JSON.parse(String(options.body))).toEqual({ title: "Senior Frontend Engineer", status: "offer" });
  // Let the tracker refresh under the modal before testing focus on its new row.
  await waitFor(() => expect(document.getElementById(`tracker-roles-${frontendRole.id}`)?.textContent).toBe("Senior Frontend Engineer"));
  fireEvent.click(details.getByRole("button", { name: "Close" }));

  const row = await screen.findByRole("row", { name: /Senior Frontend Engineer/ });
  expect(within(row).getByText("Offer")).toBeDefined();
  expect(screen.getByLabelText<HTMLInputElement>("Filter roles").value).toBe("Northstar");
  expect(screen.queryByRole("row", { name: /Data Engineer/ })).toBeNull();
  const overview = within(screen.getByRole("region", { name: "Overview" }));
  expect(overview.getByText("Interviews", { selector: "dt" }).nextElementSibling?.textContent).toBe("0");
  expect(overview.getByText("Offers", { selector: "dt" }).nextElementSibling?.textContent).toBe("1");
  const nextUp = within(screen.getByRole("region", { name: "Next up" }));
  expect(await nextUp.findAllByText(/Senior Frontend Engineer/)).toHaveLength(2);
  await waitFor(() => expect(document.activeElement).toBe(within(row).getByRole("button", { name: "View Senior Frontend Engineer" })));
  expect(screen.getByTestId("dashboard-location").textContent).toBe("/dashboard");
});

it("confirms deletion, retains failed deletes, and refreshes the dashboard after retry", async () => {
  removeRole.mockReturnValueOnce(jsonResponse({}, 500));
  renderDashboard();
  const { dialog } = await openFrontendRole();
  fireEvent.click(dialog.getByRole("button", { name: "Delete role" }));
  let confirmation = within(await screen.findByRole("dialog", { name: "Delete role?" }));
  expect(confirmation.getByText(/also removes its linked events and status history/)).toBeDefined();
  expect(removeRole).not.toHaveBeenCalled();
  fireEvent.click(confirmation.getByRole("button", { name: "Cancel" }));
  const details = within(await screen.findByRole("dialog", { name: "Frontend Engineer" }));
  fireEvent.click(details.getByRole("button", { name: "Delete role" }));
  confirmation = within(await screen.findByRole("dialog", { name: "Delete role?" }));
  fireEvent.click(confirmation.getByRole("button", { name: "Delete role" }));
  expect((await confirmation.findByRole("alert")).textContent).toContain("unavailable");
  fireEvent.click(confirmation.getByRole("button", { name: "Delete role" }));

  await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  await screen.findByRole("row", { name: /Data Engineer/ });
  expect(screen.queryByRole("row", { name: /Frontend Engineer/ })).toBeNull();
  expect(await screen.findByText("Showing 1 of 1")).toBeDefined();
  const nextUp = within(screen.getByRole("region", { name: "Next up" }));
  expect(await nextUp.findByText("Submit portfolio")).toBeDefined();
  expect(nextUp.queryByText("Technical interview")).toBeNull();
  expect(nextUp.queryByText("Follow up with Jordan")).toBeNull();
  const rolesCard = screen.getByRole("link", { name: "View roles" }).closest('[data-slot="card"]')!;
  expect(within(rolesCard as HTMLElement).getByText("1")).toBeDefined();
  await waitFor(() => expect(document.activeElement).toBe(screen.getByLabelText("Filter roles")));
  expect(removeRole).toHaveBeenCalledTimes(2);
});

it("shows upcoming events and role counts", async () => {
  renderDashboard();

  const nextUp = within(await screen.findByRole("region", { name: "Next up" }));
  for (const event of upcomingEvents) {
    const eventTitle = await nextUp.findByText(event.title);
    const item = eventTitle.closest("li");
    expect(item?.hasAttribute("tabindex")).toBe(false);
    expect(item?.hasAttribute("role")).toBe(false);
    expect(item?.querySelector("time")?.getAttribute("datetime")).toContain(event.event_date);
  }
  expect(nextUp.getAllByRole("listitem")).toHaveLength(upcomingEvents.length);

  const overview = within(screen.getByRole("region", { name: "Overview" }));
  const interviews = await overview.findByText("Interviews", { selector: "dt" });
  expect(interviews.nextElementSibling?.textContent).toBe("1");
  expect(interviews.closest("[tabindex]")).toBeNull();
  expect(overview.queryByRole("button")).toBeNull();
  expect(overview.getByText("Applied", { selector: "dt" }).nextElementSibling?.textContent).toBe("0");
  expect(overview.getByText("Offers", { selector: "dt" }).nextElementSibling?.textContent).toBe("0");
});

it("explains unavailable actions without changing the dashboard location", async () => {
  renderDashboard();
  await screen.findByRole("heading", { name: "Welcome Kevin" });
  const unavailableMessage = "This feature isn't implemented just yet.";
  fireEvent.click(screen.getByRole("tab", { name: "Contacts" }));
  const addContact = screen.getByRole("button", { name: "Add contact" });

  expect(addContact.getAttribute("aria-disabled")).toBe("true");
  fireEvent.click(addContact);
  expect(await screen.findByText(unavailableMessage)).not.toBeNull();
  expect(screen.getByTestId("dashboard-location").textContent).toBe("/dashboard");
  fireEvent.keyDown(addContact, { key: "Escape" });
  await waitFor(() => expect(screen.queryByText(unavailableMessage)).toBeNull());
  fireEvent.click(screen.getByRole("tab", { name: "Roles" }));

  expect(screen.getByRole("button", { name: "Switch to dark mode" }).hasAttribute("aria-disabled")).toBe(false);
  expect(screen.getByRole("button", { name: "Role status: All statuses" }).hasAttribute("aria-disabled")).toBe(false);
  expect(screen.getByLabelText("Filter roles").hasAttribute("aria-disabled")).toBe(false);
});

it("loads upcoming events after a failed request is retried", async () => {
  let requests = 0;
  responseOverrides["/events/upcoming"] = () => ++requests === 1
    ? jsonResponse({}, 500)
    : jsonResponse(dashboardResponses["/events/upcoming"]);

  renderDashboard();
  const nextUp = within(await screen.findByRole("region", { name: "Next up" }));
  fireEvent.click(await nextUp.findByRole("button", { name: "Retry upcoming events" }));

  expect(await nextUp.findByText(upcomingEvents[0].title)).not.toBeNull();
  expect(nextUp.queryByRole("alert")).toBeNull();
  expect(requests).toBe(2);
});

it("rejects another account's dashboard data until the session is confirmed", async () => {
  const nextSession = {
    user: { id: "other-user-id", name: "Taylor", email: "taylor@example.com" },
    csrf_token: "other-csrf-token",
  };
  const nextRole = {
    ...frontendRole,
    id: "other-role",
    user_id: nextSession.user.id,
    title: "Platform Engineer",
    company_id: null,
  };
  const nextEvent = {
    ...upcomingEvents[0],
    id: "other-event",
    tracked_role_id: nextRole.id,
    title: "Meet the platform team",
  };
  const refresh = createDeferredResponse();
  let cookieChanged = false;
  responseOverrides["/auth/me"] = () => cookieChanged ? refresh.promise : jsonResponse(signedInSession);
  responseOverrides["/tracked-roles/"] = () => cookieChanged ? jsonResponse([nextRole]) : jsonResponse({}, 500);
  responseOverrides["/events/upcoming"] = () => cookieChanged
    ? jsonResponse({ user_id: nextSession.user.id, events: [nextEvent] })
    : jsonResponse({}, 500);
  responseOverrides["/companies/"] = () => jsonResponse([]);
  responseOverrides["/contacts/"] = () => jsonResponse([]);

  renderDashboard();
  await screen.findByRole("heading", { name: "Welcome Kevin" });
  const roles = within(screen.getByRole("tabpanel", { name: "Roles" }));
  const nextUp = within(screen.getByRole("region", { name: "Next up" }));
  const retryRoles = await roles.findByRole("button", { name: "Retry" });
  const retryUpcoming = await nextUp.findByRole("button", { name: "Retry upcoming events" });

  // Another tab changes the cookie while this tab's session check is still in flight.
  cookieChanged = true;
  act(() => window.dispatchEvent(new StorageEvent("storage", { key: "huntly:auth-changed" })));
  fireEvent.click(retryRoles);
  fireEvent.click(retryUpcoming);
  expect((await roles.findByRole("alert")).textContent).toMatch(/could not verify the account/i);
  expect((await nextUp.findByRole("alert")).textContent).toMatch(/could not verify the account/i);
  expect(screen.getByRole("heading", { name: "Welcome Kevin" })).not.toBeNull();
  expect(roles.queryByText(nextRole.title)).toBeNull();
  expect(nextUp.queryByText(nextEvent.title)).toBeNull();

  await act(async () => refresh.resolve(jsonResponse(nextSession)));

  await screen.findByRole("heading", { name: "Welcome Taylor" });
  expect(await screen.findByRole("row", { name: /Platform Engineer/ })).not.toBeNull();
  const confirmedEvents = within(screen.getByRole("region", { name: "Next up" }));
  expect(await confirmedEvents.findByText(nextEvent.title)).not.toBeNull();
});

it("filters the signed-in user's tracker tables and switches the theme", async () => {
  renderDashboard();
  await screen.findByRole("heading", { name: "Welcome Kevin" });

  const roles = within(screen.getByRole("tabpanel", { name: "Roles" }));
  const frontendRow = await roles.findByRole("row", { name: /Frontend Engineer/ });
  await within(frontendRow).findByText("Northstar Labs");
  expect(frontendRow.hasAttribute("tabindex")).toBe(false);
  expect(frontendRow.hasAttribute("aria-disabled")).toBe(false);
  expect(within(frontendRow).getAllByRole("cell")).toHaveLength(6);
  expect(roles.getByRole("row", { name: /Data Engineer/ })).not.toBeNull();
  expect(screen.getByRole("button", { name: "Add role" }).hasAttribute("aria-disabled")).toBe(false);

  fireEvent.change(roles.getByLabelText("Filter roles"), { target: { value: "  BOSTON  " } });
  expect(roles.getByRole("row", { name: /Frontend Engineer/ })).not.toBeNull();
  expect(roles.queryByRole("row", { name: /Data Engineer/ })).toBeNull();

  fireEvent.click(roles.getByRole("button", { name: "Role status: All statuses" }));
  fireEvent.click(await screen.findByRole("menuitemradio", { name: "Saved" }));
  await waitFor(() => expect(screen.queryByRole("menu", { hidden: true })).toBeNull());
  expect(roles.queryByRole("row", { name: /Frontend Engineer/ })).toBeNull();
  expect(roles.queryByRole("row", { name: /Data Engineer/ })).toBeNull();

  fireEvent.change(roles.getByLabelText("Filter roles"), { target: { value: "" } });
  expect(roles.getByRole("row", { name: /Data Engineer/ })).not.toBeNull();

  fireEvent.click(roles.getByRole("button", { name: "Role status: Saved" }));
  expect((await screen.findByRole("menuitemradio", { name: "Saved" })).getAttribute("aria-checked")).toBe("true");
  fireEvent.click(screen.getByRole("menuitemradio", { name: "All statuses" }));
  expect(roles.getByRole("row", { name: /Frontend Engineer/ })).not.toBeNull();
  expect(roles.getByRole("row", { name: /Data Engineer/ })).not.toBeNull();

  fireEvent.click(screen.getByRole("tab", { name: "Companies" }));
  const companies = within(screen.getByRole("tabpanel", { name: "Companies" }));
  await companies.findByRole("row", { name: /Northstar Labs/ });
  expect(companies.getByRole("row", { name: /Meridian Studio/ })).not.toBeNull();
  expect(companies.getByRole("button", { name: "Add company" }).getAttribute("aria-haspopup")).toBe("dialog");

  fireEvent.change(companies.getByLabelText("Filter companies"), { target: { value: "austin" } });
  expect(companies.queryByRole("row", { name: /Northstar Labs/ })).toBeNull();
  expect(companies.getByRole("row", { name: /Meridian Studio/ })).not.toBeNull();

  fireEvent.click(screen.getByRole("tab", { name: "Contacts" }));
  const contacts = within(screen.getByRole("tabpanel", { name: "Contacts" }));
  const jordanRow = await contacts.findByRole("row", { name: /Jordan Lee/ });
  expect(within(jordanRow).getByText("Northstar Labs")).not.toBeNull();
  expect(contacts.getByRole("row", { name: /Morgan Chen/ })).not.toBeNull();
  expect(screen.getByRole("button", { name: "Add contact" }).getAttribute("aria-disabled")).toBe("true");

  fireEvent.change(contacts.getByLabelText("Filter contacts"), { target: { value: "Recruiter" } });
  expect(contacts.getByRole("row", { name: /Jordan Lee/ })).not.toBeNull();
  expect(contacts.queryByRole("row", { name: /Morgan Chen/ })).toBeNull();

  fireEvent.click(screen.getByRole("button", { name: "Switch to dark mode" }));
  expect(document.documentElement.classList.contains("dark")).toBe(true);
  expect(localStorage.getItem("huntly-theme")).toBe("dark");

  fireEvent.click(screen.getByRole("button", { name: "Switch to light mode" }));
  expect(document.documentElement.classList.contains("dark")).toBe(false);
  expect(localStorage.getItem("huntly-theme")).toBe("light");
});
