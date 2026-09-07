import {readFileSync,readdirSync} from 'node:fs';
import {resolve} from 'node:path';
import {createHash} from 'node:crypto';
export const digest=s=>createHash('sha256').update(s).digest('hex');
const parse=p=>JSON.parse(readFileSync(p,'utf8'));
const escape=s=>s.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
export function validateTerms(text,glossary,introduced=[],where='lesson'){
 const available=new Set(introduced);
 const links=[...text.matchAll(/\[([^\]]+)\]\(term:([a-z]+)\)/g)];
 for(const link of links)if(!glossary[link[2]])throw Error(`${where}: unknown glossary term ${link[2]}`);
 for(const [id,g] of Object.entries(glossary))for(const alias of g.aliases){
  const re=new RegExp(`(?<![\\p{L}\\p{N}_])${escape(alias)}(?![\\p{L}\\p{N}_])`,'gu');
  for(const match of text.matchAll(re)){
   const enclosing=links.find(l=>match.index>=l.index&&match.index<l.index+l[0].length);
   if(enclosing?.[2]===id||available.has(id)||links.some(l=>l[2]===id&&l.index<match.index))continue;
   const line=text.slice(0,match.index).split('\n').length;
   throw Error(`${where}:${line}: ${alias} used before introduction; add an inline term:${id} definition`);
  }
 }
}
export function checkFlow(root,architecture){
 const dir=resolve(root,'architecture-explorer/content/flow'), m=parse(resolve(dir,'model.json')),g=parse(resolve(dir,'glossary.json')), gate=parse(resolve(dir,'review.json'));
 const ids=['start-here','source-of-truth','document-journey','ontology-basics'];
 if(JSON.stringify(Object.keys(m.pages))!==JSON.stringify(ids))throw Error('Flow milestone must contain exactly four pages');
 for(const key of ['stages','jobs'])if(new Set(m[key].map(x=>x.id)).size!==m[key].length)throw Error(`Duplicate flow ${key} ID`);
 const nodes=new Set(architecture.nodes.map(n=>n.id));
 for(const ref of m.evidence)if(!nodes.has(ref))throw Error(`Broken flow evidence ${ref}`);
 for(const s of m.stages){if(!m.labels[s.state]||!ids.includes(s.lesson)||s.terms.some(t=>!g[t]))throw Error(`Broken flow stage ${s.id}`);for(const ref of s.evidence||[])if(!nodes.has(ref))throw Error(`Broken stage evidence ${ref}`);}
 for(const job of m.jobs)if(!m.stages.some(s=>s.id===job.stage))throw Error(`Broken capability ${job.id}`);
 for(const [id,t] of Object.entries(g)){if(!ids.includes(t.lesson)||!m.stages.some(s=>s.id===t.stage))throw Error(`Broken glossary destination ${id}`);for(const lang of ['en','ko-KR'])if(!t[lang]?.definition||!t[lang]?.example||!t[lang]?.label)throw Error(`Missing glossary translation ${id}/${lang}`);}
 const ancestors=id=>{const seen=new Set();const visit=x=>{for(const p of gate.pages[x].prerequisites){if(p===id||!gate.pages[p])throw Error('Invalid prerequisite graph');if(!seen.has(p)){seen.add(p);visit(p)}}};visit(id);return [...seen]};
 for(const lang of ['en','ko-KR']){
  if(JSON.stringify(readdirSync(resolve(dir,lang)).sort())!==JSON.stringify(ids.map(id=>id+'.md').sort()))throw Error('Missing or extra flow lesson');
  for(const id of ids){
   const md=readFileSync(resolve(dir,lang,id+'.md'),'utf8');
   if(gate.pages[id].hashes[lang]!==digest(md))throw Error(`Flow review required: ${lang}/${id}`);
   const [begin,why,...extra]=md.split('\n<!-- WHY -->\n');if(!why||extra.length)throw Error(`Missing progressive disclosure ${id}`);
   for(const scene of begin.split('\n<!-- SCENE -->\n')){if([...scene.matchAll(/```diagram\n/g)].length!==1||[...scene.matchAll(/^## /gm)].length!==1)throw Error(`One question and diagram per visual section: ${id}`);if(/\b(?:D1|DV1|V1|C1|A1|P1)\b/.test(scene))throw Error(`Beginner identifier ${id}`);const prose=scene.replace(/```[\s\S]*?```/g,'').replace(/^## .*$/gm,'').trim();if(prose.split(/\n\n+/).length>1||prose.length>720)throw Error(`Excessive beginner prose ${id}`);}
   const questions=[...why.matchAll(/```check\n([\s\S]*?)\n---\n([\s\S]*?)\n```/g)];if(questions.length<2||questions.length>4||questions.some(q=>q[2].length<35))throw Error(`Substantive checks missing ${id}`);
   const introduced=ancestors(id).flatMap(p=>gate.pages[p].introduces);
   validateTerms(md,g,introduced,`${lang}/${id}`);
   for(const term of gate.pages[id].introduces)if(!md.includes(`](term:${term})`))throw Error(`Claimed term introduction missing ${id}/${term}`);
   const other=readFileSync(resolve(dir,lang==='en'?'ko-KR':'en',id+'.md'),'utf8');
   if([...md.matchAll(/```(?:diagram|check)\n/g)].length!==[...other.matchAll(/```(?:diagram|check)\n/g)].length)throw Error(`Bilingual diagram/check parity ${id}`);
  }
 }
 for(const file of ['model.json','glossary.json'])if(gate.fingerprints[file]!==digest(readFileSync(resolve(dir,file),'utf8')))throw Error(`Flow model review required: ${file}`);
 return gate;
}
