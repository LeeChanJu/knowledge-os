import remarkGfm from 'remark-gfm';
import Markdown from 'react-markdown';
import learning from '../../data/learning.json';
import flagships from '../../content/flagships.json';
import model from '../../content/atlas/model.json';
import {integration,integratedEntry,canonicalEntry,guideHref,locationHref,stageTrail} from './integration';
import {atlasHref} from './state';
import {githubLink} from '../docs/helpers';
import {Term} from '../docs/Term';
import type {Language} from '../i18n';
import type {Architecture} from '../model';
const text=import.meta.glob('../../content/guides/{ko-KR,en}/*.md',{query:'?raw',import:'default',eager:true}) as Record<string,string>;
export function GuideLocation({id,lang}:{id:string;lang:Language}){
 const e=integratedEntry(id);if(!e)return null;
 const {axis,journey,node}=e.location,base=axis==='engineering'?model.backbones.engineering:model.journeys.find(j=>j.id===journey)!.backbone;
 const trail=stageTrail(base,node);
 return <nav className="guide-location" aria-label={lang==='en'?'Position in the whole flow':'전체 흐름에서의 위치'}><a href={`#/${lang}/${axis}${axis==='runtime'&&journey!=='read'?'?journey='+journey:''}`}>{lang==='en'?'↑ Whole flow':'↑ 전체 흐름'}</a><ol>{base.map(n=><li key={n}><a aria-current={n===trail[0]?'step':undefined} href={atlasHref(lang,{axis:axis as 'runtime'|'engineering',journey,node:n,root:'',open:[n],returnTo:''})}>{model.nodes.find(x=>x.id===n)!.labels[lang]}</a></li>)}</ol><p className="guide-trail">{trail.map(n=>model.nodes.find(x=>x.id===n)!.labels[lang]).join(' → ')}</p><a href={locationHref(lang,id)}>{lang==='en'?'Return to this stage':'이 단계로 돌아가기'} → {model.nodes.find(n=>n.id===node)!.labels[lang]}</a></nav>;
}
export default function Guide({id,lang,architecture}:{id:string;lang:Language;architecture:Architecture}){
 const e=canonicalEntry(id),g=integration.guides.find(g=>g.id===e?.id),ko=lang==='ko-KR';
 if(!e||!g)return <main><h1>{ko?'문서를 찾을 수 없습니다':'Guide not found'}</h1><a href={`#/${lang}/reference`}>Reference</a></main>;
 const docs=learning.documents[lang] as Record<string,{title:string}>;
 const [body,checks='']=text[`../../content/guides/${g.content[lang]}`].split('<!-- CHECKS -->');
 const context=new URLSearchParams(location.hash.split('?')[1]).get('atlas')||locationHref(lang,id).replace(`#/${lang}/`,'');
 const query='atlas='+encodeURIComponent(context);
 const questions=checks.split('### ').slice(1).map(p=>({question:p.split('\n')[0],answer:p.slice(p.indexOf('\n')).trim()}));
 const conceptual=[...new Set(g.members.flatMap(id=>(flagships.pages as Record<string,{conceptualSources:string[]}>)[id]?.conceptualSources||[]))];
 const term=model.nodes.find(n=>n.id===e.location.node)?.term;
 return <main className="integrated-guide" key={e.id}><GuideLocation id={e.id} lang={lang}/><small>{e.role}</small><h1>{docs[e.id].title}</h1>{g.members.length>1&&<p className="guide-merged">{ko?'함께 통합한 주제':'Merged topics'}: {g.members.map(mid=>docs[mid].title).join(' · ')}</p>}
 <Markdown remarkPlugins={[remarkGfm]}>{body.split('\n## ')[0]}</Markdown>
 {term&&<Term id={term} lang={lang} href={locationHref(lang,e.id)}>{ko?'지도에서 개념 살펴보기':'Inspect the concept in its flow'}</Term>}
 {body.split('\n## ').slice(1).map(section=>{const i=section.indexOf('\n');return <details className="guide-section" key={section.slice(0,i)}><summary>{section.slice(0,i)}</summary><Markdown remarkPlugins={[remarkGfm]}>{section.slice(i)}</Markdown></details>})}
 <section className="guide-checks"><h2>{ko?'스스로 설명해 보기':'Explain it yourself'}</h2>{questions.map(q=><div key={q.question}><p>{q.question}</p><details><summary>{ko?'생각해 본 뒤 답 보기':'Reveal a possible answer'}</summary><Markdown remarkPlugins={[remarkGfm]}>{q.answer}</Markdown></details></div>)}</section>
 {conceptual.length>0&&<details className="guide-conceptual"><summary>{ko?'개념 참고 자료':'Conceptual references'}</summary><p>{ko?'외부 자료는 개념 설명을 위한 것입니다. 외부 제품의 기능이 Knowledge OS에 구현되었다는 뜻은 아닙니다.':'These external sources explain concepts; their product capabilities are not claims about this repository.'}</p>{conceptual.map(id=>{const source=(flagships.sources as Record<string,{title:string;url:string}>)[id];return <a className="guide-related" key={id} href={source.url} target="_blank" rel="noreferrer">{source.title} ↗</a>})}</details>}
 <details className="guide-evidence"><summary>{ko?'Knowledge OS 구현·테스트·ADR 근거':'Knowledge OS implementation, test and ADR evidence'}</summary><p>{ko?'구현 참조와 실행된 검증 결과는 다릅니다.':'Implementation references are different from executed verification.'}</p>{g.referenceIds.map(ref=><div key={ref}><a href={`#/${lang}/reference/item/${encodeURIComponent(ref)}?${query}`}>{ref.slice(4)}</a> · <a href={githubLink(ref)} target="_blank" rel="noreferrer">GitHub ↗</a></div>)}</details>
 <details className="guide-verification"><summary>{ko?'현재 검증 상태·남은 범위':'Current verification and remaining scope'}</summary>{g.claimIds.length?g.claimIds.map(id=>{const claim=architecture.verification.find(c=>c.id===id);return claim&&<section key={id}><h3>{id} · {claim.status}</h3><p>{claim.scope}</p><p>{claim.limitations}</p><a href={`#/${lang}/reference/item/${id}?${query}`}>{ko?'실행 기록과 범위 확인':'Inspect execution records and scope'} →</a></section>}):<p>{ko?'이 문서에 연결된 새로운 실행 검증 주장은 없습니다. 코드나 테스트 파일만으로 VERIFIED를 부여하지 않습니다.':'No executed verification claim is attached to this guide. Code and test files alone do not establish VERIFIED.'}</p>}</details>
 <details><summary>{ko?'연관 문서':'Related guides'}</summary>{[...new Set(g.relatedIds.map(id=>canonicalEntry(id)?.id).filter(Boolean))].map(id=><a className="guide-related" key={id} href={guideHref(lang,id!,query)}>{docs[id!].title} →</a>)}</details>
 <details className="guide-archive"><summary>{ko?'이전 문서와 통합 이력':'Original documents and merge history'}</summary>{g.members.map(id=><a className="guide-related" key={id} href={`#/${lang}/archive/document/${id}?${query}`}>{docs[id].title} · {ko?'이전 본문':'archived original'} ↗</a>)}</details>
 </main>;
}
