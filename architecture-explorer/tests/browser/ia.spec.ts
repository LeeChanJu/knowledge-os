import {test,expect} from '@playwright/test';
import {readFileSync} from 'node:fs';
const integration=JSON.parse(readFileSync('content/atlas/integration.json','utf8'));
const learning=JSON.parse(readFileSync('data/learning.json','utf8'));
for(const lang of ['ko-KR','en'])test(`all 77 documents resolve and 68 bilingual guides render in ${lang}`,async({page})=>{
 test.setTimeout(180000);const errors:string[]=[],external:string[]=[];
 page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(!r.url().startsWith('http://127.0.0.1:')&&!r.url().startsWith('data:'))external.push(r.url())});
 for(const e of integration.entries){
  await page.goto(`/#/${lang}/${e.aliases.find((p:string)=>p.startsWith('reference/'))||e.aliases[0]}`);
  if(e.resolution==='redirected'){await expect(page.locator('.atlas-map')).toBeVisible();continue}
  await expect(page.locator('.integrated-guide h1')).toHaveText(learning.documents[lang][e.canonicalId].title);
  await expect(page.locator('.guide-location [aria-current=step]')).toHaveCount(1);
  await expect(page.locator('.guide-checks details')).toHaveCount(2);
 }
 await page.goto(`/#/${lang}/reference/guide/assertion`);
 await page.locator('.guide-section summary').last().click();await expect(page.locator('.guide-section table')).toBeVisible();
 await page.locator('.guide-checks summary').first().click();await expect(page.locator('.guide-checks details[open]')).toBeVisible();
 await page.screenshot({path:`test-results/integrated-guide-${lang}.png`,fullPage:true});
 expect(errors).toEqual([]);expect(external).toEqual([]);
});
test('canonical library searches merged titles, filters, and preserves archived originals',async({page})=>{
 await page.goto('/#/en/reference');await expect(page.locator('.guide-library-results article')).toHaveCount(68);
 await page.getByLabel('Find a concept',{exact:true}).fill('Graph RAG');await expect(page.locator('.guide-library-results article')).toHaveCount(1);
 await page.getByLabel('Map',{exact:true}).selectOption('engineering');await expect(page.locator('.guide-library [role=status]')).toBeVisible();
 await page.getByLabel('Map',{exact:true}).selectOption('');await page.locator('.guide-library-results a').click();await expect(page).toHaveURL(/reference\/guide\/rag/);
 await page.locator('.guide-archive summary').click();await page.locator('.guide-archive a').last().click();await expect(page).toHaveURL(/archive\/document/);await expect(page.locator('.archive-notice')).toBeVisible();
 await page.goBack();await expect(page.locator('.integrated-guide')).toBeVisible();await page.goForward();await expect(page.locator('.archive-notice')).toBeVisible();
});
test('old Learn links resolve into maps and selected concepts retain their original flow',async({page})=>{
 for(const e of integration.entries){await page.goto('/#/en/learn/'+e.id);await expect(page.locator('.atlas,.atlas-home')).toHaveCount(1)}
 await page.goto('/#/en/learn/relationships?step=statements&concept=assertion');await expect(page).toHaveURL(/reference\/guide\/assertion\?atlas=/);await expect(page.locator('.atlas-return a')).toHaveAttribute('href',/runtime\?node=relation-statements/);
 await page.locator('.atlas-return a').click();await expect(page.locator('.atlas-drawer')).toBeVisible();await expect(page).toHaveURL(/node=relation-statements/);
});
