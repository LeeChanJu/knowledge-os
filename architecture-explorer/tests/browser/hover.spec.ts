import {test,expect} from '@playwright/test';
test('pointer can cross a short gap to the glossary learn link',async({page})=>{
 await page.goto('/#/en/learn/start-here');
 const term=page.locator('.map-user .learn-term');await term.scrollIntoViewIfNeeded();await term.locator('button').first().hover();
 const popup=term.locator('.learn-definition');await expect(popup).toBeVisible();
 const trigger=await term.locator('button').first().boundingBox();const link=await popup.locator('a').boundingBox();
 await page.mouse.move(trigger!.x-3,trigger!.y+trigger!.height+2);await page.waitForTimeout(150);await expect(popup).toBeVisible();
 await page.mouse.move(link!.x+link!.width/2,link!.y+link!.height/2,{steps:12});await page.waitForTimeout(650);await expect(popup).toBeVisible();
 await popup.locator('a').click();await expect(page).toHaveURL(/(?:term=mcp|concept=mcp)/);
});
test('definition dismisses outside its corridor and after learning navigation',async({page})=>{
 await page.goto('/#/en/learn/start-here');const term=page.locator('.map-user .learn-term');await term.locator('button').first().hover();await expect(term.locator('.learn-definition')).toBeVisible();
 await page.mouse.move(1500,1000);await expect(term.locator('.learn-definition')).toHaveCount(0);
 await term.locator('button').first().focus();await expect(term.locator('.learn-definition')).toBeVisible();await page.keyboard.press('Escape');await expect(term.locator('.learn-definition')).toHaveCount(0);
 await page.goto('/#/en/learn/remember');const branch=page.locator('.concept-branches .learn-term').first();await branch.locator('button').first().click();await branch.locator('a').click();await expect(branch.locator('.learn-definition')).toHaveCount(0);await expect(page.locator('.concept-inspector')).toBeVisible();
});
test('an open glossary never covers its own trigger',async({page})=>{
 await page.goto('/#/en/learn/remember');
 const term=page.locator('.concept-branches .learn-term').first(),trigger=term.locator('button').first();
 await trigger.hover();await expect(term.locator('.learn-definition')).toBeVisible();
 await expect.poll(()=>trigger.evaluate(button=>{const r=button.getBoundingClientRect();return button.contains(document.elementFromPoint(r.x+r.width/2,r.y+r.height/2))})).toBe(true);
 await trigger.click();await expect(term.locator('.learn-definition')).toBeVisible();
 await term.locator('.learn-definition a').click();await expect(page.locator('.concept-inspector')).toBeVisible();
});
