import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { expect, it } from "vitest";
import AppRoutes from "@/app/AppRoutes";
import AuthProvider from "@/features/auth/session/AuthProvider";
import type { Company } from "@/features/companies/api";
import { ThemeProvider } from "@/theme/ThemeProvider";
import { jsonResponse, mockApiFetch, signedInSession } from "../auth/fixtures";

it("creates, edits, and deletes companies and keeps a draft after a duplicate name", async () => {
  const first: Company = {
    user_id: signedInSession.user.id, id: "first", name: "Northstar",
    website: null, linkedin_url: null, location: null, notes: null,
  };
  let companies = [first];
  const patches: unknown[] = [];
  mockApiFetch().mockImplementation(async (input, options = {}) => {
    const path = new URL(String(input)).pathname;
    const method = options.method ?? "GET";
    if (path === "/auth/me") return jsonResponse(signedInSession);
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

  render(<MemoryRouter initialEntries={["/companies"]}><AuthProvider><AppRoutes /></AuthProvider></MemoryRouter>, { wrapper: ThemeProvider });
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
  const search = await screen.findByRole("searchbox", { name: "Search companies" });
  fireEvent.change(search, { target: { value: "miami" } });
  fireEvent.click(await screen.findByRole("button", { name: "View Meridian" }));
  expect(screen.queryByRole("button", { name: "View Northstar" })).toBeNull();
  fireEvent.click(within(await screen.findByRole("dialog", { name: "Meridian" })).getByRole("button", { name: "Edit company" }));
  const edit = within(await screen.findByRole("dialog", { name: "Edit company" }));
  fireEvent.change(edit.getByLabelText("Company name (required)"), { target: { value: "Meridian Labs" } });
  fireEvent.change(edit.getByLabelText("Location"), { target: { value: "" } });
  fireEvent.click(edit.getByRole("button", { name: "Save changes" }));
  const details = within(await screen.findByRole("dialog", { name: "Meridian Labs" }));
  expect(patches).toEqual([{ name: "Meridian Labs", location: null }]);
  fireEvent.click(details.getByRole("button", { name: "Delete company" }));
  const confirm = within(await screen.findByRole("dialog", { name: "Delete company?" }));
  expect(confirm.getByText(/roles and contacts linked to Meridian Labs will be kept/i)).toBeDefined();
  fireEvent.click(confirm.getByRole("button", { name: "Delete company" }));
  await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  fireEvent.change(search, { target: { value: "" } });
  await screen.findByRole("button", { name: "View Northstar" });
  expect(screen.queryByRole("button", { name: "View Meridian Labs" })).toBeNull();
});
