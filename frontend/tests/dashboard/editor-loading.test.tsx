import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { expect, it, vi } from "vitest";
import AppRoutes from "@/app/AppRoutes";
import AuthProvider from "@/features/auth/session/AuthProvider";
import { ThemeProvider } from "@/theme/ThemeProvider";
import { jsonResponse, mockAuthFetchWithDashboard, signedInSession } from "../auth/fixtures";

it("keeps only the latest dashboard editor when an earlier dialog finishes loading", async () => {
  let releaseRoleDialog!: () => void;
  const loadingRoleDialog = new Promise<void>((resolve) => { releaseRoleDialog = resolve; });
  vi.doMock("@/features/roles/RoleDialog", async (importOriginal) => {
    await loadingRoleDialog;
    return importOriginal();
  });
  mockAuthFetchWithDashboard().mockImplementation(async () => jsonResponse(signedInSession));
  render(
    <MemoryRouter initialEntries={["/dashboard"]}><AuthProvider><AppRoutes /></AuthProvider></MemoryRouter>,
    { wrapper: ThemeProvider },
  );

  fireEvent.click(await screen.findByRole("button", { name: "Add role" }));
  await screen.findByText("Loading role details…");
  fireEvent.click(screen.getByRole("tab", { name: "Companies" }));
  const addCompany = screen.getByRole("button", { name: "Add company" });
  fireEvent.click(addCompany);
  const companyDialog = await screen.findByRole("dialog", { name: "Add company" });
  await act(async () => {
    releaseRoleDialog();
    await vi.dynamicImportSettled();
  });

  expect(screen.getAllByRole("dialog", { hidden: true })).toHaveLength(1);
  fireEvent.click(within(companyDialog).getByRole("button", { name: "Cancel" }));
  await waitFor(() => expect(screen.queryByRole("dialog", { hidden: true })).toBeNull());
  await waitFor(() => expect(document.activeElement).toBe(addCompany));
});
