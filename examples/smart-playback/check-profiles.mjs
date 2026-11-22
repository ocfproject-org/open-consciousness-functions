import {readFileSync} from 'node:fs';
import {strict as assert} from 'node:assert';
import {validate,plan,availableChoices} from './eb-model.mjs';
import {nativeStream} from './eb-player.mjs';
const all=JSON.parse(readFileSync(process.argv[2]));
let count=0;
for(const m of Object.values(all)){
 validate(m);
 const controls=[...new Set(m.windows.filter(w=>w.approved).map(w=>w.control))];
 const allCombos=(i=0,toggles={},expected='')=>{
   if(i<controls.length){
     const id=controls[i],values=availableChoices(m,id);
     return values.forEach((choice,ordinal)=>allCombos(i+1,{...toggles,[id]:choice},expected+ordinal));
   }
   count++;
   const p=plan(m,'B',toggles,false,true),result=nativeStream(m,p,toggles);
   const empty=/^0+$/.test(expected);
   assert.equal(result.edited,!empty);
   assert.equal(result.path,empty?m.assets[0].path:`media/native-${m.identity.session}-${expected}.wav`);
 };
 allCombos();
 // The measured insertion for a legacy `true` can be any nondefault ordinal.
 for(const id of controls){
   const legacy=plan(m,'B',{[id]:true},false,true);
   const modern=availableChoices(m,id).find(choice=>{
     const p=plan(m,'B',{[id]:choice},false,true);
     return JSON.stringify(p)===JSON.stringify(legacy);
   });
   assert(modern,id);
   assert.deepEqual(nativeStream(m,legacy,{[id]:true}),nativeStream(m,legacy,{[id]:modern}));
 }
 assert.throws(()=>nativeStream(m,{segments:[{asset:'not-verifed',window:m.windows[0]}]}),/No verified audio/);
}
assert(count>0);
console.log('Exact profile mappings, legacy booleans and unknown assets verified.');
