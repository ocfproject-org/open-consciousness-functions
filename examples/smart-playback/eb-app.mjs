import {SmartPlayer,nativeStream} from './eb-player.mjs';
import {plan,virtualTime,availableChoices,defaultChoice,isPlainCommandPreview} from './eb-model.mjs';
const $=id=>document.getElementById(id), ids=['preparation','relaxation','resonant-tuning','energy-ball','affirmation','return'];
const titles={lesson:'Private modular Energy Ball audition',awake:'Quiet Focus awake companion'};
const recommendations={lesson:{preparation:'short',relaxation:'short','resonant-tuning':'reminder',affirmation:'reminder'},awake:{preparation:'short',relaxation:'short','resonant-tuning':'reminder','energy-ball':'reminder',affirmation:'reminder',return:'short'}};
// Additional command auditions are published only with an exact private manifest.
const commandPreviews={
 focus:['OCF-FND-002','Focus'],
 'quick-recharge':['OCF-FND-003','Quick Recharge'],
 'sleep-easy':['OCF-SLP-005','Sleep Easy'],
};
function registerCommandPreviews(manifests){
 for(const [key,[functionId,title]] of Object.entries(commandPreviews)){
   const m=manifests[key];
   if(m?.identity?.kind!=='private-review'||m.identity.function!==functionId
      ||m.identity.session!==functionId.toLowerCase())continue;
   titles[key]=title;
   recommendations[key]={'resonant-tuning':'reminder'};
   $('which').append(new Option(title,key));
 }
}
const STORAGE='ocf.private.smart-playback.defaults.v1';
const modes=['standard','full','experienced','advanced'];
const modeLabels={standard:'Standard',full:'Full Guidance',experienced:'Experienced',advanced:'Advanced'};
const full=()=>Object.fromEntries(ids.map(id=>[id,player.m?defaultChoice(player.m,id):'full']));
const plain=()=>isPlainCommandPreview(player.m);
const initialPreset=()=>plain()?'standard':'full';
const standard=()=>normalized({'resonant-tuning':'off',affirmation:'off'});
const initialToggles=()=>plain()?standard():full();
const dialog=$('settings'), gear=$('settings-open'), seek=$('seek');
let scrubbing=false, bookmarkPlan=null, bookmarkJump=0;
const bookmarkNames={
 'short-box':'Transmutation Box',affirmation:'Affirmation','short-relaxation':'Relaxation',
 'tuning-off':'Resonant Tuning','awake-reminder':'Energy Ball: inflate',
 'awake-deflate':'Energy Ball: deflate','awake-box-short':'Transmutation Box','awake-relax-short':'Relaxation','awake-tuning-off':'Resonant Tuning','awake-affirmation':'Affirmation','awake-waking':'Waking return','post-sleep-short-return':'Waking return from Focus 10'
};
const player=new SmartPlayer($('source'),$('insert'),message=>{announce(message);if(ready)renderInterruption();});window.smart=player;
let all=null,ready=false,which='lesson',supported=[],draftPreset='full',appliedPreset='full',appliedToggles={},usingDefaults=false;
const fmt=s=>Math.floor(s/60)+':'+(s%60).toFixed(1).padStart(4,'0');
function buildBookmarks(){
 const list=$('bookmark-list'), section=$('smart-bookmarks');
 const activePlan=player.p;
 const currentWindows=player.m.windows.filter(w=>w.approved&&Object.hasOwn(bookmarkNames,w.id));
 if(bookmarkPlan===activePlan)return;
 bookmarkPlan=activePlan;
 const marks=currentWindows.map(w=>({
   id:w.id,label:bookmarkNames[w.id],
   start:activePlan.segments.find(s=>s.window?.id===w.id)?.start??virtualTime(activePlan,w.start-w.fade),
 }));
 if(player.m.identity.session==='quiet-focus'){
   const names={'awake-count-up':'Focus 10 → 11 sweep','awake-count-down':'Focus 11 → 10 sweep'};
   for(const w of player.m.timelines.dspWindows)if(Object.hasOwn(names,w.id))
      marks.push({id:w.id,label:names[w.id],start:virtualTime(activePlan,w.start)});
 }
 const count=player.m.events.find(e=>e.role==='one-to-ten');
 if(count)marks.push({id:'focus-ten-count',label:'Count into Focus 10',start:virtualTime(activePlan,count.start)});
 const guided=player.m.events.find(e=>e.id==='guided-practice.detailed');
 if(guided)marks.push({id:'guided-energy-ball',label:'Energy Ball practice',start:virtualTime(activePlan,guided.start)});
 const nodes=marks.sort((a,b)=>a.start-b.start).map(w=>{
   const position=Math.max(0,w.start-5);
   const item=document.createElement('li'), button=document.createElement('button');
   button.type='button';button.dataset.bookmark=w.id;
   button.textContent=w.label+' · '+fmt(position);
   button.setAttribute('aria-label','Jump before '+w.label+' at '+fmt(position));
   button.onclick=async()=>{
      if(!ready||player.p!==activePlan)return;
      const jump=++bookmarkJump;
      scrubbing=false;
      try{
         await player.seek(position);
         if(jump===bookmarkJump&&ready&&player.p===activePlan){
            update();
            if(!player.running&&!player.interruption)announce('At '+fmt(position)+', before '+w.label+'. Press Play when ready.');
         }
      }catch(error){
         if(jump===bookmarkJump&&ready&&player.p===activePlan&&!isCancellation(error)&&!player.interruption)announce('Could not jump to that section. Try again.');
      }
   };
   item.append(button);return item;
 });
 list.replaceChildren(...nodes);section.hidden=!nodes.length;
}
function update(){
 if(!ready||!player.p)return;
 buildBookmarks();
 renderInterruption();
 seek.max=player.p.duration;
 if(!scrubbing)seek.value=player.current();
 const time=Number(seek.value);
 seek.setAttribute('aria-valuetext',fmt(time)+' of '+fmt(player.p.duration));
 $('timing').textContent='Total '+fmt(player.p.duration)+' · Remaining '+fmt(Math.max(0,player.p.duration-time));
}
function readDefaults(){
 try{
   const record=JSON.parse(localStorage.getItem(STORAGE));
   const toggles=Object.fromEntries(ids.filter(id=>['string','boolean'].includes(typeof record?.[id])).map(id=>[id,record[id]]));
   const presets=Object.fromEntries(Object.keys(titles).filter(k=>modes.includes(record?.presets?.[k])&&record.presets[k]!=='standard').map(k=>[k,record.presets[k]]));
   return {toggles,presets,commandDefaults:record?.commandDefaults??{}};
 }catch{return {toggles:{},presets:{},commandDefaults:{}};}
}
function announce(message){$('status').textContent=message;}
function isCancellation(error){return error?.name==='AbortError'||/cancelled|canceled/i.test(error?.message||'');}
function normalized(toggles){
 return Object.fromEntries(ids.map(k=>{
   const values=availableChoices(player.m,k), original=defaultChoice(player.m,k);
   const legacy={'affirmation':'full','resonant-tuning':'off','energy-ball':'reminder'};
   let wanted=toggles[k];
   if(typeof wanted==='boolean'){
      wanted=wanted?(values.includes('short')?'short':legacy[k]):original;
   }
   return [k,supported.includes(k)&&values.includes(wanted)?wanted:original];
 }));
}
function recommended(){return normalized(recommendations[which]);}
function same(a,b){return ids.every(id=>a[id]===b[id]);}
function defaultMode(toggles,preferred){
 if(preferred==='advanced')return preferred;
 if(preferred==='experienced'&&same(toggles,recommended()))return preferred;
 if(plain()&&same(toggles,standard()))return 'standard';
 if(same(toggles,full()))return 'full';
 return same(toggles,recommended())?'experienced':'advanced';
}
function setButtons(preset){
 draftPreset=preset;
 for(const id of modes)$(id).setAttribute('aria-pressed',String(id===preset));
 $('advanced-options').hidden=preset!=='advanced';
 $('settings-selection').textContent='Selected in this dialog: '+modeLabels[preset];
}
function readDraft(){return normalized(Object.fromEntries(ids.map(id=>[id,$(id).value])));}
function writeDraft(toggles,preset){
 for(const id of ids)$(id).value=toggles[id];
 setButtons(preset);
}
function summarize(){
 const details=plain()?' · Resonant Tuning: '+appliedToggles['resonant-tuning']+' · Main affirmation: '+appliedToggles.affirmation:'';
 $('guidance-summary').textContent='Guidance: '+modeLabels[appliedPreset]+(usingDefaults?' · Saved defaults':'')+details;
}
function renderInterruption(){
 const interruption=player.interruption;
 const visible=Boolean(ready&&interruption);
 const notice=$('fallback-notice'), message=$('fallback-message'), retry=$('retry-guidance');
 notice.hidden=!visible;
 $('play').disabled=!ready||visible;
 if(!visible){message.textContent='';retry.disabled=false;return;}
 const newMessage='Playback paused. '+modeLabels[appliedPreset]+' is still selected. '+(interruption.reason?interruption.reason+'. ':'')+'Retry this selection or choose Full Guidance.';
 if(message.textContent!==newMessage)message.textContent=newMessage;
 retry.textContent='Retry '+modeLabels[appliedPreset];
 $('use-full').hidden=appliedPreset==='full';
}
function apply(toggles,preset,saved=false){
 const next=normalized(toggles);
 appliedPreset=preset;appliedToggles=next;usingDefaults=saved;
 if(!same(player.toggles,next)||player.interruption)player.setProfile(same(next,full())?'full':'B',next);
 summarize();update();
}
gear.onclick=()=>{
 if(!ready)return;
 $('saving-status').textContent='';
 writeDraft(appliedToggles,appliedPreset);
 dialog.showModal();
 $(appliedPreset).focus();
};
dialog.addEventListener('close',()=>{if(!gear.disabled)gear.focus();});
$('cancel-settings').onclick=()=>dialog.close();
$('settings-form').onsubmit=e=>{e.preventDefault();if(ready){apply(readDraft(),draftPreset);dialog.close();}};
$('save-defaults').onclick=()=>{
 if(!ready)return;
 const draft=readDraft(), current=readDefaults();
 const choices=Object.fromEntries(supported.map(id=>[id,draft[id]]));
 const merged=plain()
   ?{...current.toggles,presets:current.presets,commandDefaults:{...current.commandDefaults,[which]:{choices,preset:draftPreset}}}
   :{...current.toggles,...choices,presets:{...current.presets,[which]:draftPreset},commandDefaults:current.commandDefaults};
 try{localStorage.setItem(STORAGE,JSON.stringify(merged));}
 catch{$('saving-status').textContent='This browser could not save your defaults. You can still apply choices to this session.';return;}
 apply(draft,draftPreset,true);dialog.close();announce('Smart Playback defaults saved on this browser.');
};
$('clear-defaults').onclick=()=>{
 if(!ready)return;
 try{localStorage.removeItem(STORAGE);}
 catch{$('saving-status').textContent='This browser could not remove your saved defaults.';return;}
 const preset=initialPreset();apply(initialToggles(),preset);dialog.close();announce('Smart Playback defaults cleared. '+modeLabels[preset]+' selected.');
};
for(const preset of modes)$(preset).onclick=()=>{
 if(preset==='advanced'){setButtons(preset);return;}
 writeDraft(preset==='standard'?standard():preset==='full'?full():recommended(),preset);
};
$('retry-guidance').onclick=async()=>{
 if(!ready||!player.interruption)return;
 const retry=$('retry-guidance');retry.disabled=true;
 try{await player.play();}finally{retry.disabled=false;update();}
};
$('use-full').onclick=()=>{
 if(!ready||!player.interruption)return;
 apply(full(),'full');
 announce('Full Guidance selected. Press Play when ready.');
 $('play').focus();
};
$('play').onclick=()=>{if(ready&&!player.interruption)player.play();};$('pause').onclick=()=>player.pause();
seek.addEventListener('pointerdown',()=>{scrubbing=true;});
for(const event of ['pointercancel','blur'])seek.addEventListener(event,()=>{scrubbing=false;});
seek.addEventListener('keyup',()=>{scrubbing=false;});
seek.addEventListener('input',()=>{scrubbing=true;update();});
seek.addEventListener('change',()=>{
 const target=Number(seek.value);scrubbing=false;
 if(ready)player.seek(target).catch(e=>{if(!isCancellation(e)&&!player.interruption)announce('Could not change position. Try again.');});
});
$('resume').onclick=()=>{
 if(!ready)return;
 const restored=player.restore();
 if(restored){
   const next=normalized(player.toggles);
   if(!same(next,appliedToggles)){appliedPreset=defaultMode(next);usingDefaults=false;}
   appliedToggles=next;summarize();
 }
 announce(restored?'Matching saved position restored. Press Play.':'No matching saved position.');update();
};
async function show(key){
 ready=false;scrubbing=false;bookmarkPlan=null;bookmarkJump++;$('smart-bookmarks').hidden=true;$('which').disabled=true;$('play').disabled=true;gear.disabled=true;player.pause();renderInterruption();
 for(const id of ['seek','resume'])$(id).disabled=true;
 $('download').removeAttribute('href');
 which=key;$('title').textContent=titles[key];$('policy').hidden=true;$('lesson-proof').hidden=key!=='lesson';
 try{
   const m=all[key];if(!m||m.identity.kind!=='private-review')throw Error('Not a private audition');
   await player.load(m,{privateReview:true,title:titles[key]});
   player.toggles=full();
   supported=ids.filter(id=>m.windows.some(w=>w.approved&&w.control===id));
   $('policy').hidden=key!=='lesson';
   $('policy').textContent=supported.includes('return')
     ?'Both returns keep the full Focus 20 to Focus 10 countdown. Short names C1, cues the thought of One, and allows 30 seconds before the same closer.'
     :'This recording keeps its full waking return.';
   for(const id of ids){
     const choices=availableChoices(m,id);
     if(choices.includes('reminder')){
       const names={off:'Off',reminder:'Reminder',full:'Full'};
       $(id).replaceChildren(...['off','reminder','full'].filter(x=>choices.includes(x)).map(x=>new Option(names[x],x)));
     }else{
       const titles={preparation:['Full','Short reminder'],relaxation:['Full','Short: Plus Relax'],return:['Full','Short return']};
       const names=titles[id]||['Full','Short'];
       $(id).replaceChildren(...choices.map(x=>new Option(names[x==='short'?1:0],x)));
     }
     $(id).disabled=!supported.includes(id);
     $(id).closest('label').hidden=$(id).disabled;
   }
   $('notice').textContent=m.notice;
   const path=plain()?nativeStream(m,plan(m,'B',standard(),false,true),standard()).path:m.assets[0].path;
   $('download').textContent=plain()?'Download Standard audition':'Download original full baseline';
   $('download').href=new URL(path,import.meta.url).href;
   ready=true;for(const id of ['seek','play','resume'])$(id).disabled=false;gear.disabled=!supported.length;
   $('standard').hidden=!plain();
   $('full-description').textContent=plain()?'Play Full Resonant Tuning. The affirmation stays off unless you choose it.':'Play the complete original session.';
   const saved=readDefaults(), entry=plain()?saved.commandDefaults[key]:null;
   const choices=plain()?(entry?.choices??{}):saved.toggles;
   const hasSaved=supported.some(id=>Object.hasOwn(choices,id));
   const defaults=normalized({...initialToggles(),...choices});
   apply(defaults,hasSaved?defaultMode(defaults,plain()?entry?.preset:saved.presets[key]):initialPreset(),hasSaved);
   player.hasInteracted=false;
 }catch(e){announce('Unavailable: '+e.message);}
 finally{$('which').disabled=false;}
}
$('which').onchange=()=>{if(all)show($('which').value);};
try{
 const r=await fetch('./eb-official.json',{cache:'no-store'});
 if(!r.ok)throw Error('Private manifests unavailable');
 all=await r.json();
 registerCommandPreviews(all);
 const requested=location.hash.slice(1);
 const first=requested==='quiet-focus'?'awake'
   :Object.hasOwn(commandPreviews,requested)&&Object.hasOwn(titles,requested)?requested:'lesson';
 $('which').value=first;
 await show(first);
}catch(e){announce('Unavailable: '+e.message);$('which').disabled=true;}
const timer=setInterval(update,200);window.addEventListener('pagehide',()=>clearInterval(timer));
