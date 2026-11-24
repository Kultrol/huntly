import { test, expect } from "@playwright/test";

const user = { id: "responsive-user", name: "Kevin", email: "kevin@example.test" };
const role = {
  id: "responsive-role", user_id: user.id, company_id: null,
  title: "Platform engineer — accessibility and internal developer tools",
  status: "interview", role_type: "full_time", priority: "high", location: "Miami",
  applied_at: "2026-11-01T12:00:00Z", updated_at: "2026-11-01T12:00:00Z",
  salary_min: "90000", salary_max: "120000", salary_currency: "USD",
  listing_url: "https://example.test/jobs/platform", notes: null,
  description: "Build accessible tools. ".repeat(20),
};
const event = {
  id: "responsive-event", tracked_role_id: role.id,
  title: "Technical interview and portfolio discussion", event_type: "interview",
  custom_type_name: null, status: "scheduled", event_date: "2030-11-20",
  event_time: "09:30:00", notes: "Prepare project examples. ".repeat(12),
  location: "Video call", url: null,
};

async function fixtures(page, { empty = false, failList = false, failSave = false, companies = [], roles = empty ? [] : [role] } = {}) {
  const events = empty ? [] : [event];
  let failedLists = 0;
  // Match only the app's /api prefix. A glob of **/api/** also catches Vite
  // modules such as src/features/auth/api/login.ts and returns JSON for them.
  await page.route((url) => url.pathname.startsWith("/api/"), async (route) => {
    const path = new URL(route.request().url()).pathname.replace(/^\/api/, "");
    const method = route.request().method();
    const reply = (body, status = 200) => route.fulfill({ status, json: body });
    if (path === "/auth/me") return reply({ user, csrf_token: "responsive-csrf" });
    if (path === "/contacts/") return reply([]);
    if (path === "/companies/" && method === "GET") return reply(companies);
    if (path === "/companies/" && method === "POST") {
      const company = {
        user_id: user.id, id: `company-${companies.length + 1}`,
        website: null, linkedin_url: null, location: null, notes: null,
        ...route.request().postDataJSON(),
      };
      companies.push(company);
      return reply(company, 201);
    }
    if (path.startsWith("/companies/") && method === "PATCH") {
      const company = companies.find(({ id }) => path === `/companies/${id}`);
      if (!company) return reply({ detail: "Company not found" }, 404);
      Object.assign(company, route.request().postDataJSON());
      return reply(company);
    }
    if (path === "/events/upcoming") return reply({ user_id: user.id, events });
    if (path === "/events/") return reply(events);
    if (path === "/tracked-roles/" && method === "GET") {
      // Dev StrictMode aborts the first load, so the visible retry needs the
      // second mount request to fail as well. The click after that succeeds.
      if (failList && failedLists < 2) {
        failedLists += 1;
        return reply({}, 500);
      }
      return reply(roles);
    }
    if (path === "/tracked-roles/" && method === "POST") {
      if (failSave) { failSave = false; return reply({}, 500); }
      const created = { ...role, ...route.request().postDataJSON(), id: "new-role" };
      roles.push(created);
      return reply(created, 201);
    }
    return reply({ detail: `Unexpected fixture request: ${method} ${path}` }, 400);
  });
}

async function noPageOverflow(page) {
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(overflow).toBeLessThanOrEqual(1);
}

async function dialogFits(page) {
  const bounds = await page.getByRole("dialog").boundingBox();
  const viewport = page.viewportSize();
  expect(bounds).not.toBeNull();
  expect(bounds.x).toBeGreaterThanOrEqual(15);
  expect(bounds.x + bounds.width).toBeLessThanOrEqual(viewport.width - 15);
  expect(bounds.y).toBeGreaterThanOrEqual(15);
  expect(bounds.y + bounds.height).toBeLessThanOrEqual(viewport.height - 15);
}

test("workspace reflows from mobile to ultrawide with populated data", async ({ page }, testInfo) => {
  test.setTimeout(120_000);
  await fixtures(page);
  const sizes = [[320, 568], [390, 844], [430, 932], [639, 900], [640, 900],
    [767, 900], [768, 900], [1023, 900], [1024, 900], [1279, 900], [1280, 900],
    [1440, 900], [1920, 1080], [2560, 1440], [3440, 1440], [5120, 1440], [844, 390]];

  for (const [width, height] of sizes) {
    await page.setViewportSize({ width, height });
    await page.goto("/dashboard");
    await expect(page.getByRole("heading", { name: "Welcome Kevin" })).toBeVisible();
    await noPageOverflow(page);
    const trackerRole = page.getByRole("button", { name: `View ${role.title}`, exact: true });
    await trackerRole.focus();
    await trackerRole.press("Enter");
    const preview = page.getByRole("dialog", { name: role.title, exact: true });
    await expect(preview).toBeVisible();
    await dialogFits(page);
    if ([320, 1440, 3440].includes(width)) {
      await page.screenshot({ path: testInfo.outputPath(`dashboard-role-${width}.png`), fullPage: true });
    }
    await preview.getByRole("button", { name: "Edit role", exact: true }).click();
    const editor = page.getByRole("dialog", { name: "Edit role", exact: true });
    await expect(editor).toBeVisible();
    await dialogFits(page);
    await editor.getByRole("button", { name: "Cancel", exact: true }).click();
    await expect(preview).toBeVisible();
    await preview.getByRole("button", { name: "Delete role", exact: true }).click();
    const confirmation = page.getByRole("dialog", { name: "Delete role?", exact: true });
    await expect(confirmation).toBeVisible();
    await confirmation.getByRole("button", { name: "Cancel", exact: true }).click();
    await preview.getByRole("button", { name: "Close", exact: true }).click();
    await expect(trackerRole).toBeFocused();
    await page.getByRole("link", { name: "View roles" }).click();
    await expect(page).toHaveURL(/\/roles$/);
    await page.getByRole("button", { name: role.title, exact: true }).click();
    const details = page.getByRole("region", { name: `${role.title} details`, exact: true });
    await expect(details.getByText(event.title, { exact: true })).toBeVisible();
    await expect(details.getByText("Last updated", { exact: true })).toBeVisible();
    await noPageOverflow(page);
    if (width >= 1920) {
      const shell = await page.locator('[data-slot="sidebar-wrapper"]').boundingBox();
      const nav = await page.locator('[data-slot="sidebar-container"]').boundingBox();
      expect(Math.abs(shell.x - (width - shell.width) / 2)).toBeLessThan(2);
      expect(Math.abs(nav.x - shell.x)).toBeLessThan(2);
      const content = await page.locator("main .page-gutters > div").boundingBox();
      expect(content.width).toBeLessThanOrEqual(1281);
    }
    if ([320, 1440, 3440].includes(width)) {
      await page.screenshot({ path: testInfo.outputPath(`roles-${width}.png`), fullPage: true });
    }
    await details.getByRole("button", { name: "Add event" }).click();
    await expect(page.getByRole("dialog", { name: "Add event" })).toBeVisible();
    await dialogFits(page);
    await page.getByRole("button", { name: "Cancel", exact: true }).click();
    await page.getByRole("button", { name: "Add role", exact: true }).click();
    await dialogFits(page);
    await page.getByRole("textbox", { name: "Notes", exact: true }).fill("A draft at every viewport.");
    const submit = page.getByRole("dialog").getByRole("button", { name: "Add role", exact: true });
    await submit.scrollIntoViewIfNeeded();
    await expect(submit).toBeInViewport();
    await page.getByRole("button", { name: "Cancel", exact: true }).click();
  }
});

test("mobile navigation, keyboard focus, touch targets, and failed saves", async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await fixtures(page, { failSave: true });
  await page.goto("/dashboard");
  const dashboardAdd = page.getByRole("button", { name: "Add role", exact: true });
  await dashboardAdd.click();
  const dashboardForm = page.getByRole("dialog", { name: "Add role", exact: true });
  await expect(dashboardForm).toBeVisible();
  await dialogFits(page);
  await dashboardForm.getByRole("textbox", { name: "Role title (required)" }).fill("Dashboard draft");
  await dashboardForm.getByRole("button", { name: "Cancel", exact: true }).click();
  await expect(dashboardAdd).toBeFocused();
  await expect(page).toHaveURL(/\/dashboard$/);
  const toggle = page.getByRole("button", { name: "Toggle Sidebar" });
  await toggle.click();
  const drawer = page.getByRole("dialog", { name: "Sidebar" });
  await drawer.getByRole("button", { name: "Close", exact: true }).click();
  await expect(toggle).toBeFocused();
  await toggle.click();
  await drawer.getByRole("link", { name: "Roles", exact: true }).click();
  await expect(drawer).toBeHidden();
  const add = page.getByRole("button", { name: "Add role", exact: true });
  await add.click();
  const dialog = page.getByRole("dialog", { name: "Add role" });
  await dialog.getByRole("textbox", { name: "Role title (required)" }).fill("Saved draft");
  await dialog.getByRole("combobox", { name: "Status (required)" }).click();
  await page.getByRole("option", { name: "Applied", exact: true }).click();
  await dialog.getByRole("combobox", { name: "Company", exact: true }).click();
  await page.getByRole("option", { name: "Unassigned", exact: true }).click();
  await dialog.getByRole("button", { name: "Add role", exact: true }).click();
  await expect(dialog.getByRole("alert")).toBeVisible();
  await expect(dialog.getByRole("textbox", { name: "Role title (required)" })).toHaveValue("Saved draft");
  if (testInfo.project.name === "webkit-touch") {
    for (const locator of [dialog.getByRole("button", { name: "Add role", exact: true }), dialog.getByRole("combobox", { name: "Status (required)" })]) {
      expect((await locator.boundingBox()).height).toBeGreaterThanOrEqual(44);
    }
  }
  await dialog.getByRole("button", { name: "Cancel", exact: true }).click();
  await expect(add).toBeFocused();
});

test("empty, retry, dark mode, and reduced motion", async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 320, height: 568 });
  await page.emulateMedia({ colorScheme: "dark", reducedMotion: "reduce" });
  await fixtures(page, { empty: true, failList: true });
  await page.goto("/roles");
  await expect(page.getByRole("alert")).toBeVisible();
  await noPageOverflow(page);
  await page.getByRole("button", { name: "Retry roles" }).click();
  await expect(page.getByText("No roles yet. Add a role to start tracking it.")).toBeVisible();
  await expect(page.locator("html")).toHaveClass(/dark/);
  await page.screenshot({ path: testInfo.outputPath("roles-empty-dark-320.png"), fullPage: true });
  await noPageOverflow(page);
});


test("keeps a dashboard role draft while creating a company and opens its workspace", async ({ page }, testInfo) => {
  const touch = testInfo.project.name === "webkit-touch";
  await page.setViewportSize(touch ? { width: 320, height: 568 } : { width: 3440, height: 1440 });
  await fixtures(page);
  await page.goto("/dashboard");
  await page.getByRole("button", { name: "Add role", exact: true }).click();
  const roleForm = page.getByRole("dialog", { name: "Add role", exact: true });
  await roleForm.getByLabel("Role title (required)").fill("Analyst");
  await roleForm.getByRole("combobox", { name: "Status (required)" }).click();
  await page.getByRole("option", { name: "Saved", exact: true }).click();
  await roleForm.getByRole("button", { name: "New company" }).click();
  const companyForm = page.getByRole("dialog", { name: "Add company", exact: true });
  await companyForm.getByLabel("Company name (required)").fill("Meridian");
  await companyForm.getByLabel("Location").fill("Miami");
  await companyForm.getByRole("button", { name: "Add company" }).click();
  await expect(roleForm.getByLabel("Role title (required)")).toHaveValue("Analyst");
  await expect(roleForm.getByRole("combobox", { name: "Company", exact: true })).toContainText("Meridian");
  await roleForm.getByRole("button", { name: "Add role", exact: true }).click();
  const saved = page.getByRole("dialog", { name: "Analyst" });
  await expect(saved.getByText("Meridian", { exact: true })).toBeVisible();
  await saved.getByRole("button", { name: "Close", exact: true }).click();
  await page.getByRole("link", { name: "View companies" }).click();
  await page.getByRole("searchbox", { name: "Search companies" }).fill("Miami");
  await page.getByRole("button", { name: "View Meridian" }).click();
  const details = page.getByRole("complementary", { name: "Company details" });
  await expect(details.getByText("Miami", { exact: true })).toBeVisible();
  await expect(details.getByText("Analyst", { exact: true })).toBeVisible();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await noPageOverflow(page);
});

test("company list and details scroll independently and preserve position through edits and mobile Back", async ({ page }) => {
  const companies = Array.from({ length: 64 }, (_, index) => ({
    id: `studio-${index}`, user_id: user.id, name: `Studio ${String(index + 1).padStart(2, "0")}`,
    location: index % 2 ? "Remote" : "Miami", website: null, linkedin_url: null, notes: null,
  }));
  const selected = companies[3];
  const roles = Array.from({ length: 36 }, (_, index) => ({
    ...role, id: `studio-role-${index}`, company_id: selected.id, title: `Directory engineer ${index + 1}`,
  }));
  await fixtures(page, { companies, roles });
  await page.setViewportSize({ width: 1440, height: 800 });
  await page.goto("/companies");
  const search = page.getByRole("searchbox", { name: "Search companies" });
  const list = page.getByRole("region", { name: "Company list" });
  const details = page.getByRole("complementary", { name: "Company details" });

  async function editNotes(note) {
    await details.getByRole("button", { name: "Edit company" }).click();
    const form = page.getByRole("dialog", { name: "Edit company" });
    await form.getByRole("textbox", { name: "Notes" }).fill(note);
    await form.getByRole("button", { name: "Save changes" }).click();
    await expect(form).toBeHidden();
    await expect(details.getByText(note, { exact: true })).toBeVisible();
  }

  await list.getByRole("button", { name: `View ${selected.name}`, exact: true }).click();
  const heading = details.getByRole("heading", { name: selected.name, exact: true });
  const roleTitles = details.getByText(/^Directory engineer \d+$/);
  await expect(heading).toBeInViewport();
  await expect(roleTitles).toHaveCount(roles.length);
  await expect(page.getByRole("dialog")).toHaveCount(0);

  const headingBeforeScroll = await heading.boundingBox();
  const searchBeforeScroll = await search.boundingBox();
  const pageBeforeScroll = await page.evaluate(() => window.scrollY);
  await list.evaluate((node) => { node.scrollTop = node.scrollHeight; });
  const scrollPosition = await list.evaluate((node) => node.scrollTop);
  expect(scrollPosition).toBeGreaterThan(0);
  const lastCompany = companies.at(-1);
  const lastRow = list.getByRole("button", { name: `View ${lastCompany.name}`, exact: true });
  await expect(lastRow).toBeInViewport();
  expect(await heading.boundingBox()).toEqual(headingBeforeScroll);
  expect(await search.boundingBox()).toEqual(searchBeforeScroll);
  expect(await page.evaluate(() => window.scrollY)).toBe(pageBeforeScroll);

  await expect(roleTitles.last()).not.toBeInViewport();
  await roleTitles.last().scrollIntoViewIfNeeded();
  await expect(roleTitles.last()).toBeInViewport();
  expect(await list.evaluate((node) => node.scrollTop)).toBe(scrollPosition);
  expect(await page.evaluate(() => window.scrollY)).toBe(pageBeforeScroll);
  await lastRow.focus();
  await lastRow.press("Enter");
  await expect(details.getByRole("heading", { name: lastCompany.name, exact: true })).toBeInViewport();
  await expect(details.and(page.locator(":focus-within"))).toBeVisible();
  await editNotes("Discuss hybrid scheduling with the recruiter.");
  await expect(lastRow).toHaveAttribute("aria-current", "true");
  expect(await list.evaluate((node) => node.scrollTop)).toBe(scrollPosition);
  await noPageOverflow(page);

  await page.setViewportSize({ width: 390, height: 700 });
  await page.goto("/companies");
  await search.fill("Remote");
  const mobileCompany = companies[47];
  const mobileRow = list.getByRole("button", { name: `View ${mobileCompany.name}`, exact: true });
  await mobileRow.scrollIntoViewIfNeeded();
  const mobileScroll = await list.evaluate((node) => node.scrollTop);
  expect(mobileScroll).toBeGreaterThan(0);
  await mobileRow.click();
  await expect(details.getByRole("heading", { name: mobileCompany.name, exact: true })).toBeInViewport();
  await expect(list).toBeHidden();
  await editNotes("Follow up after the portfolio review.");
  await details.getByRole("button", { name: "Back to companies" }).click();
  await expect(search).toHaveValue("Remote");
  await expect(mobileRow).toBeFocused();
  await expect(mobileRow).toBeInViewport();
  expect(await list.evaluate((node) => node.scrollTop)).toBe(mobileScroll);
  await noPageOverflow(page);
});
