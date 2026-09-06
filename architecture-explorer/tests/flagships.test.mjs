import {test} from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync,cpSync,readFileSync,writeFileSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {resolve,join} from 'node:path';
import {checkFlagships,textHash} from '../scripts/check-flagships.mjs';
const root=resolve('..'), architecture=JSON.parse(readFileSync('data/architecture.json'));
const pages=new Set(JSON.parse(readFileSync('content/manifest.json')).pages.map(p=>p.id));
function fixture(fn){const dir=mkdtempSync(join(tmpdir(),'flagships-'));try{cpSync('content',resolve(dir,'architecture-explorer/content'),{recursive:true});fn(dir);}finally{rmSync(dir,{recursive:true,force:true});}}
test('four complete Markdown pairs have checked metadata without prose in generated JSON',()=>{const m=checkFlagships(root,architecture,pages);assert.equal(Object.keys(m.pages).length,4);assert.equal(JSON.stringify(m).includes('A folder organizes files'),false);for(const id of Object.keys(m.pages)){const en=readFileSync(`content/en/${id}.md`,'utf8');assert.ok(en.split(/\s+/).length>800,`${id} is not a glossary card`);}});
test('unreviewed Markdown edits fail non-mutating check',()=>fixture(dir=>{const path=resolve(dir,'architecture-explorer/content/en/start-here.md');writeFileSync(path,readFileSync(path,'utf8')+'\nChanged.');const before=readFileSync(path,'utf8');assert.throws(()=>checkFlagships(dir,architecture,pages),/review required/);assert.equal(readFileSync(path,'utf8'),before);}));
test('missing counterpart, broken evidence and missing answer fail independently',()=>{for(const kind of ['counterpart','evidence','answer'])fixture(dir=>{const base=resolve(dir,'architecture-explorer/content');const meta=JSON.parse(readFileSync(join(base,'flagships.json')));if(kind==='counterpart')rmSync(join(base,'ko-KR/start-here.md'));if(kind==='evidence')meta.pages['start-here'].referenceIds.push('ref:missing.py');if(kind==='answer'){const path=join(base,'en/start-here.md');const text=readFileSync(path,'utf8').replace(/\n---\n/,'\n');writeFileSync(path,text);meta.pages['start-here'].hashes.en=textHash(text);}writeFileSync(join(base,'flagships.json'),JSON.stringify(meta));assert.throws(()=>checkFlagships(dir,architecture,pages));});});
