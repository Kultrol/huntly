import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, useLocation } from "react-router";
import { beforeEach, expect, it } from "vitest";
import AppRoutes from "@/app/AppRoutes";
import AuthProvider from "@/features/auth/session/AuthProvider";
import { ThemeProvider } from "@/theme/ThemeProvider";
import { jsonResponse, mockApiFetch, signedInSession } from "../auth/fixtures";

const shellResponses = {
  "/auth/me": signedInSession,
  "/tracked-roles/": [],
  "/companies/": [],
  "/contacts/": [],
  "/events/upcoming": { user_id: signedInSession.user.id, events: [] },
};

type ShellPath = keyof typeof shellResponses;

beforeEach(() => {
  mockApiFetch().mockImplementation(async (input, options) => {
    const url = new URL(String(input));
    const path = url.pathname as ShellPath;
    if ((options?.method ?? "GET") !== "GET" || !Object.hasOwn(shellResponses, path)) {
      throw new Error(`Unexpected sidebar request ${options?.method ?? "GET"} ${path}`);
    }
    if (path === "/events/upcoming" && !/^\d{4}-\d{2}-\d{2}$/.test(url.searchParams.get("from_date") ?? "")) {
      throw new Error("The upcoming events request must include a calendar date.");
    }
    return jsonResponse(shellResponses[path]);
  });
});

function CurrentLocation() {
  const { pathname, search, hash } = useLocation();
  return <span data-testid="current-location" hidden>{pathname + search + hash}</span>;
}

function renderSignedInApp() {
  return render(
    <MemoryRouter initialEntries={["/dashboard"]}>
      <CurrentLocation />
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </MemoryRouter>,
    { wrapper: ThemeProvider },
  );
}

function workspaceNav() {
  return within(screen.getByRole("navigation", { name: "Workspace" }));
}

it("marks the dashboard as the current workspace page", async () => {
  renderSignedInApp();
  await screen.findByRole("heading", { name: "Welcome Kevin" });

  const workspace = workspaceNav();
  const dashboard = workspace.getByText("Dashboard");
  expect(dashboard.closest("[aria-current='page']")).not.toBeNull();
  expect(dashboard.closest("a")).toBeNull();
  expect(workspace.getByRole("link", { name: "Roles" }).getAttribute("href")).toBe("/roles");
  for (const label of ["Companies", "Contacts"]) {
    expect(workspace.getByRole("button", { name: label }).getAttribute("aria-disabled")).toBe("true");
  }
});

it("explains unavailable sidebar actions without leaving the dashboard", async () => {
  renderSignedInApp();
  await screen.findByRole("heading", { name: "Welcome Kevin" });
  const unavailableMessage = "This feature isn't implemented just yet.";
  const settings = screen.getByRole("button", { name: "Settings" });

  expect(settings.getAttribute("aria-disabled")).toBe("true");
  fireEvent.click(settings);
  expect(await screen.findByText(unavailableMessage)).not.toBeNull();
  expect(screen.getByTestId("current-location").textContent).toBe("/dashboard");
  fireEvent.keyDown(settings, { key: "Escape" });
  await waitFor(() => expect(screen.queryByText(unavailableMessage)).toBeNull());

  fireEvent.mouseEnter(settings);
  expect(await screen.findByText(unavailableMessage)).not.toBeNull();
  fireEvent.mouseLeave(settings);
  await waitFor(() => expect(screen.queryByText(unavailableMessage)).toBeNull());

  expect(screen.getByRole("button", { name: "Logout" }).hasAttribute("aria-disabled")).toBe(false);
});

it("moves between the dashboard and roles from the workspace navigation", async () => {
  renderSignedInApp();
  await screen.findByRole("heading", { name: "Welcome Kevin" });

  fireEvent.click(workspaceNav().getByRole("link", { name: "Roles" }));

  expect(screen.getByTestId("current-location").textContent).toBe("/roles");
  const roles = workspaceNav().getByText("Roles");
  expect(roles.closest("[aria-current='page']")).not.toBeNull();
  expect(roles.closest("a")).toBeNull();
  expect(workspaceNav().getByRole("link", { name: "Dashboard" }).getAttribute("href")).toBe("/dashboard");
  for (const label of ["Companies", "Contacts"]) {
    expect(workspaceNav().getByRole("button", { name: label }).getAttribute("aria-disabled")).toBe("true");
  }
  expect(screen.getByRole("button", { name: "Settings" }).getAttribute("aria-disabled")).toBe("true");

  fireEvent.click(workspaceNav().getByRole("link", { name: "Dashboard" }));
  expect(await screen.findByRole("heading", { name: "Welcome Kevin" })).not.toBeNull();
  expect(screen.getByTestId("current-location").textContent).toBe("/dashboard");
});
