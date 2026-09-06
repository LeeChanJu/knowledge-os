import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";
const content = JSON.parse(readFileSync("data/learning.json", "utf8"));
test("learning entry, bilingual reading, implementation links and graph round trip", async ({
  page,
}) => {
  const errors: string[] = [],
    external: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("request", (r) => {
    if (
      !r
        .url()
        .startsWith(
          `http://127.0.0.1:${process.env.EXPLORER_PORT || "5173"}/`,
        ) &&
      !r.url().startsWith("data:")
    )
      external.push(r.url());
  });
  await page.goto("/#/ko-KR");
  await expect(page.locator("html")).toHaveAttribute("lang", "ko-KR");
  await expect(page.locator(".lesson-grid a")).toHaveCount(10);
  await page.getByRole("link", { name: /처음부터 배우기/ }).click();
  await expect(page.locator("h1")).toContainText("01.");
  await page.goto("/#/ko-KR/learn/ontology");
  await expect(page.locator("h1")).toHaveText("온톨로지 (Ontology)");
  await page.getByRole("button", { name: "English", exact: true }).click();
  await expect(page).toHaveURL(/#\/en\/learn\/ontology$/);
  await expect(page.locator("h1")).toHaveText("Ontology");
  await page.getByRole("tab", { name: "3. Implementation" }).click();
  await expect(page.locator("#technical")).toBeVisible();
  await expect(page.locator("#technical")).toContainText("F5");
  await page
    .locator("#implementation .evidence-card")
    .filter({ hasText: "Ontology.validate" })
    .click();
  await expect(page.locator(".source-path")).toContainText(
    "src/knowledge_os/ontology.py::Ontology.validate",
  );
  const github = page.getByRole("link", {
    name: /Evidence revision on GitHub/,
  });
  await expect(github).toHaveAttribute(
    "href",
    /github\.com\/LeeChanJu\/knowledge-os\/blob\/[a-f0-9]{40}\/src\/knowledge_os\/ontology.py$/,
  );
  await expect(
    page.getByRole("link", { name: /Current repository on GitHub/ }),
  ).toHaveAttribute("href", /\/blob\/main\//);
  await page.goBack();
  await expect(page.locator("h1")).toHaveText("Ontology");
  await page.goForward();
  await expect(page.locator(".source-path")).toContainText("Ontology.validate");
  await page.goto("/#/en/learn/ontology");
  await page.locator(".toc-explore").click();
  await expect(page).toHaveURL(/explore\/node\/ontology$/);
  await expect(
    page.getByRole("heading", { name: "Ontology", exact: true }),
  ).toBeVisible();
  await expect(page.locator(".node-list button")).toHaveCount(36);
  await page.getByRole("link", { name: /Read the explanation/ }).click();
  await expect(page).toHaveURL(/learn\/ontology$/);
  await page.getByRole("button", { name: "한국어", exact: true }).click();
  await page.getByRole("button", { name: "테마 바꾸기" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await page.screenshot({
    path: "test-results/learning-light.png",
    fullPage: true,
  });
  expect(errors).toEqual([]);
  expect(external).toEqual([]);
});
test("all paired pages and walkthroughs render; search, empty states and invalid routes work", async ({
  page,
}) => {
  for (const lang of ["en", "ko-KR"])
    for (const entry of content.manifest.pages) {
      await page.goto(`/#/${lang}/learn/${entry.id}`);
      await expect(page.locator("h1")).toHaveText(
        content.documents[lang][entry.id].title,
      );
      await expect(page.locator(".teaching-flow li")).toHaveCount(
        content.documents[lang][entry.id].steps.length,
      );
    }
  await page.goto("/#/en/learn/start-here");
  await page
    .getByLabel("Search documentation", { exact: true })
    .fill("ontology");
  await expect(page.locator(".docs-sidebar nav a").first()).toBeVisible();
  await page
    .getByLabel("Search documentation", { exact: true })
    .fill("zz-no-document-zz");
  await expect(page.getByText("No documents match.")).toBeVisible();
  await page.goto("/#/en/reference");
  await page.getByLabel("Reference type").selectOption("test");
  await expect(page.locator(".evidence-card")).not.toHaveCount(0);
  await page
    .getByRole("textbox", { name: "Search results" })
    .fill("zz-no-test-zz");
  await expect(page.getByText("No documents match.")).toBeVisible();
  await page.goto("/#/en/learn/not-real");
  await expect(
    page.getByRole("heading", { name: "Page not found" }),
  ).toBeVisible();
  await page.goto("/#/ko-KR/reference/item/not-real");
  await expect(
    page.getByRole("heading", { name: "페이지를 찾을 수 없습니다" }),
  ).toBeVisible();
});
test("term definitions, keyboard dismissal and mobile learning navigation", async ({
  page,
}) => {
  await page.goto("/#/en/learn/assertion");
  await page
    .getByRole("button", { name: /Explain this:/ })
    .first()
    .click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/#/ko-KR");
  await expect(
    page.getByRole("link", { name: /처음부터 배우기/ }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: "test-results/learning-mobile.png",
    fullPage: true,
  });
});

test('closing implementation and reopening from the depth control keeps state consistent', async ({page})=>{
 await page.goto('/#/en/learn/ontology');
 await page.getByRole('tab',{name:'3. Implementation'}).click();
 await expect(page.locator('.docs-article details')).toHaveAttribute('open','');
 await page.locator('.docs-article summary').click();
 await expect(page.locator('.docs-article details')).not.toHaveAttribute('open','');
 await page.getByRole('tab',{name:'3. Implementation'}).click();
 await expect(page.locator('.docs-article details')).toHaveAttribute('open','');
});
