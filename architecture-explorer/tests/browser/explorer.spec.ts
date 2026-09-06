import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";
const model = JSON.parse(readFileSync("data/architecture.json", "utf8"));
const overviewCount = model.nodes.filter(
  (n: { overview: boolean }) => n.overview,
).length;

test("every visible control works; architecture remains a static local document", async ({
  page,
}) => {
  const errors: string[] = [];
  const external: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("request", (r) => {
    if (
      !r.url().startsWith(`http://127.0.0.1:${process.env.EXPLORER_PORT || "5173"}/`) &&
      !r.url().startsWith("data:")
    )
      external.push(r.url());
  });
  await page.goto("/#/en/explore");
  await expect(
    page.getByRole("heading", { name: "A map of the system." }),
  ).toBeVisible();
  await expect(page.locator(".node-list button")).toHaveCount(overviewCount);
  await expect(page.locator(".graph-canvas canvas").first()).toBeVisible();
  await expect(
    page.getByText("CHECKED SNAPSHOT", { exact: false }),
  ).toBeVisible();
  await page.screenshot({
    path: "test-results/overview-dark.png",
    fullPage: true,
  });
  // Canvas selection: calculate the preset position of Source Registry from the fit bounds.
  const canvas = page.getByRole("application");
  const box = (await canvas.boundingBox())!;
  const zoom = Math.min(
    (box.width - 80) / (1040 + 178),
    (box.height - 80) / (825 + 64),
  );
  const x = box.width / 2 + (0 - 520) * zoom,
    y = box.height / 2 + (165 - 412.5) * zoom;
  await canvas.click({ position: { x, y } });
  await expect(
    page.getByRole("heading", { name: "Source Registry", exact: true }),
  ).toBeVisible();
  await expect
    .poll(() => page.locator(".node-list button").count())
    .toBeGreaterThan(overviewCount);
  await expect(
    page.getByRole("heading", { name: "Inputs", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Outputs", exact: true }),
  ).toBeVisible();
  await page.getByRole("tab", { name: /Evidence/ }).click();
  await page
    .getByRole("button", { name: /source_id src\/knowledge_os\/ids.py/ })
    .click();
  await expect(
    page.getByRole("heading", { name: "source_id", exact: true }),
  ).toBeVisible();
  await expect(page.locator(".source-path")).toContainText(
    "src/knowledge_os/ids.py::source_id",
  );
  await page.goBack();
  await expect(
    page.getByRole("heading", { name: "Source Registry", exact: true }),
  ).toBeVisible();
  await page.goForward();
  await expect(
    page.getByRole("heading", { name: "source_id", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Close component details" }).click();
  await expect(page.locator(".node-list button")).toHaveCount(overviewCount);
  // Zoom, fit and pan must alter the actual canvas pixels.
  const before = await canvas.screenshot();
  await page.getByRole("button", { name: "Zoom in", exact: true }).click();
  expect(Buffer.compare(before, await canvas.screenshot())).not.toBe(0);
  await page.getByRole("button", { name: "Zoom out", exact: true }).click();
  await page.getByRole("button", { name: "Fit", exact: true }).click();
  const beforePan = await canvas.screenshot();
  await page.mouse.move(box.x + box.width - 35, box.y + box.height - 70);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width - 135, box.y + box.height - 140, {
    steps: 6,
  });
  await page.mouse.up();
  expect(Buffer.compare(beforePan, await canvas.screenshot())).not.toBe(0);
  await page
    .getByRole("button", { name: "Reset overview", exact: true })
    .click();
  await canvas.click({ position: { x, y } });
  await expect(
    page.getByRole("heading", { name: "Source Registry", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Reset overview", exact: true })
    .click();
  // Hidden node search, clear-search button, and no-result handling.
  const search = page.getByRole("textbox", {
    name: "Find a component or reference",
  });
  await search.fill("Production Embedding Provider");
  await page
    .getByRole("button", { name: /Production Embedding Provider deferred/ })
    .click();
  await expect(
    page.getByRole("heading", {
      name: "Production Embedding Provider",
      exact: true,
    }),
  ).toBeVisible();
  await search.fill("does-not-exist");
  await expect(
    page.getByText("No matches within these filters."),
  ).toBeVisible();
  await page.getByRole("button", { name: "Clear search", exact: true }).click();
  // Domain and status filters do not bypass one-hop disclosure.
  await page.getByLabel("Architectural domain").selectOption("retrieval");
  await expect(page.locator(".node-list")).toContainText(
    "Production Embedding Provider",
  );
  for (const status of ["VERIFIED", "IMPLEMENTED", "KNOWN ISSUE", "DEFERRED"])
    await page.getByRole("checkbox", { name: status, exact: true }).uncheck();
  await expect(
    page.getByRole("heading", { name: "No nodes match these filters" }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Show all states and domains" })
    .click();
  await expect(
    page.getByRole("heading", { name: "No nodes match these filters" }),
  ).not.toBeVisible();
  await page
    .getByRole("complementary", { name: "Explore and filter" })
    .getByRole("button", { name: "Clear filters", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Reset overview", exact: true })
    .click();
  // Explicit verification provenance and unresolved findings.
  await page.getByRole("button", { name: "F1 ✓", exact: true }).click();
  await expect(
    page.getByRole("heading", {
      name: "F1 · Immutable metadata hash integrity",
      exact: true,
    }),
  ).toBeVisible();
  await expect(page.getByText(/Executed at current HEAD: 9 passed/)).toBeVisible();
  await page.getByRole("tab", { name: /Evidence/ }).click();
  await expect(
    page.getByRole("heading", { name: "Pinned verification dependencies" }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Reset overview", exact: true })
    .click();
  await page.getByRole("button", { name: "F3 ↗", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Required resolution" }),
  ).toBeVisible();
  await page.screenshot({
    path: "test-results/finding-dark.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Change theme" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await page
    .getByRole("button", { name: "Reset overview", exact: true })
    .click();
  await canvas.click({ position: { x, y } });
  await expect(
    page.getByRole("heading", { name: "Source Registry", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Reset overview", exact: true })
    .click();
  await page.screenshot({
    path: "test-results/overview-light.png",
    fullPage: true,
  });
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await page.getByRole("button", { name: "Change theme" }).click();
  expect(errors).toEqual([]);
  expect(external).toEqual([]);
});

test("unknown hashes, direct links, and narrow layouts remain usable", async ({
  page,
}) => {
  await page.goto("/#/node/not-real");
  await expect(
    page.getByRole("heading", { name: "Unknown documentation node" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Return to overview" }).click();
  await page.goto("/#/node/contract-evidence");
  await expect(
    page.getByRole("heading", { name: "Evidence Contract", exact: true }),
  ).toBeVisible();
  await page.setViewportSize({ width: 760, height: 1000 });
  await expect(
    page.getByRole("button", { name: "Reset overview", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Evidence Contract", exact: true }),
  ).toBeVisible();
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth > innerWidth,
  );
  expect(overflow).toBe(false);
});
