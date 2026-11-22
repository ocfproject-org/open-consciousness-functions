import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
const root=process.argv[2];
const {validate,plan,availableChoices}=await import(pathToFileURL(path.join(root,'eb-model.mjs')));
const result={};
for(const m of Object.values(JSON.parse(fs.readFileSync(path.join(root,'eb-official.json'))))){
 validate(m);
 const ids=[...new Set(m.windows.filter(w=>w.approved).map(w=>w.control))];
 const rows=ids.reduce((a,id)=>a.flatMap(([key,z])=>availableChoices(m,id).map((v,i)=>[key+i,{...z,[id]:v}])),[['',{}]]);
 for(const [key,z] of rows){
  const p=plan(m,'B',z,false,true);
  if(!p.segments.some(s=>s.window))continue;
  const assets=Object.fromEntries(m.assets.map(a=>[a.id,a.path.split('/').at(-1)]));
  result['native-'+m.identity.session+'-'+key+'.wav']=p.segments.map(s=>({
    from:s.from,start:s.start,end:s.end,file:assets[s.asset],
    correlation:s.window?.correlation??null,
  }));
 }
}
console.log(JSON.stringify(result));
