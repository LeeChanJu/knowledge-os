import {test,expect} from '@playwright/test';
import {readFileSync} from 'node:fs';
const journeys=JSON.parse(readFileSync('content/ia/journeys.json','utf8')).journeys;
for(const lang of ['ko-KR','en'])test(`six complete journeys, concepts and return paths in ${lang}`,async({page})=>{
 test.setTimeout(120000);
 const errors:string[]=[],external:string[]=[];
 page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(!r.url().startsWith(`http://127.0.0.1:${process.env.EXPLORER_PORT||'5173'}/`)&&!r.url().startsWith('data:'))external.push(r.url())});
 await page.goto(`/#/${lang}/learn/start-here`);
 await expect(page.locator('.ia-nav a')).toHaveCount(7);await expect(page.locator('.journey-card-grid a')).toHaveCount(6);
 await expect(page.locator('.outside-source')).toContainText(lang==='en'?'originals stay here':'원본은 여기 남습니다');
 await page.locator('.journey-search input').fill('zz-no-journey');await expect(page.locator('.journey-choices [role=status]')).toBeVisible();await page.locator('.journey-search input').fill('');
 await page.screenshot({path:`test-results/ia-${lang}-home.png`,fullPage:true});
 for(const j of journeys){
  await page.goto(`/#/${lang}/learn/${j.id}`);await expect(page.locator('h1')).toHaveText(j.title[lang]);
  for(const s of j.stages){
   await page.locator('.journey-path a').filter({hasText:s.title[lang]}).click();
   await expect(page.locator('.journey-path [aria-current=step]')).toContainText(s.title[lang]);
   await expect(page.locator('.journey-stage h2')).toHaveCount(1);await expect(page.locator('.journey-stage figure')).toHaveCount(1);
   const term=page.locator('.concept-branches .learn-term').first();await term.locator('button').first().click();await expect(term.locator('.learn-definition')).toBeVisible();await term.locator('.learn-definition a').click();
   await expect(page.locator('.concept-inspector')).toBeVisible();await expect(page).toHaveURL(new RegExp(`concept=${s.terms[0]}`));
   await page.locator('.concept-inspector>a').last().click();await expect(page).toHaveURL(/reference\//);await expect(page.locator('.ia-context')).toContainText(s.title[lang]);
   await page.locator('.ia-context a').last().click();await expect(page.locator('.concept-inspector')).toBeVisible();
   await page.locator('.concept-close').click();await expect(page.locator('.concept-inspector')).toHaveCount(0);
  }
  await page.locator('.capability-boundaries>summary').click();await expect(page.locator('.capability-boundaries section')).toHaveCount(4);
  await page.locator('.journey-checks>summary').click();await expect(page.locator('.flow-check')).toHaveCount(2);await page.locator('.flow-check summary').first().click();await expect(page.locator('.flow-check details p').first()).toBeVisible();
  await page.screenshot({path:`test-results/ia-${lang}-${j.id}.png`,fullPage:true});
 }
 await page.goto(`/#/${lang}/learn/find?step=meaning`);await page.getByRole('button',{name:lang==='en'?'한국어':'English',exact:true}).click();await expect(page).toHaveURL(/learn\/find\?step=meaning/);await expect(page.locator('.journey-stage')).toBeVisible();
 await page.setViewportSize({width:390,height:844});await page.goto(`/#/${lang}/learn/start-here`);
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);await expect(page.locator('.outside-source')).toBeInViewport({ratio:1});await expect(page.locator('.map-user')).toBeInViewport({ratio:1});
 await page.screenshot({path:`test-results/ia-${lang}-mobile.png`});await page.locator('.map-user .learn-term>button').click();await expect(page.locator('.map-user .learn-definition')).toBeVisible();await page.keyboard.press('Escape');await expect(page.locator('.map-user .learn-definition')).toHaveCount(0);
 expect(errors).toEqual([]);expect(external).toEqual([]);
});
test('context survives evidence, graph selection, back/forward and reference filters',async({page})=>{
 await page.goto('/#/en/learn/remember?step=propose');await page.locator('.stage-deep-dives>summary').click();await page.locator('.journey-evidence').first().click();await expect(page.locator('.ia-context')).toContainText('Submit');
 await page.goBack();await expect(page).toHaveURL(/step=propose/);await page.goForward();await expect(page).toHaveURL(/reference\/item/);await page.locator('.ia-context a').last().click();
 await page.locator('.stage-deep-dives>summary').click();await page.locator('.stage-deep-dives>a').last().click();await expect(page).toHaveURL(/explore\/node\/proposal\?journey=remember&step=propose/);await expect(page.locator('.ia-context')).toBeVisible();
 await page.locator('.node-list button').first().click();await expect(page).toHaveURL(/journey=remember&step=propose/);await page.locator('.ia-context a').last().click();await expect(page.locator('.journey-stage')).toBeVisible();
 await page.goto('/#/en/reference');await page.getByLabel('Find a concept',{exact:true}).fill('ontology');await expect(page.locator('.reference-library details a')).not.toHaveCount(0);await page.getByLabel('Document role').selectOption('DEEP DIVE');await expect(page.locator('.reference-library details a')).toHaveCount(2);await page.getByLabel('Find a concept',{exact:true}).fill('zz-nothing');await expect(page.locator('.reference-library [role=status]')).toBeVisible();
});
test('map branches, optional primer and contextual map return work',async({page})=>{
 await page.goto('/#/en/learn/start-here');await page.locator('.ia-primer>summary').click();await expect(page.locator('.ia-primer')).not.toContainText('<!--');
 await page.getByRole('link',{name:'Connected knowledge Implemented boundary',exact:true}).click();await expect(page).toHaveURL(/remember\?step=store$/);
 await page.locator('.journey-whole>summary').click();await expect(page.locator('.outside-source')).toBeVisible();await page.getByRole('link',{name:/Google Drive \/ Notion \/ Files Outside/}).click();await expect(page).toHaveURL(/sources\?step=original$/);
 await page.locator('.journey-step-nav a').last().click();await expect(page).toHaveURL(/start-here\?journey=sources&step=original/);await expect(page.locator('.outside-source')).toBeVisible();
});
