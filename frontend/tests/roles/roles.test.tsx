import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { beforeEach, expect, it, vi } from "vitest";
import AppRoutes from "@/app/AppRoutes";
import AuthProvider from "@/features/auth/session/AuthProvider";
import type { TrackedRole } from "@/features/roles/types";
import { ThemeProvider } from "@/theme/ThemeProvider";
import { createDeferredResponse, jsonResponse, mockApiFetch, signedInSession } from "../auth/fixtures";

const role: TrackedRole = {
  id: "role-1",
  user_id: signedInSession.user.id,
  company_id: "company-1",
  title: "Platform Engineer",
  status: "interview",
  location: "Miami",
  role_type: "full_time",
  priority: "high",
  listing_url: "https://example.com/job",
  salary_min: "85000.50",
  salary_max: null,
  salary_currency: "USD",
  applied_at: "2026-11-08T15:40:00Z",
  description: "Build internal tools.",
  notes: "Ask about the team.",
  updated_at: "2026-11-10T15:40:00Z",
};

let records: TrackedRole[];
let companies: { id: string; name: string; user_id: string }[];
const post = vi.fn<(options: RequestInit) => Response | Promise<Response>>();
const patch = vi.fn<(options: RequestInit) => Response>();
const remove = vi.fn<() => Response>();
const list = vi.fn<() => Response>();
const listCompanies = vi.fn<() => Response>();

beforeEach(() => {
  records = [role];
  companies = [{ id: "company-1", user_id: role.user_id, name: "Northstar Labs" }];
  list.mockImplementation(() => jsonResponse(records));
  listCompanies.mockImplementation(() => jsonResponse(companies));
  post.mockImplementation((options) => jsonResponse({ ...role, id: "new-role", company_id: null, ...JSON.parse(String(options.body)) }, 201));
  patch.mockImplementation((options) => jsonResponse({ ...role, ...JSON.parse(String(options.body)) }));
  remove.mockImplementation(() => new Response(null, { status: 204 }));
  mockApiFetch().mockImplementation(async (input, options = {}) => {
    const path = new URL(String(input)).pathname;
    const method = options.method ?? "GET";
    if (path === "/auth/me" && method === "GET") return jsonResponse(signedInSession);
    if (path === "/events/upcoming") return jsonResponse({ user_id: role.user_id, events: [] });
    if (path === "/events/") return jsonResponse([]);
    if (path === "/companies/" && method === "GET") return listCompanies();
    if (path === "/companies/" && method === "POST") {
      const saved = { id: "company-2", user_id: role.user_id, ...JSON.parse(String(options.body)) };
      companies.push(saved);
      return jsonResponse(saved, 201);
    }
    if (path === "/tracked-roles/" && method === "GET") return list();
    if (path === "/tracked-roles/" && method === "POST") return post(options);
    if (path === "/tracked-roles/role-1" && method === "PATCH") return patch(options);
    if (path === "/tracked-roles/role-1" && method === "DELETE") return remove();
    throw new Error(`Unexpected request ${method} ${path}`);
  });
});

function renderRoles() {
  render(
    <MemoryRouter initialEntries={["/roles"]}>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </MemoryRouter>,
    { wrapper: ThemeProvider },
  );
}

async function choose(control: HTMLElement, label: string) {
  fireEvent.click(control);
  const option = await screen.findByRole("option", { name: label });
  fireEvent.pointerDown(option, { pointerType: "mouse" });
  fireEvent.mouseUp(option);
  fireEvent.click(option, { detail: 1 });
  await waitFor(() => expect(control.textContent).toContain(label));
}

async function openRole() {
  fireEvent.click(await screen.findByRole("button", { name: role.title }));
  return within(await screen.findByRole("region", { name: `${role.title} details` }));
}

it("retries failed role and company loads and keeps the search and filter when closing details", async () => {
  list.mockReturnValueOnce(jsonResponse({}, 500));
  listCompanies.mockReturnValueOnce(jsonResponse({}, 500));
  renderRoles();

  fireEvent.click(await screen.findByRole("button", { name: "Retry roles" }));
  await screen.findByText("Northstar Labs");
  const search = screen.getByRole<HTMLInputElement>("searchbox", { name: "Search roles" });
  const filter = screen.getByRole<HTMLSelectElement>("combobox", { name: "Filter by status" });
  fireEvent.change(search, { target: { value: "Northstar" } });
  await choose(filter, "Saved");
  expect(screen.getByText("No roles match your search or filters.")).toBeDefined();
  await choose(filter, "Interview");

  const panel = await openRole();
  expect(panel.getByText("Build internal tools.")).toBeDefined();
  const salary = new Intl.NumberFormat().format(85_000.5);
  expect(panel.getByText(`${salary}+ USD`)).toBeDefined();
  expect(panel.getByRole("link", { name: "Open job listing" }).getAttribute("href")).toBe(role.listing_url);
  fireEvent.click(screen.getByRole("button", { name: role.title }));
  await waitFor(() => expect(screen.queryByRole("region", { name: `${role.title} details` })).toBeNull());
  expect(search.value).toBe("Northstar");
  expect(filter.textContent).toContain("Interview");
});

it("retries company names from the table and restores company search without reloading roles", async () => {
  listCompanies.mockReturnValueOnce(jsonResponse({}, 500));
  renderRoles();

  const retry = await screen.findByRole("button", { name: "Retry companies" });
  expect(screen.getByRole("button", { name: role.title })).toBeDefined();
  const search = screen.getByRole<HTMLInputElement>("searchbox", { name: "Search roles" });
  fireEvent.change(search, { target: { value: "Northstar" } });
  expect(screen.getByText("No roles match your search or filters.")).toBeDefined();

  fireEvent.click(retry);
  await screen.findByText("Northstar Labs");
  expect(screen.getByRole("button", { name: role.title })).toBeDefined();
  expect(search.value).toBe("Northstar");
  expect(screen.queryByRole("button", { name: "Retry companies" })).toBeNull();
  expect(list).toHaveBeenCalledTimes(1);
  expect(listCompanies).toHaveBeenCalledTimes(2);
});

it("creates a role with validated fields, omits company_id, and retains a draft after a failed save", async () => {
  records = [];
  const request = createDeferredResponse();
  post.mockReturnValueOnce(request.promise);
  renderRoles();

  await screen.findByText("No roles yet. Add a role to start tracking it.");
  fireEvent.click(screen.getByRole("button", { name: "Add role" }));
  const panel = within(await screen.findByRole("dialog", { name: "Add role" }));
  expect(panel.getByRole("combobox", { name: "Company" }).textContent).toContain("Unassigned");

  const title = panel.getByRole<HTMLInputElement>("textbox", { name: "Role title (required)" });
  fireEvent.change(title, { target: { value: "  Frontend Developer  " } });
  await choose(panel.getByRole("combobox", { name: "Status (required)" }), "Applied");
  await choose(panel.getByRole("combobox", { name: "Role type" }), "Contract");
  await choose(panel.getByRole("combobox", { name: "Priority" }), "High");
  fireEvent.change(panel.getByRole("textbox", { name: "Location" }), { target: { value: "Miami" } });
  fireEvent.change(panel.getByLabelText("Application date"), { target: { value: "2026-11-10" } });
  fireEvent.change(panel.getByRole("textbox", { name: "Listing URL" }), { target: { value: "https://example.com/listing" } });
  fireEvent.change(panel.getByRole("textbox", { name: "Description" }), { target: { value: "Build usable interfaces." } });
  fireEvent.change(panel.getByRole("textbox", { name: "Notes" }), { target: { value: "Follow up next week." } });
  fireEvent.change(panel.getByRole("spinbutton", { name: "Minimum" }), { target: { value: "91000.50" } });
  fireEvent.change(panel.getByRole("spinbutton", { name: "Maximum" }), { target: { value: "90000" } });
  fireEvent.change(panel.getByRole("textbox", { name: "Currency" }), { target: { value: "USD" } });

  const form = title.form!;
  fireEvent.submit(form);
  expect(panel.getByRole("alert").textContent).toBe("Minimum salary cannot exceed maximum salary.");
  expect(post).not.toHaveBeenCalled();

  fireEvent.change(panel.getByRole("spinbutton", { name: "Maximum" }), { target: { value: "105000" } });
  fireEvent.submit(form);
  expect(panel.getByRole<HTMLButtonElement>("button", { name: "Saving…" }).disabled).toBe(true);
  const requestOptions = post.mock.calls[0][0];
  expect(new Headers(requestOptions.headers).get("X-CSRF-Token")).toBe(signedInSession.csrf_token);
  expect(JSON.parse(String(requestOptions.body))).toEqual({
    title: "Frontend Developer",
    status: "applied",
    role_type: "contract",
    priority: "high",
    location: "Miami",
    applied_at: new Date("2026-11-10T00:00:00").toISOString(),
    listing_url: "https://example.com/listing",
    salary_min: "91000.50",
    salary_max: "105000",
    salary_currency: "USD",
    description: "Build usable interfaces.",
    notes: "Follow up next week.",
  });

  await act(async () => request.resolve(jsonResponse({}, 500)));
  expect(panel.getByRole("alert").textContent).toContain("server is unavailable");
  expect(title.value).toContain("Frontend Developer");
  fireEvent.submit(form);
  await screen.findByRole("region", { name: "Frontend Developer details" });
  expect(post).toHaveBeenCalledTimes(2);
});

it("adds a company inline and submits the role draft with that company selected", async () => {
  renderRoles();
  fireEvent.click(await screen.findByRole("button", { name: "Add role" }));
  const form = within(await screen.findByRole("dialog", { name: "Add role" }));
  const title = form.getByLabelText<HTMLInputElement>("Role title (required)");
  fireEvent.change(title, { target: { value: "Data Analyst" } });
  await choose(form.getByRole("combobox", { name: "Status (required)" }), "Applied");
  fireEvent.click(form.getByRole("button", { name: "New company" }));
  const companyForm = within(await screen.findByRole("dialog", { name: "Add company" }));
  fireEvent.change(companyForm.getByLabelText("Company name (required)"), { target: { value: "Meridian" } });
  fireEvent.click(companyForm.getByRole("button", { name: "Add company" }));
  await waitFor(() => expect(form.getByRole("combobox", { name: "Company" }).textContent).toContain("Meridian"));
  expect(title.value).toBe("Data Analyst");
  expect(post).not.toHaveBeenCalled();
  fireEvent.click(form.getByRole("button", { name: "Add role" }));
  await screen.findByRole("region", { name: "Data Analyst details" });
  expect(JSON.parse(String(post.mock.calls[0][0].body))).toMatchObject({
    title: "Data Analyst", status: "applied", company_id: "company-2",
  });
});

it("clears an existing company assignment without changing other role fields", async () => {
  renderRoles();
  const details = await openRole();
  fireEvent.click(details.getByRole("button", { name: "Edit role" }));
  const edit = within(await screen.findByRole("dialog", { name: "Edit role" }));
  await choose(edit.getByRole("combobox", { name: "Company" }), "Unassigned");
  fireEvent.click(edit.getByRole("button", { name: "Save changes" }));
  await waitFor(() => expect(patch).toHaveBeenCalledTimes(1));
  expect(JSON.parse(String(patch.mock.calls[0][0].body))).toEqual({ company_id: null });
});

it("edits a role from its details and sends only fields changed by the user", async () => {
  renderRoles();
  const search = await screen.findByRole<HTMLInputElement>("searchbox", { name: "Search roles" });
  fireEvent.change(search, { target: { value: "Northstar" } });
  const details = await openRole();
  fireEvent.click(details.getByRole("button", { name: "Edit role" }));
  const panel = within(await screen.findByRole("dialog", { name: "Edit role" }));
  await choose(panel.getByRole("combobox", { name: "Status (required)" }), "Offer");
  fireEvent.change(panel.getByRole("textbox", { name: "Notes" }), { target: { value: "" } });
  fireEvent.click(panel.getByRole("button", { name: "Save changes" }));

  await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  const updated = within(screen.getByRole("region", { name: `${role.title} details` }));
  expect(updated.getByText("Offer")).toBeDefined();
  expect(search.value).toBe("Northstar");
  expect(JSON.parse(String(patch.mock.calls[0][0].body))).toEqual({ status: "offer", notes: null });
});

it("keeps a role after a failed delete and removes it after a successful retry", async () => {
  remove.mockReturnValueOnce(jsonResponse({}, 500));
  renderRoles();
  const details = await openRole();
  fireEvent.click(details.getByRole("button", { name: "Delete role" }));
  const confirm = within(await screen.findByRole("dialog", { name: "Delete role?" }));
  expect(confirm.getByText(/also removes its linked events and status history/i)).toBeDefined();
  fireEvent.click(confirm.getByRole("button", { name: "Delete role" }));
  expect((await confirm.findByRole("alert")).textContent).toContain("server is unavailable");
  fireEvent.click(confirm.getByRole("button", { name: "Cancel" }));
  const restored = within(await screen.findByRole("region", { name: `${role.title} details` }));
  expect(restored.getByText("Build internal tools.")).toBeDefined();

  fireEvent.click(restored.getByRole("button", { name: "Delete role" }));
  fireEvent.click(within(await screen.findByRole("dialog", { name: "Delete role?" })).getByRole("button", { name: "Delete role" }));
  expect(await screen.findByText("No roles yet. Add a role to start tracking it.")).toBeDefined();
  await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  expect(remove).toHaveBeenCalledTimes(2);
});

it("shows aging open roles at the 14-day boundary and opens them from the summary", async () => {
  const now = Date.now();
  records = [
    { ...role, id: "stale", title: "Stale role", updated_at: new Date(now - 14 * 86_400_000).toISOString() },
    { ...role, id: "recent", title: "Recent role", updated_at: new Date(now - 13 * 86_400_000).toISOString() },
    { ...role, id: "closed", title: "Closed role", status: "accepted", updated_at: new Date(now - 30 * 86_400_000).toISOString() },
  ];
  renderRoles();
  const heading = await screen.findByRole("heading", { name: "Aging roles" });
  const card = within(heading.closest('[data-slot="card"]')! as HTMLElement);
  expect(card.getByRole("button", { name: "Stale role, 14 days since last update" })).toBeDefined();
  expect(card.queryByText("Recent role")).toBeNull();
  expect(card.queryByText("Closed role")).toBeNull();
  fireEvent.change(screen.getByRole("searchbox"), { target: { value: "does not exist" } });
  fireEvent.click(card.getByRole("button", { name: "Stale role, 14 days since last update" }));
  expect(await screen.findByRole("region", { name: "Stale role details" })).toBeDefined();
  expect(screen.getByRole<HTMLInputElement>("searchbox").value).toBe("");
});

it("preserves the role draft and focus when the keyboard changes the visible viewport", async () => {
  const viewport = Object.assign(new EventTarget(), {
    width: 390, height: 844, offsetTop: 0, offsetLeft: 0, pageTop: 0, pageLeft: 0, scale: 1,
  });
  vi.stubGlobal("visualViewport", viewport);
  renderRoles();
  fireEvent.click(await screen.findByRole("button", { name: "Add role" }));
  const dialog = await screen.findByRole("dialog", { name: "Add role" });
  const title = within(dialog).getByRole<HTMLInputElement>("textbox", { name: "Role title (required)" });
  title.focus();
  fireEvent.change(title, { target: { value: "Mobile draft" } });

  act(() => {
    viewport.height = 360;
    viewport.offsetTop = 20;
    viewport.dispatchEvent(new Event("resize"));
  });
  expect(dialog.style.top).toBe("200px");
  expect(dialog.style.getPropertyValue("--dialog-viewport-height")).toBe("360px");
  expect(title.value).toBe("Mobile draft");
  expect(document.activeElement).toBe(title);

  act(() => {
    viewport.scale = 2;
    viewport.dispatchEvent(new Event("resize"));
  });
  expect(dialog.style.top).toBe("");
  expect(dialog.style.getPropertyValue("--dialog-viewport-height")).toBe("");
  expect(title.value).toBe("Mobile draft");
});
