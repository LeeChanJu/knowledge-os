import {test,expect} from '@playwright/test';
for(const lang of ['ko-KR','en'])test(`M2 roadmap round trip in ${lang}`,async({page})=>{
 const ko=lang==='ko-KR',names=ko?['답변에 쓸 근거 반환','답변의 근거 확인','당시 문서 상태','왜 문서 버전을 보존할까?']:['Return supporting material','Check the answer’s evidence','The document as it was','Why preserve document versions?'];
 const errors:string[]=[],external:string[]=[];page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(!r.url().startsWith(`http://127.0.0.1:${process.env.EXPLORER_PORT||5173}/`)&&!r.url().startsWith('data:'))external.push(r.url())});
 await page.goto(`/#/${lang}/runtime`);await expect(page.locator('.atlas-backbone>li')).toHaveCount(8);await expect(page.locator('.atlas-drawer')).toHaveCount(0);await expect(page.locator('.atlas-outside')).toContainText('Notion');
 const baseline=await page.locator('.atlas-backbone').boundingBox();
 for(const name of names)await page.locator('.atlas-map .atlas-stop').filter({hasText:name}).click();
 await expect(page.locator('.atlas-drawer h2')).toHaveText(names[3]);await expect(page.locator('.atlas-backbone')).toHaveCSS('width','238px');expect((await page.locator('.atlas-backbone').boundingBox())!.y).toBe(baseline!.y);
 await page.screenshot({path:`test-results/atlas-${lang}-runtime.png`,fullPage:true});
 await page.locator('.atlas-cross').click();await expect(page).toHaveURL(/engineering/);await expect(page.locator('.atlas-backbone>li')).toHaveCount(10);
 const stages=ko?['그 규칙을 저장 코드에 적용','다른 주소가 섞이면 잡아내기','어디까지 실제로 확인했나?']:['Enforce the rule in storage','Detect mismatched metadata','What was actually verified?'];
 for(const name of stages)await page.locator('.atlas-map .atlas-stop').filter({hasText:name}).click();
 await page.locator('.atlas-drawer summary').filter({hasText:ko?'실행·검증 근거':'Executed verification evidence'}).click();await expect(page.locator('.atlas-drawer')).toContainText('VERIFIED');await expect(page.locator('.atlas-drawer')).toContainText(ko?'9개':'9 passed');
 await page.screenshot({path:`test-results/atlas-${lang}-engineering.png`,fullPage:true});
 await page.locator('.atlas-drawer summary').filter({hasText:ko?'구현·테스트·계약 근거':'Implementation, tests and contracts'}).click();
 await page.locator('.atlas-ref>a').first().click();await expect(page).toHaveURL(/reference\/item/);await expect(page.locator('.atlas-return')).toBeVisible();await page.locator('.atlas-return a').click();await expect(page).toHaveURL(/engineering/);
 await page.locator('.atlas-original').click();await expect(page.locator('.atlas-drawer h2')).toHaveText(names[3]);
 await page.goBack();await expect(page).toHaveURL(/engineering/);await page.goForward();await expect(page).toHaveURL(/runtime/);
 await page.locator('.atlas-drawer summary').filter({hasText:ko?'기술적으로 보기':'Technical view'}).click();await page.locator('.atlas-drawer .learn-term>button').click();await expect(page.locator('.learn-definition')).toBeVisible();await page.keyboard.press('Escape');await expect(page.locator('.learn-definition')).toHaveCount(0);
 await page.locator('.atlas-deep').click();await expect(page).toHaveURL(/reference\//);await page.locator('.atlas-return a').click();await expect(page.locator('.atlas-drawer h2')).toHaveText(names[3]);
 await page.getByRole('button',{name:ko?'기준선만 보기':'Collapse to backbone',exact:true}).click();await expect(page.locator('.atlas-branches')).toHaveCount(0);await expect(page.locator('.atlas-backbone>li')).toHaveCount(8);
 await page.getByLabel(ko?'지도에서 찾기':'Search roadmap',{exact:true}).fill('zz-none');await expect(page.locator('.atlas-search')).toContainText(ko?'없습니다':'No stages');await page.getByLabel(ko?'지도에서 찾기':'Search roadmap',{exact:true}).fill(names[2]);await page.locator('.atlas-search button').click();await expect(page.locator('.atlas-drawer h2')).toHaveText(names[2]);
 await page.getByRole('button',{name:ko?'English':'한국어',exact:true}).click();await expect(page).toHaveURL(/node=version/);
 expect(errors).toEqual([]);expect(external).toEqual([]);
});
test('whole backbones, zoom, keyboard, collapse, mobile and entry',async({page})=>{
 await page.goto('/#/en');await expect(page.locator('.atlas-home>div>a')).toHaveCount(2);await page.locator('.atlas-home a').last().click();await expect(page.locator('.atlas-backbone>li')).toHaveCount(10);
 await page.locator('.atlas-viewport').focus();await page.keyboard.press('ArrowDown');await expect(page.locator('.atlas-drawer')).toBeVisible();await page.keyboard.press('Escape');await expect(page.locator('.atlas-drawer')).toHaveCount(0);
 await page.getByRole('button',{name:'Zoom in',exact:true}).click();await expect(page.locator('.atlas-toolbar output')).toHaveText('110%');await page.getByRole('button',{name:'Zoom out',exact:true}).click();await expect(page.locator('.atlas-toolbar output')).toHaveText('100%');await page.getByRole('button',{name:'Fit backbone',exact:true}).click();
 await page.goto('/#/en/runtime?node=version&root=support&open=support,evidence,version');await page.getByRole('button',{name:'Collapse descendants',exact:true}).last().click();await expect(page.locator('.atlas-map')).not.toContainText('Why preserve document versions?');await page.getByRole('button',{name:'Collapse branch',exact:true}).click();await expect(page.locator('.atlas-branches')).toHaveCount(0);
 await page.setViewportSize({width:390,height:844});await page.goto('/#/ko-KR/runtime');await page.locator('.atlas-stop').filter({hasText:'답변에 쓸 근거 반환'}).click();await expect(page.locator('.atlas-drawer')).toBeVisible();expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);await page.screenshot({path:'test-results/atlas-mobile.png',fullPage:true});
 await page.getByRole('button',{name:'테마 바꾸기'}).click();await expect(page.locator('html')).toHaveAttribute('data-theme','light');await page.screenshot({path:'test-results/atlas-light.png',fullPage:true});
});
test('architecture node navigation retains Atlas return and invalid selections stay safe',async({page})=>{
 await page.goto('/#/en/runtime?node=version&root=support&open=support,evidence,version');await page.getByText('Inspect this feature in Architecture',{exact:true}).click();await page.getByRole('link',{name:'Explore implementation relationships → version',exact:true}).click();await expect(page.locator('.atlas-return')).toBeVisible();await page.locator('.node-list button').first().click();await expect(page.locator('.atlas-return')).toBeVisible();await page.locator('.atlas-return a').click();await expect(page.locator('.atlas-drawer h2')).toHaveText('The document as it was');
 await page.goto('/#/en/runtime?node=not-real&root=not-real&open=not-real');await expect(page.locator('.atlas-drawer')).toHaveCount(0);await expect(page.locator('.atlas-backbone>li')).toHaveCount(8);
});
