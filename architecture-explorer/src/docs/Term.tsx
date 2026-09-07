import {termHref} from './ia';
import {useEffect, useId, useRef, useState, type ReactNode} from 'react';
import glossary from '../../content/flow/glossary.json';
import type {Language} from '../i18n';
export function Term({id,lang,children,href}:{id:string;lang:Language;children:ReactNode;href?:string}) {
 const [open,setOpen]=useState(false), uid=useId();
 const wrapper=useRef<HTMLSpanElement>(null), panel=useRef<HTMLSpanElement>(null);
 const timer=useRef<ReturnType<typeof setTimeout>|null>(null);
 const cancel=()=>{if(timer.current)clearTimeout(timer.current);timer.current=null;};
 const close=()=>{cancel();setOpen(false);};
 const later=()=>{if(!timer.current)timer.current=setTimeout(()=>{timer.current=null;setOpen(false)},350);};
 useEffect(()=>()=>cancel(),[]);
 useEffect(()=>{
  if(!open)return;
  // Keep the corridor between trigger and panel interactive, including a small
  // diagonal margin. Crossing whitespace must not dismiss a destination link.
  const move=(e:PointerEvent)=>{
   if(e.pointerType!=='mouse')return;
   const a=wrapper.current?.getBoundingClientRect(),b=panel.current?.getBoundingClientRect();
   if(!a||!b)return;
   const within=e.clientX>=Math.min(a.left,b.left)-12&&e.clientX<=Math.max(a.right,b.right)+12&&e.clientY>=Math.min(a.top,b.top)-12&&e.clientY<=Math.max(a.bottom,b.bottom)+12;
   if(within)cancel();else if(!wrapper.current?.contains(document.activeElement))later();
  };
  const outside=(e:PointerEvent)=>{if(!wrapper.current?.contains(e.target as Node))close();};
  document.addEventListener('pointermove',move);document.addEventListener('pointerdown',outside);
  return()=>{document.removeEventListener('pointermove',move);document.removeEventListener('pointerdown',outside);cancel();};
 },[open]);
 const g=glossary[id as keyof typeof glossary];if(!g)return <span>{children}</span>;
 return <span className="learn-term" ref={wrapper} onMouseEnter={()=>{cancel();setOpen(true)}} onBlur={e=>{if(!e.currentTarget.contains(e.relatedTarget))later()}} onKeyDown={e=>{if(e.key==='Escape'){e.stopPropagation();close()}}}>
  <button type="button" aria-expanded={open} aria-controls={uid} onFocus={()=>{cancel();setOpen(true)}} onClick={()=>{cancel();setOpen(true)}}>{children} <span aria-hidden="true">ⓘ</span></button>
  {open&&<span ref={panel} className="learn-definition" role="region" aria-label={g.name} id={uid} onMouseEnter={cancel} onFocus={cancel}>
   <button type="button" onClick={close} aria-label={lang==='en'?'Close definition':'용어 설명 닫기'}>×</button><strong>{g.name}</strong><span>{g[lang].definition}</span><small>{g[lang].example}</small>
   <a href={href||termHref(lang,id)} onClick={close}>{lang==='en'?'Learn in the flow →':'흐름에서 자세히 배우기 →'}</a>
  </span>}
 </span>;
}
