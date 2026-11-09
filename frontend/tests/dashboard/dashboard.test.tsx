import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, useLocation } from "react-router";
import { beforeEach, expect, it } from "vitest";
import AppRoutes from "@/app/AppRoutes";
import AuthProvider from "@/features/auth/session/AuthProvider";
import { ThemeProvider } from "@/theme/ThemeProvider";
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
};

const dataRole = {
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

beforeEach(() => {
  responseOverrides = {};
  mockApiFetch().mockImplementation(async (input, options) => {
    const url = new URL(String(input));
    const path = url.pathname as DashboardPath;
    if ((options?.method ?? "GET") !== "GET" || !Object.hasOwn(dashboardResponses, path)) {
      throw new Error(`Unexpected dashboard request ${options?.method ?? "GET"} ${path}`);
    }
    if (path === "/events/upcoming" && !/^\d{4}-\d{2}-\d{2}$/.test(url.searchParams.get("from_date") ?? "")) {
      throw new Error("The upcoming events request must include a calendar date.");
    }
    return responseOverrides[path]?.() ?? jsonResponse(dashboardResponses[path]);
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

it("shows upcoming events and role counts with future pages disabled", async () => {
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

  const workspace = within(screen.getByRole("navigation", { name: "Workspace" }));
  for (const label of ["Roles", "Companies", "Contacts"]) {
    expect(workspace.getByRole("button", { name: label }).getAttribute("aria-disabled")).toBe("true");
  }
});

it("explains unavailable actions without changing the dashboard location", async () => {
  renderDashboard();
  await screen.findByRole("heading", { name: "Welcome Kevin" });
  const unavailableMessage = "This feature isn't implemented just yet.";
  const targets = [
    screen.getByRole("button", { name: "Roles" }),
    screen.getByRole("button", { name: "Settings" }),
    screen.getByRole("button", { name: "Add role" }),
  ];

  for (const target of targets) {
    expect(target.getAttribute("aria-disabled")).toBe("true");
    fireEvent.click(target);
    expect(await screen.findByText(unavailableMessage)).not.toBeNull();
    expect(screen.getByTestId("dashboard-location").textContent).toBe("/dashboard");
    fireEvent.keyDown(target, { key: "Escape" });
    await waitFor(() => expect(screen.queryByText(unavailableMessage)).toBeNull());
  }

  const settings = screen.getByRole("button", { name: "Settings" });
  fireEvent.mouseEnter(settings);
  expect(await screen.findByText(unavailableMessage)).not.toBeNull();
  fireEvent.mouseLeave(settings);
  await waitFor(() => expect(screen.queryByText(unavailableMessage)).toBeNull());

  expect(screen.getByRole("button", { name: "Logout" }).hasAttribute("aria-disabled")).toBe(false);
  expect(screen.getByRole("button", { name: "Switch to dark mode" }).hasAttribute("aria-disabled")).toBe(false);
  expect(screen.getByRole("button", { name: "Role status: All statuses" }).hasAttribute("aria-disabled")).toBe(false);
  expect(screen.getByLabelText("Filter roles").hasAttribute("aria-disabled")).toBe(false);
  const dashboard = within(screen.getByRole("navigation", { name: "Workspace" })).getByText("Dashboard");
  expect(dashboard.closest("[aria-disabled='true']")).toBeNull();
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

it("filters the signed-in user's read-only tables and switches the theme", async () => {
  renderDashboard();
  await screen.findByRole("heading", { name: "Welcome Kevin" });

  const roles = within(screen.getByRole("tabpanel", { name: "Roles" }));
  const frontendRow = await roles.findByRole("row", { name: /Frontend Engineer/ });
  await within(frontendRow).findByText("Northstar Labs");
  expect(frontendRow.hasAttribute("tabindex")).toBe(false);
  expect(frontendRow.hasAttribute("aria-disabled")).toBe(false);
  expect(within(frontendRow).getAllByRole("cell")).toHaveLength(6);
  expect(roles.getByRole("row", { name: /Data Engineer/ })).not.toBeNull();
  expect(screen.getByRole("button", { name: "Add role" }).getAttribute("aria-disabled")).toBe("true");

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
  expect(screen.getByRole("button", { name: "Add company" }).getAttribute("aria-disabled")).toBe("true");

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
