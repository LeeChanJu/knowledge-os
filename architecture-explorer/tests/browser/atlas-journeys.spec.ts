import {test,expect} from '@playwright/test';
import {readFileSync} from 'node:fs';
const model=JSON.parse(readFileSync(new URL('../../content/atlas/model.json',import.meta.url),'utf8'));
for(const lang of ['ko-KR','en'] as const)test(`six complete journeys and engineering return in ${lang}`,async({page})=>{
 const ko=lang==='ko-KR',errors:string[]=[],external:string[]=[];
 page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(!r.url().startsWith(`http://127.0.0.1:${process.env.EXPLORER_PORT||5173}/`)&&!r.url().startsWith('data:'))external.push(r.url())});
 await page.goto(`/#/${lang}/runtime`);
 for(const journey of model.journeys){
  await page.locator('.atlas-journeys a').filter({hasText:journey.labels[lang]}).click();
  await expect(page.locator('.atlas-backbone>li')).toHaveCount(journey.backbone.length);
  await expect(page.locator('.atlas-drawer')).toHaveCount(0);
  await expect(page.locator('.atlas-capability')).toContainText(journey.boundaries.current[lang]);
  await page.locator('.atlas-capability summary').click();await expect(page.locator('.atlas-capability')).toContainText(journey.boundaries.deferred[lang]);
  await page.locator('.atlas-backbone .atlas-stop').last().click();
  await expect(page.locator('.atlas-checks')).toBeVisible();await expect(page.locator('.atlas-checks details')).toHaveCount(2);await page.locator('.atlas-checks summary').first().click();
 }
 await page.goto(`/#/${lang}/runtime?journey=act&node=act-execute`);
 const original=page.url();await page.locator('.atlas-cross').click();await expect(page).toHaveURL(/engineering/);
 await expect(page.locator('.atlas-position')).toContainText(ko?'허용된 사람이':'Only authorized');
 for(const id of ['executor-code','executor-test','executor-proof']){
  const label=model.nodes.find((n:{id:string})=>n.id===id)!.labels[lang];await page.locator('.atlas-branches .atlas-stop').filter({hasText:label}).click();
 }
 await page.locator('.atlas-drawer summary').filter({hasText:ko?'실행·검증 근거':'Executed verification evidence'}).click();await expect(page.locator('.atlas-drawer')).toContainText('KNOWN ISSUE');
 await page.locator('.atlas-original').click();await expect(page).toHaveURL(original);
 await page.goBack();await expect(page).toHaveURL(/engineering/);await page.goForward();await expect(page).toHaveURL(original);
 await page.getByRole('button',{name:ko?'English':'한국어',exact:true}).click();await expect(page).toHaveURL(/journey=act/);await expect(page).toHaveURL(/node=act-execute/);
 expect(errors).toEqual([]);expect(external).toEqual([]);
 await page.screenshot({path:`test-results/atlas-expanded-${lang}.png`,fullPage:true});
});
test('deep engineering branches keep ancestors and collapse predictably',async({page})=>{
 await page.goto('/#/en/engineering?node=backup-read');
 await expect(page.locator('.atlas-position')).toContainText('Capture a recovery set');
 await expect(page.locator('.atlas-position')).toContainText('Read the restored state');
 await expect(page.locator('.atlas-backbone>li')).toHaveCount(10);
 await page.getByRole('button',{name:'Collapse branch',exact:true}).click();await expect(page.locator('.atlas-branches')).toHaveCount(0);
 await page.getByLabel('Search roadmap',{exact:true}).fill('Explicit release acceptance');await page.locator('.atlas-search button').click();
 await expect(page.locator('.atlas-position')).toContainText('Identify audit failures');
 await page.locator('.atlas-drawer summary').filter({hasText:'Executed verification evidence'}).click();await expect(page.locator('.atlas-drawer')).toContainText('KNOWN ISSUE');
 await page.screenshot({path:'test-results/atlas-release.png',fullPage:true});
});
test('runtime switches clear old branches and invalid journeys safely use read',async({page})=>{
 await page.goto('/#/en/runtime?journey=ingest&node=source-version');await expect(page.locator('.atlas-backbone>li')).toHaveCount(9);
 await page.locator('.atlas-journeys a').filter({hasText:'Correct knowledge'}).click();await expect(page.locator('.atlas-drawer')).toHaveCount(0);await expect(page.locator('.atlas-backbone>li')).toHaveCount(4);
 await page.goBack();await expect(page.locator('.atlas-drawer h2')).toHaveText('Preserve the observed state');
 await page.setViewportSize({width:390,height:844});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
 await page.screenshot({path:'test-results/atlas-ingest-mobile.png',fullPage:true});
 await page.goto('/#/en/runtime?journey=invalid');await expect(page.locator('.atlas-backbone>li')).toHaveCount(8);
});
