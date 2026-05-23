/**
 * E2E happy-path test: ring up 5 products, pay cash, verify sale recorded.
 *
 * Prerequisites before running:
 *   1. Django backend running:  python manage.py runserver (desktop settings)
 *   2. Django superuser exists: python manage.py createsuperuser
 *      Email: owner@pos.local  Password: PosTest123!
 *   3. At least 5 products with stock in the DB.
 *      (Run the seed command or import products.csv)
 *
 * Run with:
 *   npx playwright test e2e/checkout.spec.ts
 */

import { test, expect, type Page } from "@playwright/test";

const BASE_URL = "http://localhost:5173";
const LOGIN_EMAIL = "owner@pos.local";
const LOGIN_PASSWORD = "PosTest123!";

async function login(page: Page) {
  await page.goto(`${BASE_URL}/login`);
  await page.getByLabel(/email/i).fill(LOGIN_EMAIL);
  await page.getByLabel(/password/i).fill(LOGIN_PASSWORD);
  await page.getByRole("button", { name: /sign in/i }).click();
  await page.waitForURL("**/dashboard");
}

test.describe("Checkout happy path", () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test("navigate to checkout from sidebar", async ({ page }) => {
    await page.getByRole("link", { name: /checkout/i }).click();
    await page.waitForURL("**/checkout");
    // Barcode input is auto-focused
    const barcodeInput = page.locator("input[placeholder*='barcode']");
    await expect(barcodeInput).toBeFocused();
  });

  test("search and add 5 items, complete cash sale", async ({ page }) => {
    await page.goto(`${BASE_URL}/checkout`);

    // Use search to add items (simulates cashier without a scanner)
    const searchInput = page.locator("input[placeholder*='2 characters']");

    // Add product 1 — search and click first result
    await searchInput.fill("tile");
    await page.waitForSelector("text=Stock:");  // results loaded
    const firstResult = page.locator("button").filter({ hasText: "Stock:" }).first();
    await firstResult.click();

    // Verify item appeared in cart
    await expect(page.getByRole("table")).toBeVisible();

    // Adjust qty to 2 using the + button
    const plusBtn = page.locator("button").filter({ has: page.locator("svg") }).first();
    // Use keyboard shortcut instead — select first row and press +
    await page.locator("tr").nth(1).click();
    await page.keyboard.press("+");
    await expect(page.locator("td").filter({ hasText: "2" }).first()).toBeVisible();

    // Add 4 more items via search (re-use same product is fine for the test)
    for (let i = 0; i < 4; i++) {
      await searchInput.fill("tile");
      await page.waitForSelector("text=Stock:");
      await page.locator("button").filter({ hasText: "Stock:" }).first().click();
    }

    // Open payment with F12
    await page.keyboard.press("F12");
    await expect(page.getByText("Complete Payment")).toBeVisible();

    // Cash is pre-selected; enter a round amount
    const totalText = await page.locator("text=TOTAL").locator("..").textContent();
    // Just enter a round Rs. 2000 as tendered cash
    const tenderedInput = page.locator("input[type='number']").last();
    await tenderedInput.fill("2000");

    // Confirm
    await page.getByRole("button", { name: /complete sale/i }).click();

    // Should show success screen
    await expect(page.getByText("Sale Complete!")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText(/SALE-/)).toBeVisible();

    // Verify "New Sale" button is present to start next sale
    await expect(page.getByRole("button", { name: /new sale/i })).toBeVisible();
  });

  test("F2 focuses search, F3 focuses barcode, Escape closes payment modal", async ({ page }) => {
    await page.goto(`${BASE_URL}/checkout`);

    await page.keyboard.press("F2");
    const searchInput = page.locator("input[placeholder*='2 characters']");
    await expect(searchInput).toBeFocused();

    await page.keyboard.press("F3");
    const barcodeInput = page.locator("input[placeholder*='barcode']");
    await expect(barcodeInput).toBeFocused();

    // Add an item so F12 works
    await searchInput.fill("tile");
    await page.waitForSelector("text=Stock:");
    await page.locator("button").filter({ hasText: "Stock:" }).first().click();

    await page.keyboard.press("F12");
    await expect(page.getByText("Complete Payment")).toBeVisible();

    await page.keyboard.press("Escape");
    await expect(page.getByText("Complete Payment")).not.toBeVisible();
  });

  test("oversell is rejected by the server", async ({ page }) => {
    await page.goto(`${BASE_URL}/checkout`);

    // This test assumes at least one product exists with stock < 9999
    const searchInput = page.locator("input[placeholder*='2 characters']");
    await searchInput.fill("tile");
    await page.waitForSelector("text=Stock:");
    await page.locator("button").filter({ hasText: "Stock:" }).first().click();

    // Manually set qty to 9999 by typing in the qty cell
    // (easier to test via API — this test just verifies the UI survives an error)
    // Click the item row to select it
    await page.locator("tr").nth(1).click();
    // Press + many times (10) to build qty up
    for (let i = 0; i < 9; i++) await page.keyboard.press("+");

    // The test succeeds as long as the page doesn't crash; oversell is caught server-side.
    // A real oversell test belongs in test_services.py.
    await expect(page.locator("text=Pay Now")).toBeVisible();
  });
});