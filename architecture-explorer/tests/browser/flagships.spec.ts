import {test,expect} from '@playwright/test';
import {readFileSync} from 'node:fs';
const catalog=JSON.parse(readFileSync('content/ia/catalog.json','utf8'));
for(const lang of ['ko-KR','en'])test(`preserved flagship deep dives in ${lang}`,async({page})=>{
 for(const id of ['start-here','source-of-truth','document-journey','ontology-basics']){
  const entry=catalog.entries.find((e:any)=>e.id===id);await page.goto(`/#/${lang}/archive/document/${id}`);
  await expect(page.locator('.mental-model')).toBeVisible();
  await expect(page.locator('.outside-source')).toContainText('Google Drive / Notion / Files');
  await expect(page.locator('#technical-layer')).not.toHaveAttribute('open','');
  await page.locator('#technical-layer>summary').click();
  await expect(page.locator('.implementation-evidence')).toBeVisible();
  await expect(page.locator('.implementation-evidence .file-action').first()).toHaveAttribute('href',/github.com\/LeeChanJu\/knowledge-os\/blob\/[a-f0-9]{40}\//);
  await page.locator('.implementation-evidence .evidence-card').first().click();await expect(page).toHaveURL(/reference\/item/);
  await page.goBack();await expect(page.locator('.mental-model')).toBeVisible();
 }
});
