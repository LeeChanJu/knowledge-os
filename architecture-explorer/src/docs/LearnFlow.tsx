import {mapTarget,docHref,contextualHref} from './ia';
import {Term} from './Term';
export {Term} from './Term';
import {Children, isValidElement, useEffect, useState, useId} from 'react';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import flow from '../../content/flow/model.json';
import glossary from '../../content/flow/glossary.json';
import type {Language} from '../i18n';
const texts=import.meta.glob('../../content/flow/{en,ko-KR}/*.md',{query:'?raw',import:'default',eager:true}) as Record<string,string>;
export const flowText=(lang:Language,id:string)=>texts[`../../content/flow/${lang}/${id}.md`]||'';
type TermId=keyof typeof glossary;
export function LessonBody({text,lang}:{text:string;lang:Language}){
 return <Markdown urlTransform={url=>url.startsWith('term:')?url:/^(?:javascript|data):/i.test(url)?'':url} remarkPlugins={[remarkGfm]} components={{
 a:({href,children})=>href?.startsWith('term:')?<Term id={href.slice(5)} lang={lang}>{children}</Term>:<a href={href}>{children}</a>,
 pre:({children})=>{const c=Children.toArray(children)[0];if(!isValidElement<{className?:string;children?:React.ReactNode}>(c))return <pre>{children}</pre>;const value=String(c.props.children).trim();
 if(c.props.className==='language-diagram')return <figure className="teaching-diagram"><ol>{value.split('\n').map((line,i)=><li key={i}>{line}</li>)}</ol></figure>;
 if(c.props.className==='language-check'){const [q,a]=value.split('\n---\n');return <div className="flow-check"><strong>{q}</strong><details><summary>{lang==='en'?'Reveal an explanation':'해설 열기'}</summary><p>{a}</p></details></div>}
 return <pre>{children}</pre>;
 }
 }}>{text}</Markdown>;
}
export function LearnFlow({id,lang}:{id:string;lang:Language}){
 const ko=lang==='ko-KR', page=flow.pages[id as keyof typeof flow.pages];
 const read=()=>new URLSearchParams(location.hash.split('?')[1]);
 const [params,setParams]=useState(read);
 useEffect(()=>{const update=()=>setParams(read());window.addEventListener('hashchange',update);return()=>window.removeEventListener('hashchange',update)},[]);
 const stage=params.get('stage')||page.stage, job=params.get('job')||'whole';
 useEffect(()=>{if(!params.size)return;const frame=requestAnimationFrame(()=>{document.querySelector(params.get('view')==='map'?'.mental-model':params.has('job')&&params.get('job')!=='whole'?'.job-walkthrough':'.stage-detail')?.scrollIntoView({block:'start'});});return()=>cancelAnimationFrame(frame)},[params]);
 const route=(extra:string)=>new URLSearchParams(extra).get('view')==='map'?`#/${lang}/learn/start-here`:mapTarget(lang,extra);
 const selected=flow.stages.find(s=>s.id===stage)||flow.stages[0];
 const jobData=flow.jobs.find(j=>j.id===job);
 const parts=flowText(lang,id).split('\n<!-- WHY -->\n');
 const chapters=parts[0].split('\n<!-- SCENE -->\n');
 return <section className="flow-learning">
 <nav className="where-strip" aria-label={ko?'전체 흐름에서 현재 위치':'Your place in the whole flow'}><a href={route(`stage=${stage}&view=map`)}>{ko?'전체 흐름':'Whole flow'}</a><span> › </span><span>{selected[lang]}</span><details><summary>{ko?'단계 선택':'Choose a stage'}</summary><div>{flow.stages.map(s=><a aria-current={stage===s.id?'step':undefined} key={s.id} href={route(`stage=${s.id}&job=${job}`)}>{s[lang]}</a>)}</div></details></nav>
 <WholeMap lang={lang} stage={stage} job={job} route={route} question={page[lang].question}/>
 <nav className="capability-nav" aria-label={ko?'무엇을 해볼까요?':'What would you like to do?'}><h2>{ko?'어느 경로를 따라가 볼까요?':'Which path would you like to follow?'}</h2><div>{flow.jobs.map(j=><a key={j.id} aria-current={job===j.id?'true':undefined} href={route(`job=${j.id}&stage=${j.stage}`)}>{j[lang].label}</a>)}</div></nav>
 {jobData&&<section className="job-walkthrough"><h3>{jobData[lang].request}</h3><figure className="teaching-diagram"><ol>{jobData[lang].steps.map(s=><li key={s}>{s}</li>)}</ol></figure><p>{jobData[lang].boundary}</p><a href={route(`stage=${stage}&view=map`)}>{ko?'전체 흐름으로 돌아가기':'Return to the whole flow'} ↑</a></section>}
 <section className="stage-detail" aria-live="polite"><h3>{selected[lang]} · {ko?'왜 이 단계가 있을까요?':'Why this stage?'}</h3><p>{selected.explanation[lang]}</p><div className="stage-context">{ko?'이전':'Before'}: {selected.before[lang]} → <strong>{selected[lang]}</strong> → {ko?'다음':'After'}: {selected.after[lang]}</div><div className="stage-links">{selected.terms.map(t=><Term key={t} id={t} lang={lang}>{glossary[t as TermId][lang].label}</Term>)}<a href={docHref(lang,selected.lesson)}>{ko?'이 단계 더 살펴보기':'Explore this stage'} →</a><a href={contextualHref(lang,`reference/item/${encodeURIComponent(selected.evidence[0])}`)}>{ko?'이 단계 구현 보기':'Implementation of this stage'} ↗</a></div></section>
 {chapters.map((text,i)=><section className="visual-scene" key={i}><LessonBody text={text} lang={lang}/></section>)}
 <details className="why-layer"><summary>{ko?'왜 이렇게 동작할까?':'Why does it work this way?'}</summary><div className="scope-legend">{Object.entries(flow.labels).map(([key,value])=><span key={key} className={`scope-${key}`}>{value[lang]}</span>)}</div><p>{flow.stateMeaning[lang]}</p><LessonBody text={parts[1]||''} lang={lang}/></details>
 <details className="flow-glossary"><summary>{ko?'흐름 속 용어 찾아보기':'Words in this flow'}</summary><p>{ko?'이름을 외우기보다 해당 단계로 돌아가 확인하세요.':'Use these to return to a stage, rather than memorize names.'}</p>{Object.entries(glossary).map(([key,g])=><Term key={key} id={key} lang={lang}>{g[lang].label}</Term>)}</details>
 </section>;
}

export function WholeMap({lang,stage='',job='whole',route,question}:{lang:Language;stage?:string;job?:string;route:(query:string)=>string;question:string}){const ko=lang==='ko-KR';return (
 <section className="mental-model" aria-label={ko?'원본과 기억·찾기 전체 지도':'Whole map: originals, remembering and finding'}>
 <h2>{question}</h2>
 <a className="outside-source" href={route(`stage=source&job=${job}`)}><strong>Google Drive / Notion / Files</strong><span>{ko?'Knowledge OS 바깥 · 원본은 여기 남습니다':'Outside Knowledge OS · originals stay here'}</span></a>
 <div className="map-arrow">↓ <small>{ko?'허용된 자료에서 근거를 가져옴':'Evidence from permitted material'}</small></div>
 <div className="context-boundary"><strong className="boundary-title">Knowledge OS</strong><div className="map-branches">
 {['save','find'].map(branch=><div key={branch} className={`map-branch ${job===branch?'chosen':''}`}><a className="branch-title" href={route(`job=${branch}`)}>{branch==='save'?(ko?'기억시키기':'Remember'):(ko?'찾아보기':'Find')}</a><span className="experience-badge target">{ko?'목표 경험':'Target experience'}</span>{(branch==='save'?['evidence','review','knowledge']:['retrieval','answer']).map(sid=>{const s=flow.stages.find(x=>x.id===sid)!;return <a className={`stage scope-${s.state} ${stage===sid?'active':''}`} key={sid} href={route(`stage=${sid}&job=${branch}`)}><span>{s[lang]}</span><small>{flow.labels[s.state as keyof typeof flow.labels][lang]}</small></a>})}</div>)}
 </div></div>
 <div className="map-user"><span>{ko?'나':'Me'}</span><span>↔</span><strong>Claude / GPT</strong><span>↔</span><Term id="mcp" lang={lang}>{ko?'MCP':'MCP'}</Term><span>↔ Knowledge OS</span></div>
 <p className="map-caption">{ko?'원본을 옮기는 대신, 근거와 검토한 내용을 연결합니다. 기억할 때는 후보를 검토하고, 찾을 때는 읽을 수 있는 근거를 돌려줍니다.':'Keep originals in place; connect evidence and reviewed statements. Remembering needs review; finding returns evidence you are allowed to read.'}</p>
 <p className="boundary-note">{ko?'“이거 기억해둬” 한마디로 끝나는 자동 제품은 목표 경험입니다. 현재는 읽기·제안 창구와 별도 검토 단계가 있으며, 답변 작성은 Claude/GPT 쪽에서 합니다.':'A complete one-message “remember this” product is a target. Today there are bounded read/proposal tools and a separate review step; Claude/GPT writes the answer.'}</p>
 </section>
);}
