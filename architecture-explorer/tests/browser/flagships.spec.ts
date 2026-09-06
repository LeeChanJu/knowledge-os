import {test,expect} from '@playwright/test';
const ids=['start-here','source-of-truth','document-journey','ontology-basics'];
for(const lang of ['ko-KR','en'])test(`complete flagship reading experience: ${lang}`,async({page})=>{
 const errors:string[]=[], requests:string[]=[];
 page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(!r.url().startsWith(`http://127.0.0.1:${process.env.EXPLORER_PORT||'5173'}/`)&&!r.url().startsWith('data:'))requests.push(r.url())});
 for(const id of ids){
  await page.goto(`/#/${lang}/learn/${id}`);await expect(page.locator('.flagship')).toBeVisible();
  await expect(page.locator('html')).toHaveAttribute('lang',lang);
  await expect(page.locator('#objectives')).toBeVisible();
  await expect(page.locator('.lesson-diagram')).not.toHaveCount(0);
  await expect(page.locator('.flagship')).toContainText('CURRENT v0.1');
  await expect(page.locator('.flagship')).toContainText('TARGET / DEFERRED');
  const questions=page.locator('.comprehension');expect(await questions.count()).toBeGreaterThanOrEqual(2);
  for(const q of await questions.all()){await q.locator('summary').click();await expect(q.locator('details')).toHaveAttribute('open','');await expect(q.locator('details p')).toBeVisible();await q.locator('summary').click();}
  await page.locator('.article-toc button').last().click();await expect(page.locator('#implementation-evidence')).toBeInViewport();
  await expect(page.locator('.conceptual-references a').first()).toHaveAttribute('href',/^https:\/\/(www.palantir.com|architecture.learning.sap.com|neo4j.com)/);
  await expect(page.locator('.implementation-evidence .file-action').first()).toHaveAttribute('href',/github.com\/LeeChanJu\/knowledge-os\/blob\/[a-f0-9]{40}\//);
  await page.locator('.implementation-evidence .evidence-card').first().click();await expect(page).toHaveURL(/reference\/item/);await page.goBack();await expect(page.locator('.flagship')).toBeVisible();await page.goForward();await expect(page).toHaveURL(/reference\/item/);await page.goBack();
  await page.locator('.toc-explore').click();await expect(page).toHaveURL(/explore\/node/);await page.getByRole('link',{name:lang==='en'?/Read the explanation/:/설명 읽기/}).click();await expect(page).toHaveURL(new RegExp('learn/'+id+'$'));
  await page.getByRole('button',{name:lang==='en'?'한국어':'English',exact:true}).click();await expect(page.locator('.flagship')).toBeVisible();await page.getByRole('button',{name:lang==='en'?'English':'한국어',exact:true}).click();
  await page.evaluate(()=>window.scrollTo(0,0));await page.screenshot({path:`test-results/${lang}-${id}-dark.png`,fullPage:true});
  await page.getByRole('button',{name:lang==='en'?'Change theme':'테마 바꾸기'}).click();await page.screenshot({path:`test-results/${lang}-${id}-light.png`,fullPage:true});
  await page.getByRole('button',{name:lang==='en'?'Change theme':'테마 바꾸기'}).click();
 }
 await page.setViewportSize({width:390,height:844});await page.goto(`/#/${lang}/learn/ontology-basics`);expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1)).toBe(true);await page.screenshot({path:`test-results/${lang}-mobile.png`,fullPage:true});
 expect(errors).toEqual([]);expect(requests).toEqual([]);
});
