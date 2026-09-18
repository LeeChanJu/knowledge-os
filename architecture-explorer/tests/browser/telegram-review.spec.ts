import { test, expect } from '@playwright/test';

for (const lang of ['ko-KR', 'en']) {
  test(`Telegram review instructions and runtime boundary in ${lang}`, async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(`/#/${lang}/reference/guide/approval`);
    const section = page.locator('summary').filter({
      hasText: lang === 'ko-KR' ? '텔레그램에서 검토하고 승인하기' : 'Review and approve in Telegram',
    });
    await expect(section).toBeVisible();
    await section.click();
    await expect(page.locator('.integrated-guide')).toContainText('?start=');
    await expect(page.getByRole('link', {
      name: lang === 'ko-KR' ? '설정과 동작 범위' : 'Setup and operating boundaries',
    })).toBeVisible();
    const pipelineSection = page.locator('summary').filter({
      hasText: lang === 'ko-KR' ? 'Notion에 쓰면 승인 요청까지 어떻게 이어지나요?' : 'How does a Notion edit reach the review inbox?',
    });
    await expect(pipelineSection).toBeVisible();
    await pipelineSection.click();
    await expect(page.locator('.integrated-guide')).toContainText(lang === 'ko-KR' ? '15분마다' : 'every 15 minutes');
    await page.screenshot({ path: `test-results/telegram-review-${lang}.png`, fullPage: true });
    await page.setViewportSize({ width: 390, height: 844 });
    await page.screenshot({ path: `test-results/telegram-review-${lang}-mobile.png`, fullPage: true });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
    await page.goto(`/#/${lang}/runtime?journey=remember&node=remember-review&root=remember-review`);
    await expect(page.locator('.atlas-drawer')).toContainText(lang === 'ko-KR' ? '텔레그램' : 'Telegram');
    expect(errors).toEqual([]);
  });
}
