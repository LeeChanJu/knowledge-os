import {test} from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync,cpSync,readFileSync,writeFileSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {checkIntegration} from '../scripts/check-integration.mjs';
const architecture=JSON.parse(readFileSync('data/architecture.json'));
test('77 originals integrated with depth for all 116 nodes',()=>assert.deepEqual(checkIntegration('..',architecture),{documents:77,guides:68,merged:7,redirected:2,depthNodes:116}));
function rejects(fn,error){const root=mkdtempSync(join(tmpdir(),'guide-check-'));try{cpSync('content',join(root,'architecture-explorer/content'),{recursive:true});const p=join(root,'architecture-explorer/content/atlas/integration.json'),m=JSON.parse(readFileSync(p));fn(m,join(root,'architecture-explorer'));writeFileSync(p,JSON.stringify(m));assert.throws(()=>checkIntegration(root,architecture),error)}finally{rmSync(root,{recursive:true,force:true})}}
test('duplicate legacy routes rejected',()=>rejects(m=>m.entries[1].aliases.push(m.entries[0].aliases[0]),/Duplicate legacy/));
test('merge cycles rejected',()=>rejects(m=>m.entries[0].canonicalId='missing',/canonical/));
test('missing merged prose member rejected',()=>rejects(m=>m.guides.find(g=>g.members.length>1).members.pop(),/member missing/));
test('renamed evidence rejected',()=>rejects(m=>m.guides[0].referenceIds.push('ref:missing.py'),/Broken guide evidence/));
test('wrong language rejected',()=>rejects(m=>m.guides[0].content.en=m.guides[0].content['ko-KR'],/language mismatch/));
test('unreachable map position rejected',()=>rejects(m=>m.entries[0].location.node='missing',/map location/));
test('source changes require reconciliation',()=>rejects((m,b)=>{const p=join(b,'content/architecture/en.json');writeFileSync(p,readFileSync(p,'utf8')+'\n')},/review required/));

test('guide ownership cannot inherit an unrelated map component',()=>rejects(m=>m.guides[0].architectureNodeIds=['contract-source'],/component ownership/));
