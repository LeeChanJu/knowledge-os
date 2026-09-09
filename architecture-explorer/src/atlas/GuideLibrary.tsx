import {useState} from 'react';
import learning from '../../data/learning.json';
import model from '../../content/atlas/model.json';
import {integration,guideHref} from './integration';
import type {Language} from '../i18n';
export function GuideLibrary({lang}:{lang:Language}){
 const [query,setQuery]=useState(''),[axis,setAxis]=useState('');
 const docs=learning.documents[lang] as Record<string,{title:string}>;
 const entries=integration.entries.filter(e=>e.resolution==='integrated'&&(!axis||e.location.axis===axis)&&([e.id,docs[e.id].title,...integration.entries.filter(x=>x.canonicalId===e.id).map(x=>docs[x.id].title)].join(' ').toLowerCase().includes(query.toLowerCase())));
 return <section className="guide-library"><h2>{lang==='en'?'Guides attached to the maps':'지도에 연결된 상세 문서'}</h2><p>{lang==='en'?'68 canonical guides. Seven overlapping documents are merged; two old introductions lead to the map. Originals remain in the archive.':'대표 문서 68개입니다. 중복 7개는 병합했고, 예전 안내 2개는 지도로 연결합니다. 이전 본문은 보관 화면에 남아 있습니다.'}</p><label>{lang==='en'?'Find a concept':'개념 찾기'}<input value={query} onChange={e=>setQuery(e.target.value)}/></label><label>{lang==='en'?'Map':'지도'}<select aria-label={lang==='en'?'Map':'지도'} value={axis} onChange={e=>setAxis(e.target.value)}><option value="">{lang==='en'?'Both maps':'두 지도 모두'}</option><option value="runtime">Runtime</option><option value="engineering">Engineering</option></select></label><div className="guide-library-results">{entries.map(e=><article key={e.id}><a href={guideHref(lang,e.id)}>{docs[e.id].title}</a><small>{e.location.axis} · {model.nodes.find(n=>n.id===e.location.node)!.labels[lang]}</small></article>)}</div>{!entries.length&&<p role="status">{lang==='en'?'No guides match.':'일치하는 문서가 없습니다.'}</p>}</section>;
}
