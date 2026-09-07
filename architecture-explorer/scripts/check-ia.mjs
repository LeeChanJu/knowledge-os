import {readFileSync,readdirSync} from 'node:fs';
import {resolve} from 'node:path';
import {digest,validateTerms} from './check-flow.mjs';
const read=(dir,p)=>readFileSync(resolve(dir,p),'utf8');
export function checkIA(root,architecture){
 const dir=resolve(root,'architecture-explorer/content');
 const catalog=JSON.parse(read(dir,'ia/catalog.json')), journeys=JSON.parse(read(dir,'ia/journeys.json')).journeys,review=JSON.parse(read(dir,'ia/review.json'));
 const manifest=JSON.parse(read(dir,'manifest.json')), glossary=JSON.parse(read(dir,'flow/glossary.json'));
 const anchors=new Set(JSON.parse(read(dir,'flow/model.json')).stages.map(s=>s.id));
 const primary=['start-here','remember','find','relationships','sources','correct','act'];
 if(JSON.stringify(catalog.primaryLearn)!==JSON.stringify(primary)||JSON.stringify(journeys.map(j=>j.id))!==JSON.stringify(primary.slice(1)))throw Error('Learn must have one map and six capabilities');
 const ids=new Set(manifest.pages.map(p=>p.id)),refs=new Set(architecture.nodes.map(n=>n.id)),routes=new Set();
 if(catalog.entries.length!==ids.size||new Set(catalog.entries.map(e=>e.id)).size!==ids.size)throw Error('IA must classify each existing page exactly once');
 for(const e of catalog.entries){
  if(!ids.has(e.id)||!catalog.roles.includes(e.role)||!e.journeys.length||e.journeys.some(j=>!primary.slice(1).includes(j)))throw Error(`Invalid IA classification ${e.id}`);
  if(e.id!=='start-here'&&(!e.path.startsWith('reference/')||!e.aliases.includes(`learn/${e.id}`)))throw Error(`Missing preserved route ${e.id}`);
  for(const path of [e.path,e.archivePath,...e.aliases].filter(Boolean)){if(routes.has(path))throw Error(`Duplicate IA route ${path}`);routes.add(path);}
  for(const lang of ['en','ko-KR'])if(e.bodyHashes[lang]!==digest(read(dir,`${lang}/${e.id}.json`)))throw Error(`IA body preservation review required: ${lang}/${e.id}`);
 }
 for(const j of journeys){
  if(j.issueIds.some(id=>!refs.has(id)))throw Error(`Broken verification reference ${j.id}`);
  if(!j.stages.length||new Set(j.stages.map(s=>s.id)).size!==j.stages.length)throw Error(`Invalid stage IDs ${j.id}`);
  const introductions={}; for(const stage of j.stages) for(const term of stage.terms) introductions[term]??=stage.id;
  if(JSON.stringify(introductions)!==JSON.stringify(review.termIntroductions[j.id]))throw Error(`Term introduction review required ${j.id}`);
  for(const lang of ['en','ko-KR']){
   for(const key of ['target','current','human','deferred'])if(!j.boundaries[key]?.[lang])throw Error(`Missing capability boundary ${j.id}/${key}/${lang}`);
   const md=read(dir,`journeys/${lang}/${j.id}.md`);
   const declared=[...md.matchAll(/<!-- stage:([a-z]+) -->/g)].map(m=>m[1]);
   if(JSON.stringify(declared)!==JSON.stringify(j.stages.map(s=>s.id)))throw Error(`Journey stage parity ${lang}/${j.id}`);
   if(review.prose[`${lang}/${j.id}`]!==digest(md))throw Error(`Journey prose review required ${lang}/${j.id}`);
   for(const s of j.stages){
    const text=md.split(`<!-- stage:${s.id} -->`)[1].split(/<!-- (?:stage:|checks)/)[0];
    if([...text.matchAll(/```diagram\n/g)].length!==1||[...text.matchAll(/^## /gm)].length!==1)throw Error(`One question/diagram per stage ${j.id}/${s.id}`);
    if(/\b(?:D1|DV1|C1|A1)\b/.test(text))throw Error(`Beginner identifier ${j.id}/${s.id}`);
    if(!anchors.has(s.anchor)||s.terms.some(t=>!glossary[t])||s.deepDives.some(id=>!ids.has(id))||s.referenceIds.some(id=>!refs.has(id)))throw Error(`Broken journey branch ${j.id}/${s.id}`);
    // Every registered term is shown inline at its first relevant stage; no
    // prerequisite concept reading is required for a new capability journey.
    validateTerms(text,glossary,[],`${lang}/${j.id}/${s.id}`);
   }
   if([...md.matchAll(/```check\n[\s\S]*?\n---\n[\s\S]*?\n```/g)].length<2)throw Error(`Missing comprehension checks ${j.id}`);
  }
 }
 for(const lang of ['en','ko-KR'])if(JSON.stringify(readdirSync(resolve(dir,'journeys',lang)).sort())!==JSON.stringify(primary.slice(1).map(id=>id+'.md').sort()))throw Error(`Missing journey language ${lang}`);
 for(const p of ['ia/catalog.json','ia/journeys.json'])if(review.metadata[p]!==digest(read(dir,p)))throw Error(`IA metadata review required: ${p}`);
 return {pages:catalog.entries.length,journeys:journeys.length,stages:journeys.reduce((n,j)=>n+j.stages.length,0)};
}
