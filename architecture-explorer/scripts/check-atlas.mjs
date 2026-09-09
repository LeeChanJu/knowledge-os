import {readFileSync,readdirSync} from 'node:fs';
import {resolve} from 'node:path';
import {createHash} from 'node:crypto';
import Ajv from 'ajv';
const hash=x=>createHash('sha256').update(x).digest('hex');
export function checkAtlas(root,architecture){
 const dir=resolve(root,'architecture-explorer/content/atlas'),read=p=>readFileSync(resolve(dir,p),'utf8');
 const model=JSON.parse(read('model.json')),review=JSON.parse(read('review.json')),catalog=JSON.parse(read('catalog.json'));
 const validate=new Ajv({strict:false}).compile(JSON.parse(read('schema.json')));if(!validate(model))throw Error('Atlas schema: '+JSON.stringify(validate.errors));
 const nodes=new Map(model.nodes.map(n=>[n.id,n])),refs=new Set(architecture.nodes.map(n=>n.id));
 if(nodes.size!==model.nodes.length)throw Error('Duplicate Atlas node');
 const expected={runtime:['question','assistant','connection','retrieve','store','support','explain','user'],engineering:['goal','design','rules','implementation','testing','verification','recovery','release','operations','improve']};
 if(JSON.stringify(model.backbones)!==JSON.stringify(expected))throw Error('Complete Atlas backbones required');
 const reach=(id,seen=new Set())=>{if(seen.has(id))throw Error('Atlas branch cycle');if(!nodes.has(id))throw Error('Broken Atlas branch: '+id);const next=new Set([...seen,id]);for(const c of nodes.get(id).branches)reach(c,next)};
 const reachable=(axis,id)=>{const visit=n=>n===id||nodes.get(n).branches.some(visit);return model.backbones[axis].some(visit)};
 for(const id of nodes.keys())reach(id);
 const legacy=JSON.parse(readFileSync(resolve(root,'architecture-explorer/content/manifest.json'))).pages;
 if(catalog.length!==77||new Set(catalog.map(e=>e.id)).size!==77||legacy.some(p=>!catalog.find(e=>e.id===p.id)))throw Error('Atlas must classify all 77 legacy pages');
 const ids=new Set(legacy.map(p=>p.id));
 for(const e of catalog){if(e.plannedMerge&&!ids.has(e.plannedMerge))throw Error('Broken Atlas merge');for(const l of ['en','ko-KR'])if(hash(readFileSync(resolve(root,`architecture-explorer/content/${l}/${e.id}.json`)))!==e.bodyHashes[l])throw Error('Legacy body changed without Atlas review');}
 for(const n of nodes.values()){
  if(!reachable('runtime',n.id)&&!reachable('engineering',n.id))throw Error('Orphan Atlas node');
  for(const ref of [...n.referenceIds,...n.claimIds,...n.architectureNodeIds])if(!refs.has(ref))throw Error('Broken Atlas reference: '+ref);
  if(n.documentId&&!ids.has(n.documentId))throw Error('Broken Atlas document');
  if(n.opposite&&(!model.backbones[n.opposite.axis]||!reachable(n.opposite.axis,n.opposite.node)))throw Error('Broken cross-roadmap mapping');
  for(const lang of ['en','ko-KR']){const p=n.content[lang];if(!p.startsWith(lang+'/')||p.includes('..')||!n.labels[lang])throw Error('Atlas language/path mismatch');if(!read(p).trim())throw Error('Empty Atlas prose');}
 }
 if(new Set(model.edges.map(e=>e.id)).size!==model.edges.length)throw Error('Duplicate Atlas edge');
 for(const e of model.edges){if(!nodes.has(e.source)||!nodes.has(e.target))throw Error('Broken Atlas edge');if(e.kind==='branch'&&!nodes.get(e.source).branches.includes(e.target))throw Error('Atlas branch edge mismatch');}
 for(const [axis,seq] of Object.entries(model.backbones))for(let i=0;i<seq.length-1;i++)if(!model.edges.some(e=>e.kind==='sequence'&&e.axis===axis&&e.source===seq[i]&&e.target===seq[i+1]))throw Error('Missing directed backbone edge');
 for(const n of nodes.values())if(n.opposite&&!model.edges.some(e=>e.kind==='cross-axis'&&e.source===n.id&&e.target===n.opposite.node&&e.axis===n.opposite.axis))throw Error('Missing cross-axis edge');
 for(const lang of ['en','ko-KR'])if(readdirSync(resolve(dir,lang)).length!==nodes.size)throw Error('Atlas bilingual coverage mismatch');
 for(const p of ['schema.json','model.json','catalog.json',...model.nodes.flatMap(n=>Object.values(n.content))])if(hash(read(p))!==review[p])throw Error('Atlas review required: '+p);
 return {nodes:nodes.size,runtime:model.backbones.runtime.length,engineering:model.backbones.engineering.length,legacy:catalog.length};
}
