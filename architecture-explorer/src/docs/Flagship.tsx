import executionRecordUrl from "../../verification/current-head-regressions.json?url";
import learning from "../../data/learning.json";
import { Children, isValidElement, type ReactNode } from 'react';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import metadata from '../../content/flagships.json';
import {githubLink} from './helpers';
import type {Language} from '../i18n';
const texts=import.meta.glob('../../content/{en,ko-KR}/*.md',{query:'?raw',import:'default',eager:true}) as Record<string,string>;
export const isFlagship=(id:string)=>id in metadata.pages;
export const flagshipText=(lang:Language,id:string)=>texts[`../../content/${lang}/${id}.md`]||'';
export function Flagship({id,lang,title}:{id:string;lang:Language;title:string}){
 const p=metadata.pages[id as keyof typeof metadata.pages], ko=lang==='ko-KR';
 const href=(path:string)=>`#/${lang}/${path}`;
 const headings=[...flagshipText(lang,id).matchAll(/^## (.+) \{#([a-z-]+)\}$/gm)];
 const label=(en:string,kr:string)=>ko?kr:en;
 const block=(className:string|undefined,children:ReactNode)=>{
   const text=String(children).trim();
   if(className==='language-question'){
     const [q,a]=text.split('\n---\n');
     return <div className="comprehension"><h3>{q}</h3><details><summary>{label('Reveal a reasoned answer','해설 열어 보기')}</summary><p>{a}</p></details></div>;
   }
   if(className==='language-flow')return <figure className="lesson-diagram"><figcaption>{label('Teaching diagram · responsibilities, not automatic execution','학습 그림 · 자동 실행이 아닌 책임의 연결')}</figcaption><ol>{text.split('\n').map((line,i)=>{const [name,...body]=line.split(' | ');return <li key={i}><span className="step-index">{i+1}</span><div><strong>{name}</strong><p>{body.join(' | ')}</p></div></li>})}</ol></figure>;
   return <pre><code className={className}>{children}</code></pre>;
 };
 return <>
 <main className="docs-article flagship" key={`${lang}/${id}`}>
  <div className="eyebrow">{label('LEARN · FOUR FLAGSHIP LESSONS','LEARN · 대표 학습 문서 4편')}</div><h1>{title}</h1>
  <nav className="flagship-prerequisites" aria-label={label('Prerequisites','먼저 읽기')}><strong>{label('Before this lesson: ','먼저 읽기: ')}</strong>{p.prerequisites.length?p.prerequisites.map(x=><a key={x} href={href('learn/'+x)}>{label(({ 'start-here':'Start Here','source-of-truth':'Source of Truth vs Context','document-journey':'One document journey'} as Record<string,string>)[x],({'start-here':'왜 Knowledge OS인가','source-of-truth':'원본과 맥락','document-journey':'문서 하나의 여정'} as Record<string,string>)[x])}</a>):label('No prior technical knowledge needed.','기술 배경지식이 없어도 됩니다.')}</nav>
  <Markdown remarkPlugins={[remarkGfm]} components={{
    h2:({children})=>{const raw=Children.toArray(children).join('');const match=raw.match(/^(.*) \{#([a-z-]+)\}$/);return <h2 id={match?.[2]}>{match?.[1]||children}</h2>},
    pre:({children})=>{const child=Children.toArray(children)[0];if(isValidElement<{className?:string;children?:ReactNode}>(child))return block(child.props.className,child.props.children);return <pre>{children}</pre>},
    a:({href,children})=><a href={href}>{children}</a>,
  }}>{flagshipText(lang,id)}</Markdown>
  <section className="conceptual-references" id="conceptual-references"><h2>{label('Conceptual references','개념 참고자료')}</h2><p>{label('These explain ideas and teaching methods. They are not evidence that Knowledge OS implements another product’s capabilities.','개념과 설명 방식을 위한 참고자료입니다. 다른 제품의 기능이 Knowledge OS에 구현됐다는 근거가 아닙니다.')}</p><ul>{p.conceptualSources.map(key=>{const s=metadata.sources[key as keyof typeof metadata.sources];return <li key={key}><a href={s.url} target="_blank" rel="noreferrer">{s.title} ↗</a></li>})}</ul></section>
  <section className="implementation-evidence" id="implementation-evidence"><h2>{label('Knowledge OS implementation evidence','Knowledge OS 구현 근거')}</h2><p>{label('Repository evidence identifies the implementation, tests and accepted contracts. A test link is not a passing result. F1/F2 have scoped executed evidence; F3–F8 and release acceptance remain open.','저장소 근거는 구현·테스트·승인된 계약을 식별합니다. 테스트 링크 자체가 통과 결과는 아닙니다. F1/F2에는 한정된 실행 근거가 있으며 F3–F8과 출시 관문은 열려 있습니다.')}</p>
  <p className="evidence-revision-note">{label("GitHub links below show the public evidence snapshot ","아래 GitHub 링크는 공개 근거 스냅샷 ")}{learning.github.revision.slice(0,12)}{label(". Current-HEAD F1/F2 execution is recorded separately; these links do not claim that the public snapshot contains the latest local code.","을 보여줍니다. 현재 HEAD의 F1/F2 실행은 별도 기록이며, 공개 스냅샷에 최신 로컬 코드가 포함됐다는 뜻은 아닙니다.")} <a href={executionRecordUrl} target="_blank" rel="noreferrer">{label("Executed regression record (JSON)","회귀 실행 기록 (JSON)")} ↗</a></p><div className="evidence-grid">{p.referenceIds.map(ref=><div className="evidence-item" key={ref}><a className="evidence-card" href={href('reference/item/'+encodeURIComponent(ref))}><span>{label(ref.includes('tests/')?'Test':ref.includes('src/')?'Implementation':'Contract / ADR / migration',ref.includes('tests/')?'테스트':ref.includes('src/')?'구현':'계약 / ADR / 마이그레이션')}</span><code>{ref.slice(4)}</code></a><a className="file-action" target="_blank" rel="noreferrer" href={githubLink(ref)}>{label('Pinned evidence on GitHub','고정된 GitHub 근거')} ↗</a></div>)}</div>
  <div className="related-concepts">{p.nodeIds.map(node=><a key={node} href={href('explore/node/'+node)}>{label('Explore','구조 살펴보기')}: {node} ↗</a>)}{['F1','F2','F5','release-gate'].map(claim=><a key={claim} href={href('reference/item/'+claim)}>{claim} · {label('verification scope','검증 범위')}</a>)}</div></section>
  <footer className="lesson-finish"><p>{label(`Flagship lesson ${Object.keys(metadata.pages).indexOf(id)+1} of 4. Other lessons remain the previous edition pending review.`,`대표 수업 ${Object.keys(metadata.pages).indexOf(id)+1}/4. 나머지 수업은 검토 전의 기존 문서입니다.`)}</p>{p.next?<a href={href('learn/'+p.next)}>{label('Next flagship lesson','다음 대표 수업')} →</a>:<a href={href('explore/node/ontology')}>{label('Locate this concept in Explore','Explore에서 이 개념 찾아보기')} →</a>}</footer>
 </main>
 <aside className="article-toc"><span className="eyebrow">{label('On this page','이 페이지에서')}</span>{headings.map((h)=><button key={h[2]} onClick={()=>document.getElementById(h[2])?.scrollIntoView({behavior:'smooth'})}>{h[1]}</button>)}<button onClick={()=>document.getElementById('conceptual-references')?.scrollIntoView()}>{label('Conceptual references','개념 참고자료')}</button><button onClick={()=>document.getElementById('implementation-evidence')?.scrollIntoView()}>{label('Implementation evidence','구현 근거')}</button><a className="toc-explore" href={href('explore/node/'+p.nodeIds[0])}>Explore ↗</a></aside>
 </>;
}
