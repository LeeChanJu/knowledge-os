import {readFileSync} from 'node:fs';
import {resolve} from 'node:path';
import {createHash} from 'node:crypto';
const hash=s=>createHash('sha256').update(s).digest('hex');
export function checkIntegration(root,architecture){
 const base=resolve(root,'architecture-explorer'),read=p=>readFileSync(resolve(base,p),'utf8'),json=p=>JSON.parse(read(p));
 const integration=json('content/atlas/integration.json'),model=json('content/atlas/model.json'),review=json('content/atlas/integration-review.json'),manifest=json('content/manifest.json').pages;
 const entries=new Map(integration.entries.map(e=>[e.id,e])),nodes=new Map(model.nodes.map(n=>[n.id,n])),refs=new Set(architecture.nodes.map(n=>n.id));
 if(integration.schemaVersion!=='1.0.0'||entries.size!==77||integration.entries.length!==77||manifest.some(p=>!entries.has(p.id)))throw Error('All 77 documents require final integration');
 const reachable=(location)=>{const base=location.axis==='engineering'?model.backbones.engineering:model.journeys.find(j=>j.id===location.journey)?.backbone||[];const visit=id=>id===location.node||nodes.get(id).branches.some(visit);return base.some(visit)};
 const aliases=new Set();
 for(const e of entries.values()){
  if(!['integrated','merged','redirected'].includes(e.resolution)||!['runtime','engineering'].includes(e.location.axis)||!reachable(e.location))throw Error('Invalid document map location: '+e.id);
  const target=entries.get(e.canonicalId);if(!target||target.canonicalId!==target.id)throw Error('Merge cycle or broken canonical document');
  if(e.resolution==='merged'&&(e.id===e.canonicalId||target.resolution!=='integrated'))throw Error('Unresolved document merge');
  if(e.archive!=='archive/document/'+e.id)throw Error('Missing archive route');
  for(const path of e.aliases){if(aliases.has(path))throw Error('Duplicate legacy alias');aliases.add(path)}
 }
 if(integration.guides.length!==68||new Set(integration.guides.map(g=>g.id)).size!==68)throw Error('68 canonical guides required');
 for(const g of integration.guides){
  if(JSON.stringify(g.architectureNodeIds)!==JSON.stringify(manifest.find(p=>p.id===g.id)?.nodeIds))throw Error('Guide component ownership must match its authoritative manifest');
  if(entries.get(g.id)?.resolution!=='integrated')throw Error('Guide has no integrated owner');
  const expected=integration.entries.filter(e=>e.canonicalId===g.id).map(e=>e.id).sort();if(JSON.stringify([...g.members].sort())!==JSON.stringify(expected))throw Error('Merged content member missing');
  for(const id of [...g.referenceIds,...g.claimIds])if(!refs.has(id))throw Error('Broken guide evidence: '+id);
  if(g.relatedIds.some(id=>!entries.has(id)))throw Error('Broken related guide');
  for(const lang of ['en','ko-KR']){
   const path=g.content[lang];if(path!==lang+'/'+g.id+'.md')throw Error('Guide language mismatch');const body=read('content/guides/'+path);
   if(body.length<700||body.split('<!-- CHECKS -->').length!==2||body.split('<!-- CHECKS -->')[1].split('### ').length<3)throw Error('Incomplete guide depth or comprehension');
   if(!review.files['content/guides/'+path])throw Error('Unreviewed guide');
  }
 }
 for(const n of nodes.values())for(const lang of ['en','ko-KR']){const body=read('content/atlas/'+n.content[lang]);if(body.split('<!-- DEPTH -->').length!==2||body.split('<!-- DEPTH -->')[1].split('### ').length<6)throw Error('Incomplete roadmap depth: '+n.id)}
 for(const [path,digest] of Object.entries({...review.sources,...review.files}))if(hash(read(path))!==digest)throw Error('Integration review required: '+path);
 return {documents:77,guides:68,merged:integration.entries.filter(e=>e.resolution==='merged').length,redirected:integration.entries.filter(e=>e.resolution==='redirected').length,depthNodes:nodes.size};
}
