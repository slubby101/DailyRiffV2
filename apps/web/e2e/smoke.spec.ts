import { test, expect } from "@playwright/test";

test("homepage has correct title", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveTitle("DailyRiff");
});

test("homepage has hero heading", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("h1")).toContainText("Practice made personal");
});

test("homepage has waitlist form", async ({ page }) => {
  await page.goto("/");
  const form = page.locator('form[aria-label="Join the waitlist"]');
  await expect(form).toBeVisible();
  await expect(form.locator('input[type="email"]')).toBeVisible();
  await expect(form.locator('button[type="submit"]')).toBeVisible();
});

test("homepage has main navigation", async ({ page }) => {
  await page.goto("/");
  const nav = page.locator('nav[aria-label="Main navigation"]');
  await expect(nav).toBeVisible();
  await expect(nav.locator("a")).toHaveCount(2);
});

test("homepage has skip-to-main-content link", async ({ page }) => {
  await page.goto("/");
  const skip = page.locator('a[href="#main-content"]');
  await expect(skip).toBeAttached();
});

test("about page loads", async ({ page }) => {
  await page.goto("/about");
  await expect(page).toHaveTitle("About | DailyRiff");
  await expect(page.locator("h1")).toContainText("About DailyRiff");
});

test("contact page loads", async ({ page }) => {
  await page.goto("/contact");
  await expect(page).toHaveTitle("Contact | DailyRiff");
  await expect(page.locator("h1")).toContainText("Contact us");
  await expect(page.locator('a[href="mailto:privacy@dailyriff.com"]').first()).toBeVisible();
});

test("privacy policy page loads with draft banner", async ({ page }) => {
  await page.goto("/legal/privacy-policy");
  await expect(page).toHaveTitle("Privacy Policy | DailyRiff");
  await expect(page.locator("h1")).toContainText("Privacy Policy");
  await expect(page.locator('[role="alert"]').first()).toContainText("DRAFT");
  await expect(page.locator('a[href="mailto:privacy@dailyriff.com"]').first()).toBeVisible();
});

test("terms of service page loads with draft banner", async ({ page }) => {
  await page.goto("/legal/terms-of-service");
  await expect(page).toHaveTitle("Terms of Service | DailyRiff");
  await expect(page.locator("h1")).toContainText("Terms of Service");
  await expect(page.locator('[role="alert"]').first()).toContainText("DRAFT");
});

test("accessibility page loads with draft banner", async ({ page }) => {
  await page.goto("/legal/accessibility");
  await expect(page).toHaveTitle("Accessibility | DailyRiff");
  await expect(page.locator("h1")).toContainText("Accessibility Statement");
  await expect(page.locator('[role="alert"]').first()).toContainText("DRAFT");
});

test("footer navigation has legal links", async ({ page }) => {
  await page.goto("/");
  const footer = page.locator('nav[aria-label="Footer navigation"]');
  await expect(footer).toBeVisible();
  await expect(footer.locator('a[href="/legal/privacy-policy"]')).toBeVisible();
  await expect(footer.locator('a[href="/legal/terms-of-service"]')).toBeVisible();
  await expect(footer.locator('a[href="/legal/accessibility"]')).toBeVisible();
});

test("footer has privacy email", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator('footer a[href="mailto:privacy@dailyriff.com"]')).toBeVisible();
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
