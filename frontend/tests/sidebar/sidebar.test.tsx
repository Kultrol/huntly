import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, useLocation } from "react-router";
import { beforeEach, expect, it, vi } from "vitest";
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
  expect(workspace.getByRole("link", { name: "Companies" }).getAttribute("href")).toBe("/companies");
  expect(workspace.getByRole("button", { name: "Contacts" }).getAttribute("aria-disabled")).toBe("true");
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
  expect(workspaceNav().getByRole("link", { name: "Companies" }).getAttribute("href")).toBe("/companies");
  expect(workspaceNav().getByRole("button", { name: "Contacts" }).getAttribute("aria-disabled")).toBe("true");
  expect(screen.getByRole("button", { name: "Settings" }).getAttribute("aria-disabled")).toBe("true");

  fireEvent.click(workspaceNav().getByRole("link", { name: "Dashboard" }));
  expect(await screen.findByRole("heading", { name: "Welcome Kevin" })).not.toBeNull();
  expect(screen.getByTestId("current-location").textContent).toBe("/dashboard");
});

it("closes the mobile navigation on selection and restores focus on dismissal", async () => {
  vi.stubGlobal("matchMedia", (query: string) => Object.assign(new EventTarget(), {
    matches: query === "(width < 48rem)", media: query,
  }));
  renderSignedInApp();
  await screen.findByRole("heading", { name: "Welcome Kevin" });
  const trigger = screen.getByRole("button", { name: "Toggle Sidebar" });
  trigger.focus();
  fireEvent.click(trigger);
  const drawer = within(await screen.findByRole("dialog", { name: "Sidebar" }));
  fireEvent.click(drawer.getByRole("button", { name: "Close" }));
  await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  await waitFor(() => expect(document.activeElement).toBe(trigger));

  fireEvent.click(trigger);
  fireEvent.click(within(await screen.findByRole("dialog", { name: "Sidebar" })).getByRole("link", { name: "Roles" }));
  await waitFor(() => expect(screen.getByTestId("current-location").textContent).toBe("/roles"));
  expect(screen.queryByRole("dialog")).toBeNull();
  expect(screen.getByRole("button", { name: "Toggle Sidebar" }).getAttribute("aria-expanded")).toBe("false");
});

it("makes collapsed desktop navigation inert while the page stays usable", async () => {
  renderSignedInApp();
  await screen.findByRole("heading", { name: "Welcome Kevin" });
  const trigger = screen.getByRole("button", { name: "Toggle Sidebar" });
  const sidebar = document.querySelector('[data-slot="sidebar-container"]')!;
  fireEvent.click(trigger);
  expect(trigger.getAttribute("aria-expanded")).toBe("false");
  expect(sidebar.hasAttribute("inert")).toBe(true);
  expect(screen.getByRole("region", { name: "Overview" })).toBeDefined();
  fireEvent.click(trigger);
  expect(trigger.getAttribute("aria-expanded")).toBe("true");
  expect(sidebar.hasAttribute("inert")).toBe(false);
});
