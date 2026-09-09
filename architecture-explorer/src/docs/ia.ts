import {guideHref,locationHref,integratedEntry} from '../atlas/integration';
import catalog from '../../content/ia/catalog.json';
import journeys from '../../content/ia/journeys.json';
import glossary from '../../content/flow/glossary.json';
import type {Language} from '../i18n';
export {catalog};
export const capabilities=journeys.journeys;
export const classification=(id:string)=>catalog.entries.find(e=>e.id===id);
export const capability=(id:string)=>capabilities.find(j=>j.id===id);
export function journeyContext(){
 const q=new URLSearchParams(location.hash.split('?')[1]);
 const route=location.hash.split('?')[0].split('/').at(-1)||'';
 const j=capability(route)||capability(q.get('journey')||'');
 if(!j)return null;
 const stage=j.stages.find(s=>s.id===(q.get('step')||''))||j.stages[0];
 const concept=stage.terms.includes(q.get('concept')||'')?q.get('concept')||'':'';
 return {journey:j.id,step:stage.id,concept};
}
export function contextQuery(context=journeyContext()){
 const q=new URLSearchParams(context?Object.entries(context).filter(([,v])=>v):[]);
 const atlas=new URLSearchParams(location.hash.split('?')[1]).get('atlas');if(atlas)q.set('atlas',atlas);
 return q.toString();
}
export function docHref(lang:Language,id:string,context=journeyContext()){
 return guideHref(lang,id,contextQuery(context));
}
export function termHref(lang:Language,id:string){
 const doc=conceptDoc(id);if(integratedEntry(doc))return locationHref(lang,doc);
 const g=glossary[id as keyof typeof glossary];return locationHref(lang,g?.lesson||'start-here');
}

export function conceptDoc(id:string){return ({version:'document-version',vector:'vector-search',fulltext:'full-text-search',graph:'knowledge-graph',canonical:'approval',retrieval:'hybrid-retrieval'} as Record<string,string>)[id]||id;}

export function mapTarget(lang:Language,query:string){
 const q=new URLSearchParams(query), job=q.get('job'),anchor=q.get('stage');
 const ids:Record<string,string>={source:'sources',interface:'remember',evidence:'sources',review:'remember',knowledge:'relationships',retrieval:'find',answer:'find'};
 const preferred=capabilities.find(j=>j.job===job);
 const j=(preferred&&(!anchor||preferred.stages.some(s=>s.anchor===anchor))?preferred:capability(ids[anchor||'']||'remember'))!;
 const step=(j.id==='remember'&&anchor==='knowledge'?j.stages.find(s=>s.id==='store'):j.stages.find(s=>s.anchor===anchor))||j.stages[0];
 return `#/${lang}/learn/${j.id}?step=${step.id}`;
}

export function contextualHref(lang:Language,path:string){
 if(path.startsWith('learn/')&&classification(path.slice(6)))return docHref(lang,path.slice(6));
 const query=contextQuery();return `#/${lang}/${path}${query?'?'+query:''}`;
}
