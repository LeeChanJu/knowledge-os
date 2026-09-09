export type Axis = 'runtime' | 'engineering';
export type AtlasState = {axis:Axis;node:string;root:string;open:string[];returnTo:string};
export function atlasState():AtlasState {
 const [path,query='']=location.hash.split('?'),q=new URLSearchParams(query);
 return {axis:path.endsWith('/engineering')?'engineering':'runtime',node:q.get('node')||'',root:q.get('root')||'',open:(q.get('open')||'').split(',').filter(Boolean),returnTo:q.get('returnTo')||''};
}
export function atlasHref(lang:string,s:AtlasState){
 const q=new URLSearchParams();if(s.node)q.set('node',s.node);if(s.root)q.set('root',s.root);if(s.open.length)q.set('open',s.open.join(','));if(s.returnTo)q.set('returnTo',s.returnTo);
 return `#/${lang}/${s.axis}${q.size?'?'+q:''}`;
}
export function validReturn(value:string){return /^(runtime|engineering)\?/.test(value)&&!/[#<>]/.test(value);}
export function atlasReturnHref(lang:string){const v=new URLSearchParams(location.hash.split('?')[1]).get('atlas');return v&&validReturn(v)?`#/${lang}/${v}`:null;}
