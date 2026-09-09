import integration from '../../content/atlas/integration.json';
import model from '../../content/atlas/model.json';
import {atlasHref} from './state';
export {integration};
export const integratedEntry=(id:string)=>integration.entries.find(e=>e.id===id);
export const canonicalEntry=(id:string)=>integratedEntry(integratedEntry(id)?.canonicalId||id);
export function locationHref(lang:string,id:string){
 const entry=integratedEntry(id);if(!entry)return `#/${lang}`;
 return atlasHref(lang,{...entry.location,axis:entry.location.axis as 'runtime'|'engineering',root:'',open:[entry.location.node],returnTo:''});
}
export function guideHref(lang:string,id:string,query=''){
 const entry=canonicalEntry(id);if(!entry)return `#/${lang}/reference`;
 if(entry.resolution==='redirected')return locationHref(lang,id);
 const q=new URLSearchParams(query);if(entry.id!==id)q.set('from',id);
 return `#/${lang}/${entry.route}${q.size?'?'+q:''}`;
}
export function migrateHash(hash:string,lang:string):string|null{
 const [path,q='']=hash.replace(/^#\/(en|ko-KR)\/?/,'').split('?');
 if(path.startsWith('archive/'))return null;
 if(path==='learn'||path==='learn/start-here')return `#/${lang}`;
 if(path.startsWith('learn/')){
  const id=path.slice(6),journey=(integration.legacyJourneys as Record<string,string>)[id];
  if(journey){
   const query=new URLSearchParams(q),step=query.get('step');
   const ids:Record<string,string>={words:'words',meaning:'meaning',connections:'links',answer:'support',subjects:'relation-subjects',statements:'relation-statements',rules:'relation-rules',support:'relation-support'};
   const node=id==='find'||id==='relationships'?ids[step||'']:(step?`${id}-${step}`:'');
   const origin=atlasHref(lang,{axis:'runtime',journey,node:node&&model.nodes.some(n=>n.id===node)?node:'',root:'',open:node?[node]:[],returnTo:''});
   const concept=query.get('concept'),documents:Record<string,string>={version:'document-version',vector:'vector-search',fulltext:'full-text-search',graph:'knowledge-graph',canonical:'approval',retrieval:'hybrid-retrieval'};
   const document=concept&&(documents[concept]||concept);
   return document&&integratedEntry(document)?guideHref(lang,document,'atlas='+encodeURIComponent(origin.replace(`#/${lang}/`,''))):origin;
  }
  if(integratedEntry(id))return locationHref(lang,id);
 }
 if(path.startsWith('reference/guide/')){const id=path.slice(16),e=integratedEntry(id);if(e&&e.resolution!=='integrated')return guideHref(lang,id,q);}
 const entry=integration.entries.find(e=>e.aliases.includes(path));
 return entry?guideHref(lang,entry.id,q):null;
}
export function stageTrail(base:string[],target:string):string[]{
 const visit=(id:string,path:string[]):string[]=>{if(id===target)return [...path,id];for(const next of model.nodes.find(n=>n.id===id)?.branches||[]){if(path.includes(next))continue;const found=visit(next,[...path,id]);if(found.length)return found}return []};
 for(const root of base){const found=visit(root,[]);if(found.length)return found}return [];
}
