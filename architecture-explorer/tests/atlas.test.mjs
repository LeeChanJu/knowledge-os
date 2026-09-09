import {test} from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync,cpSync,readFileSync,writeFileSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {checkAtlas} from '../scripts/check-atlas.mjs';
const architecture=JSON.parse(readFileSync('data/architecture.json'));
test('M2 includes both full backbones and all 77 classifications',()=>assert.deepEqual(checkAtlas('..',architecture),{nodes:28,runtime:8,engineering:10,legacy:77}));
function rejects(fn,error){const root=mkdtempSync(join(tmpdir(),'atlas-check-'));try{cpSync('content',join(root,'architecture-explorer/content'),{recursive:true});const file=join(root,'architecture-explorer/content/atlas/model.json'),m=JSON.parse(readFileSync(file));fn(m);writeFileSync(file,JSON.stringify(m));assert.throws(()=>checkAtlas(root,architecture),error)}finally{rmSync(root,{recursive:true,force:true})}}
test('cannot omit a major engineering stage',()=>rejects(m=>m.backbones.engineering.pop(),/Complete Atlas backbones/));
test('cross-roadmap targets must be reachable',()=>rejects(m=>m.nodes.find(n=>n.id==='version').opposite.node='question',/cross-roadmap/));
test('renamed symbols and tests fail references',()=>rejects(m=>m.nodes.find(n=>n.id==='version-code').referenceIds=['ref:src/knowledge_os/graph.py::renamed'],/Broken Atlas reference/));
test('branch cycles fail before rendering',()=>rejects(m=>m.nodes.find(n=>n.id==='version').branches.push('support'),/cycle/));
test('prose and labels need explicit bilingual reconciliation',()=>rejects(m=>m.nodes[0].labels.en='Altered label',/review required/));
test('Atlas cannot supply its own VERIFIED status',()=>rejects(m=>m.nodes[0].status='VERIFIED',/schema/));
test('directional backbone links are mandatory',()=>rejects(m=>m.edges.shift(),/directed backbone/));
