import { test, expect } from "@playwright/test";

test("homepage has correct title", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveTitle("DailyRiff");
});

test.skip("superadmin dashboard page loads (auth-gated, needs API)", async ({ page }) => {
  await page.goto("/dashboard");
  await expect(page.locator("h1")).toContainText("Dashboard");
});

test.skip("superadmin studios page loads (auth-gated, needs API)", async ({ page }) => {
  await page.goto("/studios");
  await expect(page.locator("h1")).toContainText("Studios");
});

test.skip("superadmin sidebar navigation is visible (auth-gated, needs API)", async ({ page }) => {
  await page.goto("/dashboard");
  const nav = page.locator('nav[aria-label="Superadmin navigation"]');
  await expect(nav).toBeVisible();
  await expect(nav.locator("a")).toHaveCount(6);
});
