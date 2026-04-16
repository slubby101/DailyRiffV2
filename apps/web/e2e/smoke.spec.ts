import { test, expect } from "@playwright/test";

test("homepage has correct title", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveTitle("DailyRiff");
});

test("superadmin dashboard page loads", async ({ page }) => {
  await page.goto("/dashboard");
  await expect(page.locator("h1")).toContainText("Dashboard");
});

test("superadmin studios page loads", async ({ page }) => {
  await page.goto("/studios");
  await expect(page.locator("h1")).toContainText("Studios");
});

test("superadmin sidebar navigation is visible", async ({ page }) => {
  await page.goto("/dashboard");
  const nav = page.locator('nav[aria-label="Superadmin navigation"]');
  await expect(nav).toBeVisible();
  await expect(nav.locator("a")).toHaveCount(6);
});
