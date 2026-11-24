import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { expect, it, vi } from "vitest";
import AppRoutes from "@/app/AppRoutes";
import AuthProvider from "@/features/auth/session/AuthProvider";
import type { Company } from "@/features/companies/api";
import { ThemeProvider } from "@/theme/ThemeProvider";
import { jsonResponse, mockApiFetch, signedInSession } from "../auth/fixtures";

const first: Company = {
  user_id: signedInSession.user.id, id: "first", name: "Northstar",
  website: null, linkedin_url: null, location: null, notes: null,
};

function renderPage(path: string) {
  render(
    <MemoryRouter initialEntries={[path]}><AuthProvider><AppRoutes /></AuthProvider></MemoryRouter>,
    { wrapper: ThemeProvider },
  );
}

it("creates from the dashboard, keeps a duplicate-name draft, and edits and deletes from Companies", async () => {
  let companies = [first];
  const patches: unknown[] = [];
  mockApiFetch().mockImplementation(async (input, options = {}) => {
    const path = new URL(String(input)).pathname;
    const method = options.method ?? "GET";
    if (path === "/auth/me") return jsonResponse(signedInSession);
    if (path === "/events/upcoming") return jsonResponse({ user_id: first.user_id, events: [] });
    if (path === "/tracked-roles/" || path === "/contacts/") return jsonResponse([]);
    if (path === "/companies/" && method === "GET") return jsonResponse(companies);
    expect(new Headers(options.headers).get("X-CSRF-Token")).toBe(signedInSession.csrf_token);
    if (path === "/companies/" && method === "POST") {
      const body = JSON.parse(String(options.body));
      if (body.name === first.name) return jsonResponse({ detail: "Company already exists." }, 400);
      expect(body).toEqual({ name: "Meridian", location: "Miami" });
      const created = { ...first, ...body, id: "second" };
      companies.push(created);
      return jsonResponse(created, 201);
    }
    if (path === "/companies/second" && method === "PATCH") {
      const body = JSON.parse(String(options.body));
      patches.push(body);
      const updated = { ...companies[1], ...body };
      companies[1] = updated;
      return jsonResponse(updated);
    }
    if (path === "/companies/second" && method === "DELETE") {
      companies = [first];
      return new Response(null, { status: 204 });
    }
    throw new Error(`Unexpected request ${method} ${path}`);
  });

  renderPage("/dashboard");
  fireEvent.click(await screen.findByRole("tab", { name: "Companies" }));
  fireEvent.click(await screen.findByRole("button", { name: "View Northstar" }));
  fireEvent.click(within(await screen.findByRole("dialog", { name: "Northstar" })).getByRole("button", { name: "Close" }));
  fireEvent.click(screen.getByRole("button", { name: "Add company" }));
  const form = within(await screen.findByRole("dialog", { name: "Add company" }));
  const name = form.getByLabelText("Company name (required)");
  const location = form.getByLabelText<HTMLInputElement>("Location");
  fireEvent.change(name, { target: { value: "Northstar" } });
  fireEvent.change(location, { target: { value: "Miami" } });
  fireEvent.click(form.getByRole("button", { name: "Add company" }));
  expect((await form.findByRole("alert")).id).toBe(name.getAttribute("aria-describedby"));
  expect(location.value).toBe("Miami");
  fireEvent.change(name, { target: { value: " Meridian " } });
  fireEvent.click(form.getByRole("button", { name: "Add company" }));
  fireEvent.click(within(await screen.findByRole("dialog", { name: "Meridian" })).getByRole("button", { name: "Close" }));
  await screen.findByRole("button", { name: "View Meridian" });
  fireEvent.click(screen.getByRole("link", { name: "View companies" }));
  const search = await screen.findByRole<HTMLInputElement>("searchbox", { name: "Search companies" });
  fireEvent.change(search, { target: { value: "miami" } });
  fireEvent.click(await screen.findByRole("button", { name: "View Meridian" }));
  expect(screen.queryByRole("button", { name: "View Northstar" })).toBeNull();
  const profile = within(screen.getByRole("complementary", { name: "Company details" }));
  expect(profile.getByRole("heading", { name: "Meridian" })).toBeDefined();
  expect(screen.queryByRole("dialog")).toBeNull();
  fireEvent.click(profile.getByRole("button", { name: "Edit company" }));
  const edit = within(await screen.findByRole("dialog", { name: "Edit company" }));
  fireEvent.change(edit.getByLabelText("Company name (required)"), { target: { value: "Meridian Labs" } });
  fireEvent.change(edit.getByLabelText("Location"), { target: { value: "" } });
  fireEvent.click(edit.getByRole("button", { name: "Save changes" }));
  await screen.findByRole("heading", { name: "Meridian Labs" });
  expect(search.value).toBe("");
  expect(patches).toEqual([{ name: "Meridian Labs", location: null }]);
  const details = within(screen.getByRole("complementary", { name: "Company details" }));
  fireEvent.click(details.getByRole("button", { name: "Delete company" }));
  const confirm = within(await screen.findByRole("dialog", { name: "Delete company?" }));
  expect(confirm.getByText(/roles and contacts linked to Meridian Labs will be kept/i)).toBeDefined();
  fireEvent.click(confirm.getByRole("button", { name: "Delete company" }));
  await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  await screen.findByRole("button", { name: "View Northstar" });
  expect(screen.getByRole("heading", { name: "Northstar" })).toBeDefined();
  expect(screen.queryByRole("button", { name: "View Meridian Labs" })).toBeNull();
});

it("preserves stored formatting on unchanged saves and location-only edits", async () => {
  const company = { ...first, location: "", notes: "  Prepare examples\r\n  Ask about the team.\r\n" };
  const patches: unknown[] = [];
  mockApiFetch().mockImplementation(async (input, options = {}) => {
    const path = new URL(String(input)).pathname;
    if (path === "/auth/me") return jsonResponse(signedInSession);
    if (path === "/companies/") return jsonResponse([company]);
    if (path === "/tracked-roles/") return jsonResponse([]);
    if (path === "/companies/first" && options.method === "PATCH") {
      const changes = JSON.parse(String(options.body));
      patches.push(changes);
      return jsonResponse({ ...company, ...changes });
    }
    throw new Error(`Unexpected request ${path}`);
  });
  renderPage("/companies");

  fireEvent.click(await screen.findByRole("button", { name: "Edit company" }));
  fireEvent.click(within(await screen.findByRole("dialog")).getByRole("button", { name: "Save changes" }));
  await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  expect(patches).toEqual([]);

  fireEvent.click(screen.getByRole("button", { name: "Edit company" }));
  const edit = within(await screen.findByRole("dialog"));
  fireEvent.change(edit.getByLabelText("Location"), { target: { value: " Miami " } });
  fireEvent.click(edit.getByRole("button", { name: "Save changes" }));
  await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  expect(patches).toEqual([{ location: "Miami" }]);
});

it("keeps the directory usable when roles fail and shows each company's roles after retry", async () => {
  const second: Company = {
    ...first, id: "second", name: "Meridian", location: "Miami",
    website: "https://meridian.example/", linkedin_url: "https://www.linkedin.com/company/meridian/",
    notes: "Ask about the platform team.",
  };
  const roles = [
    { id: "r1", company_id: first.id, title: "Data Analyst", status: "saved" },
    { id: "r2", company_id: second.id, title: "Platform Engineer", status: "interview" },
    { id: "r3", company_id: second.id, title: "Frontend Engineer", status: "applied" },
    { id: "r4", company_id: null, title: "Unassigned role", status: "saved" },
  ].map((role) => ({ ...role, user_id: first.user_id }));
  const listCompanies = vi.fn(() => jsonResponse([first, second]));
  const listRoles = vi.fn(() => jsonResponse(roles)).mockReturnValueOnce(jsonResponse({}, 500));
  mockApiFetch().mockImplementation(async (input) => {
    const path = new URL(String(input)).pathname;
    if (path === "/auth/me") return jsonResponse(signedInSession);
    if (path === "/companies/") return listCompanies();
    if (path === "/tracked-roles/") return listRoles();
    throw new Error(`Unexpected request ${path}`);
  });
  renderPage("/companies");

  const northstar = await screen.findByRole("button", { name: "View Northstar" });
  const meridian = screen.getByRole("button", { name: "View Meridian" });
  expect(northstar.getAttribute("aria-current")).toBe("true");
  fireEvent.click(meridian);
  const details = within(screen.getByRole("complementary", { name: "Company details" }));
  expect(details.getByRole("heading", { name: "Meridian" })).toBeDefined();
  expect(details.getByText("Ask about the platform team.")).toBeDefined();
  expect(details.getByRole("link", { name: "meridian.example" }).getAttribute("href")).toBe(second.website);
  expect(details.getByRole("link", { name: /linkedin/i }).getAttribute("href")).toBe(second.linkedin_url);
  expect(screen.queryByRole("dialog")).toBeNull();
  expect(screen.getByRole("button", { name: "View Meridian", description: /role count unavailable/i })).toBe(meridian);

  fireEvent.click(await details.findByRole("button", { name: /retry.*roles/i }));
  await details.findByText("Platform Engineer");
  const roleItems = details.getAllByRole("listitem").map((item) => item.textContent);
  expect(roleItems).toEqual(expect.arrayContaining([
    expect.stringMatching(/Platform Engineer\s*Interview/),
    expect.stringMatching(/Frontend Engineer\s*Applied/),
  ]));
  expect(details.queryByText("Data Analyst")).toBeNull();
  expect(details.queryByText("Unassigned role")).toBeNull();
  expect(meridian.getAttribute("aria-current")).toBe("true");
  expect(within(meridian).getByText("2")).toBeDefined();
  expect(within(northstar).getByText("1")).toBeDefined();
  expect(listCompanies).toHaveBeenCalledTimes(1);
  expect(listRoles).toHaveBeenCalledTimes(2);

  const search = screen.getByRole("searchbox", { name: "Search companies" });
  fireEvent.change(search, { target: { value: "North" } });
  const filteredDetails = within(screen.getByRole("complementary", { name: "Company details" }));
  expect(filteredDetails.getByRole("heading", { name: "Northstar" })).toBeDefined();
  expect(filteredDetails.getByText("Data Analyst")).toBeDefined();
  expect(filteredDetails.getByText("Saved")).toBeDefined();
  expect(filteredDetails.queryByText("Platform Engineer")).toBeNull();
  fireEvent.change(search, { target: { value: "no results" } });
  expect(screen.getByText("No companies match your search.")).toBeDefined();
  expect(screen.queryByRole("heading", { name: "Northstar" })).toBeNull();
});

it("selects a newly created company and preserves a matching search", async () => {
  const companies = [first];
  mockApiFetch().mockImplementation(async (input, options = {}) => {
    const path = new URL(String(input)).pathname;
    if (path === "/auth/me") return jsonResponse(signedInSession);
    if (path === "/tracked-roles/") return jsonResponse([]);
    if (path === "/companies/" && options.method === "POST") {
      const saved = { ...first, ...JSON.parse(String(options.body)), id: "second" };
      companies.push(saved);
      return jsonResponse(saved, 201);
    }
    if (path === "/companies/") return jsonResponse(companies);
    throw new Error(`Unexpected request ${path}`);
  });
  renderPage("/companies");

  await screen.findByRole("button", { name: "View Northstar" });
  const search = screen.getByRole<HTMLInputElement>("searchbox", { name: "Search companies" });
  fireEvent.change(search, { target: { value: "North" } });
  fireEvent.click(screen.getByRole("button", { name: "Add company" }));
  const form = within(await screen.findByRole("dialog", { name: "Add company" }));
  fireEvent.change(form.getByLabelText("Company name (required)"), { target: { value: "North Bay" } });
  fireEvent.click(form.getByRole("button", { name: "Add company" }));

  await screen.findByRole("heading", { name: "North Bay" });
  expect(screen.queryByRole("dialog")).toBeNull();
  expect(screen.getByRole("button", { name: "View North Bay" }).getAttribute("aria-current")).toBe("true");
  expect(search.value).toBe("North");
  expect(screen.getByText("No tracked roles yet.")).toBeDefined();
});
