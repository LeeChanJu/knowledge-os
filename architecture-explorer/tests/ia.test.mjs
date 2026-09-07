import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,mkdtempSync,cpSync,rmSync,writeFileSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {checkIA} from '../scripts/check-ia.mjs';
const architecture=JSON.parse(readFileSync('data/architecture.json'));
test('all 77 original pages are preserved under one map and six 26-stage journeys',()=>assert.deepEqual(checkIA('..',architecture),{pages:77,journeys:6,stages:26}));
function rejects(path,fn,error){const root=mkdtempSync(join(tmpdir(),'learn-ia-'));try{cpSync('content',join(root,'architecture-explorer/content'),{recursive:true});const p=join(root,'architecture-explorer/content',path),v=JSON.parse(readFileSync(p));fn(v);writeFileSync(p,JSON.stringify(v));assert.throws(()=>checkIA(root,architecture),error)}finally{rmSync(root,{recursive:true,force:true})}}
test('a lost legacy alias is rejected',()=>rejects('ia/catalog.json',v=>v.entries[1].aliases=[],/Missing preserved route/));
test('unknown map stage and broken code reference are rejected',()=>{rejects('ia/journeys.json',v=>v.journeys[0].stages[0].anchor='invented',/Broken journey branch/);rejects('ia/journeys.json',v=>v.journeys[0].stages[0].referenceIds.push('ref:missing'),/Broken journey branch/)});
test('old prose cannot be silently discarded during IA work',()=>rejects('en/ontology.json',v=>v.title='Discarded original',/body preservation/));
test('term introduction mapping and bilingual reviews require reconciliation',()=>{rejects('ia/review.json',v=>v.termIntroductions.remember.entity='store',/Term introduction/);rejects('ia/review.json',v=>v.prose['ko-KR/find']='stale',/prose review/)});

test('capability verification links cannot point at invented findings',()=>rejects('ia/journeys.json',v=>v.journeys[0].issueIds.push('F999'),/Broken verification reference/));
