import {checkFlow} from './check-flow.mjs';
import {readFileSync, readdirSync} from 'node:fs';
import {resolve} from 'node:path';
import {createHash} from 'node:crypto';
export const textHash = s => createHash('sha256').update(s).digest('hex');
export function checkFlagships(root, architecture, pageIds) {
  const dir=resolve(root,'architecture-explorer/content');
  const metadata=JSON.parse(readFileSync(resolve(dir,'flagships.json'),'utf8'));
  const expected=['start-here','source-of-truth','document-journey','ontology-basics'];
  if(JSON.stringify(Object.keys(metadata.pages))!==JSON.stringify(expected)) throw Error('Only four approved flagships are allowed');
  const nodes=new Map(architecture.nodes.map(n=>[n.id,n]));
  for(const lang of ['en','ko-KR']) {
    if(JSON.stringify(readdirSync(resolve(dir,lang)).filter(f=>f.endsWith('.md')).sort())!==JSON.stringify(expected.map(p=>p+'.md').sort())) throw Error('Missing or extra flagship Markdown translation');
    for(const [id,p] of Object.entries(metadata.pages)) {
      const md=readFileSync(resolve(dir,lang,id+'.md'),'utf8');
      if(p.hashes[lang]!==textHash(md)) throw Error(`Flagship review required: ${lang}/${id}`);
      const headings=[...md.matchAll(/^## .+ \{#([a-z-]+)\}$/gm)].map(m=>m[1]);
      if(JSON.stringify(headings)!==JSON.stringify(p.sections)) throw Error(`Flagship section parity: ${lang}/${id}`);
      if(new Set(headings).size!==headings.length) throw Error(`Duplicate flagship heading: ${id}`);
      for(const h of ['objectives','example','current','checks']) if(!headings.includes(h))throw Error(`Missing flagship teaching element: ${id}/${h}`);
      const questions=[...md.matchAll(/```question\n([\s\S]*?)\n```/g)];
      if(questions.length<2||questions.length>4||questions.some(q=>q[1].split('\n---\n').some(s=>s.trim().length<30)||!q[1].includes('\n---\n')))throw Error(`Incomplete comprehension checks: ${id}`);
      if(!md.includes('```flow\n')||!md.includes('CURRENT v0.1')||!md.includes('TARGET / DEFERRED')) throw Error(`Missing flagship teaching diagram or boundaries: ${id}`);
      if(/<\/?(?:script|iframe|img)\b/i.test(md)||/\]\((?:https?:|javascript:)/i.test(md))throw Error(`Keep conceptual sources in their separate reviewed section: ${id}`);
      // The text stays in Markdown, never in generated architecture/learning JSON.
    }
  }
  for(const [id,p] of Object.entries(metadata.pages)){
    for(const next of [...p.prerequisites,p.next].filter(Boolean)) if(!pageIds.has(next))throw Error(`Broken flagship lesson: ${id}/${next}`);
    for(const ref of p.referenceIds)if(!nodes.get(ref)?.resource)throw Error(`Broken flagship implementation evidence: ${ref}`);
    if(!p.referenceIds.some(r=>r.includes('tests/'))||!p.referenceIds.some(r=>r.includes('docs/architecture/'))||!p.referenceIds.some(r=>r.includes('src/')))throw Error(`Missing code/test/ADR evidence: ${id}`);
    for(const n of p.nodeIds)if(!nodes.has(n))throw Error(`Broken flagship Explore node: ${n}`);
    for(const s of p.conceptualSources)if(!metadata.sources[s])throw Error(`Broken conceptual source: ${s}`);
  }
  checkFlow(root, architecture);
  return metadata;
}
