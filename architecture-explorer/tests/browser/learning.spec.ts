import {test,expect} from '@playwright/test';
test('guide evidence preserves exact map origin, language, and browser history',async({page})=>{
 const origin='runtime?node=version&root=support&open=support%2Cversion';
 await page.goto('/#/en/reference/guide/document-version?atlas='+encodeURIComponent(origin));
 await expect(page.locator('.guide-location ol a').first()).toHaveText('My question');await expect(page.locator('.guide-trail')).toContainText('document');
 await page.locator('.guide-evidence summary').click();await page.locator('.guide-evidence a').first().click();
 await expect(page.locator('.source-path')).toBeVisible();await expect(page).toHaveURL(/atlas=/);
 await expect(page.getByRole('link',{name:/Evidence revision on GitHub/})).toHaveAttribute('href',/github.com\/LeeChanJu\/knowledge-os\/blob\//);
 await page.goBack();await expect(page.locator('.integrated-guide')).toBeVisible();
 await page.getByRole('button',{name:'한국어',exact:true}).click();await expect(page).toHaveURL(/ko-KR\/reference\/guide\/document-version\?atlas=/);
 await page.getByRole('button',{name:'테마 바꾸기'}).click();await page.reload();await expect(page.locator('html')).toHaveAttribute('data-theme','light');
});
test('guide terms, disclosure, mobile layout, empty and invalid routes',async({page})=>{
 await page.goto('/#/en/reference/guide/assertion');await page.locator('.integrated-guide .learn-term>button').click();await expect(page.locator('.learn-definition')).toBeVisible();await page.keyboard.press('Escape');await expect(page.locator('.learn-definition')).toHaveCount(0);
 await page.locator('.guide-section summary').first().click();await expect(page.locator('.guide-section').first()).toHaveAttribute('open','');await page.locator('.guide-section summary').first().click();await expect(page.locator('.guide-section').first()).not.toHaveAttribute('open','');
 await page.setViewportSize({width:390,height:844});await page.goto('/#/ko-KR/reference/guide/source-of-truth');
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);await page.screenshot({path:'test-results/guide-mobile.png',fullPage:true});
 await page.goto('/#/en/reference/guide/not-real');await expect(page.getByRole('heading',{name:'Guide not found'})).toBeVisible();
});
