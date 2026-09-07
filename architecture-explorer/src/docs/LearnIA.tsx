import {useState,useEffect} from 'react';
import {WholeMap, LessonBody, flowText} from './LearnFlow';
import {Term} from './Term';
import {capabilities, capability, catalog, classification, docHref, journeyContext, contextQuery, conceptDoc, mapTarget} from './ia';
import glossary from '../../content/flow/glossary.json';
import learning from '../../data/learning.json';
import type {Language} from '../i18n';
const prose=import.meta.glob('../../content/journeys/{en,ko-KR}/*.md',{query:'?raw',import:'default',eager:true}) as Record<string,string>;
export const journeyText=(lang:Language,id:string)=>prose[`../../content/journeys/${lang}/${id}.md`]||'';
export function CapabilityNav({lang,active=''}:{lang:Language;active?:string}){
 return <nav className="ia-nav" aria-label={lang==='en'?'Learning journeys':'행동으로 배우기'}>
  <a href={`#/${lang}/learn/start-here`} aria-current={active==='start-here'?'page':undefined}>{lang==='en'?'Whole system':'전체 시스템'}</a>
  {capabilities.map(j=><a key={j.id} href={`#/${lang}/learn/${j.id}`} aria-current={active===j.id?'page':undefined}>{j.title[lang]}</a>)}
 </nav>;
}
export function ContextTrail({lang}:{lang:Language}){
 const ctx=journeyContext(),j=capability(ctx?.journey||'');
 if(!ctx||!j)return <nav className="ia-context"><a href={`#/${lang}/learn/start-here`}>{lang==='en'?'Return to the whole-system flow':'전체 흐름에서 위치 찾기'} ↑</a></nav>;
 const s=j.stages.find(s=>s.id===ctx.step)!;
 return <nav className="ia-context" aria-label={lang==='en'?'Learning position':'학습 위치'}>
 <a href={`#/${lang}/learn/start-here?${contextQuery(ctx)}`}>{lang==='en'?'Whole system':'전체 시스템'}</a><span>›</span>
 <a href={`#/${lang}/learn/${j.id}`}>{j.title[lang]}</a><span>›</span>
 <a href={`#/${lang}/learn/${j.id}?step=${s.id}${ctx.concept?'&concept='+ctx.concept:''}`}>{s.title[lang]}</a>
 </nav>;
}
export function LearnHome({lang}:{lang:Language}){
 const ko=lang==='ko-KR',context=journeyContext(),j=capability(context?.journey||'');
 const [search,setSearch]=useState('');
 const matches=capabilities.filter(j=>(j.title[lang]+' '+j.request[lang]).toLowerCase().includes(search.toLowerCase()));
 return <main className="docs-article ia-home">
 <div className="eyebrow">LEARN · {ko?'전체를 보고, 궁금한 가지로':'THE WHOLE FIRST, THEN BRANCH OUT'}</div>
 <h1>{ko?'Knowledge OS로 무엇을 할 수 있나요?':'What can I do with Knowledge OS?'}</h1>
 <WholeMap lang={lang} job={j?.job} stage={j?.stages.find(s=>s.id===context?.step)?.anchor} route={q=>mapTarget(lang,q)} question={ko?'원본은 그대로 두고, AI와 어떻게 기억하고 찾을까요?':'How do I remember and find with AI while originals stay in place?'}/>
 <section className="journey-choices"><h2>{ko?'하고 싶은 일 하나를 골라보세요':'Choose something you want to do'}</h2>
 <label className="journey-search">{ko?'행동 찾기':'Find a journey'}<input value={search} onChange={e=>setSearch(e.target.value)} placeholder={ko?'기억, 근거, 정정…':'Remember, source, correct…'}/></label>
 <div className="journey-card-grid">{matches.map((j,i)=><a key={j.id} href={`#/${lang}/learn/${j.id}`}><small>{String(i+1).padStart(2,'0')}</small><strong>{j.title[lang]}</strong><span>{j.request[lang]}</span><span aria-hidden="true">→</span></a>)}</div>
 {!matches.length&&<p role="status">{ko?'해당하는 행동이 없습니다. 다른 말로 찾아보세요.':'No journeys match. Try another word.'}</p>}
 </section>
 <details className="ia-primer"><summary>{ko?'처음이라면: 왜 바로 믿지 않고 검토할까요?':'New here? Why review instead of trusting immediately?'}</summary><LessonBody text={flowText(lang,'start-here').split('\n<!-- WHY -->\n')[0].replace(/<!-- SCENE -->/g,'')} lang={lang}/></details>
 <section className="surface-choices"><a href={`#/${lang}/explore`}>Explore · {ko?'구현의 관계 지도':'Architecture relationships'} ↗</a><a href={`#/${lang}/reference`}>Reference · {ko?'정확한 개념·구현 찾기':'Exact concepts and implementation'} ↗</a><a href={`#/${lang}/reference/deep-dives/start-here`}>{ko?'기존 시작 문서와 기술 상세':'Preserved introduction and technical detail'} ↗</a></section>
 </main>;
}
export function Journey({id,lang}:{id:string;lang:Language}){
 const j=capability(id)!,ko=lang==='ko-KR',q=new URLSearchParams(location.hash.split('?')[1]);
 const step=j.stages.find(s=>s.id===q.get('step'))||j.stages[0],index=j.stages.indexOf(step);
 const term=q.get('concept')||'',g=step.terms.includes(term)?glossary[term as keyof typeof glossary]:null;
 const url=(sid:string,concept='')=>`#/${lang}/learn/${id}?step=${sid}${concept?'&concept='+concept:''}`;
 useEffect(()=>{if(!q.has('step')&&!g)return;const frame=requestAnimationFrame(()=>document.querySelector(g?'.concept-inspector':'.journey-stage')?.scrollIntoView({block:'start'}));return()=>cancelAnimationFrame(frame)},[id,step.id,term]);
 const context={journey:id,step:step.id,concept:g?term:''};
 const text=journeyText(lang,id),stageText=text.split(`<!-- stage:${step.id} -->`)[1]?.split(/<!-- (?:stage:|checks)/)[0]||'';
 const docs=learning.documents[lang] as Record<string,{title:string}>;
 const labels={target:ko?'목표 경험':'Target experience',current:ko?'현재 구현':'Current implementation',human:ko?'권한·사람의 경계':'Authorization / human boundary',deferred:ko?'보류·미검증 범위':'Deferred / unverified scope'};
 return <main className="docs-article capability-journey" key={id}>
 <ContextTrail lang={lang}/><h1>{j.title[lang]}</h1><p className="journey-intent"><small>{ko?'따라가 볼 목표 경험':'Target experience to explore'}</small>{j.request[lang]}</p>
 <details className="journey-whole"><summary>{ko?'전체 지도에서 이 경로 보기':'Locate this path in the whole map'}</summary><WholeMap lang={lang} stage={step.anchor} job={j.job} route={query=>mapTarget(lang,query)} question={ko?'지금 전체 흐름의 어디인가요?':'Where am I in the whole flow?'}/></details>
 <section className="journey-path" aria-label={ko?'전체 행동 경로':'Complete capability path'}><div className="journey-endpoint">{ko?'나 → Claude/GPT → 연결 창구':'Me → Claude/GPT → connection tools'}</div><ol>{j.stages.map((s,i)=><li key={s.id}><a href={url(s.id)} aria-current={step.id===s.id?'step':undefined}><small>{i+1}</small>{s.title[lang]}</a></li>)}</ol><div className="journey-endpoint">{ko?'자료·결과 반환 → Claude/GPT → 나':'Return material/outcome → Claude/GPT → me'}</div></section>
 <section className="journey-stage" aria-label={step.title[lang]}>
 <div className="stage-neighbors">{ko?'이전':'Before'}: {j.stages[index-1]?.title[lang]||(ko?'요청과 근거':'Request and source material')} → <strong>{step.title[lang]}</strong> → {ko?'다음':'After'}: {j.stages[index+1]?.title[lang]||(ko?'자료·결과 반환':'Return material/outcome')}</div>
 <LessonBody text={stageText} lang={lang}/>
 <div className="concept-branches"><h3>{ko?'이 동작을 설명하는 개념':'Concepts that explain this step'}</h3>{step.terms.map(t=>{const g=glossary[t as keyof typeof glossary];return <Term key={t} id={t} lang={lang} href={url(step.id,t)}>{g[lang].label}</Term>})}</div>
 {g&&<section className="concept-inspector" aria-label={ko?'개념 가지':'Concept branch'}><a className="concept-close" href={url(step.id)}>{ko?'단계로 접기':'Back to stage'} ↑</a><small>{step.title[lang]} → {g[lang].label}</small><h3>{g.name}</h3><p>{g[lang].definition}</p><p>{g[lang].example}</p><a href={docHref(lang,conceptDoc(term),context)}>{ko?'관련 설명 깊게 보기':'Read the related explanation'} →</a></section>}
 <details className="stage-deep-dives"><summary>{ko?'더 깊게 보기 · 설명과 구현':'Go deeper · explanation and implementation'}</summary><div className="stage-reading-links">{step.deepDives.map(d=><a key={d} href={docHref(lang,d,context)}>{docs[d]?.title} →</a>)}</div><h3>{ko?'Knowledge OS 구현 근거':'Knowledge OS implementation evidence'}</h3><p>{ko?'아래 링크는 구현 위치이며 새로운 통과 결과가 아닙니다.':'These identify implementation locations, not fresh passing results.'}</p>{step.referenceIds.map(ref=><a className="journey-evidence" key={ref} href={`#/${lang}/reference/item/${encodeURIComponent(ref)}?${contextQuery(context)}`}>{ref.slice(4)}</a>)}<a href={`#/${lang}/explore/node/${({source:'source',interface:'mcp',evidence:'chunk',review:'proposal',knowledge:'assertion',retrieval:'keyword',answer:'mcp'} as Record<string,string>)[step.anchor]}?${contextQuery(context)}`}>Explore ↗</a></details>
 </section>
 <nav className="journey-step-nav" aria-label={ko?'이전·다음 단계':'Previous and next step'}>{index>0&&<a href={url(j.stages[index-1].id)}>← {j.stages[index-1].title[lang]}</a>}{index<j.stages.length-1&&<a href={url(j.stages[index+1].id)}>{j.stages[index+1].title[lang]} →</a>}<a href={`#/${lang}/learn/start-here?${contextQuery(context)}`}>{ko?'전체 흐름으로':'Whole flow'} ↑</a></nav>
 <details className="capability-boundaries"><summary>{ko?'현재 어디까지 실행할 수 있나요?':'What can execute today?'}</summary><div>{Object.entries(j.boundaries).map(([key,value])=><section key={key} className={`scope-${key}`}><h3>{labels[key as keyof typeof labels]}</h3><p>{value[lang]}</p></section>)}</div><div className="stage-reading-links">{j.issueIds.map(issue=><a key={issue} href={`#/${lang}/reference/item/${issue}?${contextQuery(context)}`}>{issue} · {ko?'검증 범위 확인':'Verification scope'}</a>)}</div></details>
 <p className="journey-scope-note">{j.boundaries.current[lang]} {ko?'전체 대화의 자동 실행을 뜻하지 않습니다.':'This does not mean the complete conversation executes automatically.'}</p>
 <details className="journey-checks"><summary>{ko?'내 말로 설명해 보기':'Check your understanding'}</summary><LessonBody text={text.split('<!-- checks -->')[1]||''} lang={lang}/></details>
 </main>;
}
export function ReferenceCatalog({lang}:{lang:Language}){
 const [query,setQuery]=useState(''),[role,setRole]=useState('');
 const docs=learning.documents[lang] as Record<string,{title:string}>;
 const groups=[['DEEP DIVE','깊이 보기','Deep dives'],['EXPLANATION','설명','Explanations'],['REFERENCE','개념·운영 참조','Concept / operation references']];
 const entries=catalog.entries.filter(e=>e.role!=='FLOW LESSON'&&(!role||e.role===role)&&(`${docs[e.id]?.title} ${e.id}`).toLowerCase().includes(query.toLowerCase()));
 return <section className="reference-library"><h2>{lang==='en'?'Concepts and explanations':'개념과 설명'}</h2><p>{lang==='en'?'Open these when a journey raises a question. They are reference branches, not a required reading sequence.':'흐름을 따라가다 궁금해질 때 여는 가지입니다. 처음부터 순서대로 읽어야 하는 목차가 아닙니다.'}</p><label>{lang==='en'?'Find a concept':'개념 찾기'}<input value={query} onChange={e=>setQuery(e.target.value)}/></label><label>{lang==='en'?'Document role':'문서 역할'}<select value={role} onChange={e=>setRole(e.target.value)}><option value="">{lang==='en'?'All roles':'모든 역할'}</option>{groups.map(([id,ko,en])=><option key={id} value={id}>{lang==='en'?en:ko}</option>)}</select></label>
 {!entries.length&&<p role="status">{lang==='en'?'No concept documents match.':'일치하는 개념 문서가 없습니다.'}</p>}{groups.map(([id,ko,en])=><details key={id} open={!!query||!!role}><summary>{lang==='en'?en:ko} · {entries.filter(e=>e.role===id).length}</summary><div>{entries.filter(e=>e.role===id).map(e=><a key={e.id} href={docHref(lang,e.id)}>{docs[e.id]?.title}</a>)}</div></details>)}
 </section>;
}
