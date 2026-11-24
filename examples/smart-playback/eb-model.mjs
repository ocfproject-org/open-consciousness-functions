export const SCHEMA='ocf.smart-playback/1';
const fail=m=>{throw Error(m);};
const finite=x=>typeof x==='number'&&Number.isFinite(x);
const exact=(v,keys)=>{if(!v||Array.isArray(v)||Object.keys(v).sort().join('|')!==keys.sort().join('|'))fail('Unexpected manifest fields');};
const variantControls={'affirmation':['off','reminder','full'],'resonant-tuning':['off','reminder','full'],'energy-ball':['off','reminder','full']};
const plainCommandIds=new Set(['OCF-FND-002','OCF-FND-003','OCF-SLP-005']);
export function isPlainCommandPreview(m){
 const i=m?.identity;
 return i?.kind==='private-review'&&plainCommandIds.has(i.function)&&i.session===i.function.toLowerCase()
   &&i.returnPolicy==='sleep'&&!m.events.some(e=>e.role==='energy-ball')
   &&m.windows.some(w=>w.approved&&w.control==='affirmation'&&w.originalChoice==='off');
}
export function isRoutineCommandPreview(m){
 const i=m?.identity;
 return i?.kind==='private-review'&&/^OCF-[A-Z]{3}-[0-9]{3}$/.test(i.function)
   &&i.function!=='OCF-EXP-007'&&i.session===`routine-${i.function.toLowerCase()}-${i.edition}`
   &&/^[a-f0-9]{12}$/.test(i.edition)
   &&Array.isArray(m.events)&&m.events.some(e=>e.role==='installation'&&e.required&&e.speech)
   &&m.events.some(e=>e.role==='one-to-ten'&&e.required&&e.id==='focus-ten.begin')
   &&!m.events.some(e=>Object.hasOwn(variantControls,e.role));
}
function routineWindow(m,w){
 if(!isRoutineCommandPreview(m)||w.originalChoice!=='off'||w.inState!=='focus-10'
    ||w.outState!=='focus-10'||w.required?.length!==0)return false;
 const before=m.events.find(e=>e.id===w.boundaries?.lastRetained);
 const after=m.events.find(e=>e.id===w.boundaries?.firstResumed);
 return before?.role==='relaxation'&&before.speech
   &&(before.required||m.windows.some(r=>r.control==='relaxation'&&r.approved&&r.start<=before.start&&r.end>=before.end))
   &&after?.id==='focus-ten.begin'&&after.required&&after.speech
   &&before.end<=w.start-w.fade&&w.end+w.fade<=after.start
   &&!m.events.some(e=>e.start<w.end+w.fade&&e.end>w.start-w.fade);
}
const baseChoice=w=>w.originalChoice||'full';
export function availableChoices(m,control){
 const rows=m.windows.filter(w=>w.control===control&&w.approved);
 if(!rows.length)return ['full'];
 const values=w=>w.variants?[baseChoice(w),...Object.keys(w.variants)]:['full','short'];
 return values(rows[0]).filter(choice=>rows.every(w=>values(w).includes(choice)));
}
export function defaultChoice(m,control){return baseChoice(m.windows.find(w=>w.control===control&&w.approved)||{});}
function alternative(w,selected){
 if(selected===true)return {insert:w.insert,correlation:w.correlation};
 if(typeof selected!=='string'||selected===baseChoice(w))return null;
 if(w.variants)return Object.hasOwn(w.variants,selected)?w.variants[selected]:null;
 return selected==='short'?{insert:w.insert,correlation:w.correlation}:null;
}
export function validate(m){
 exact(m,['schema','identity','assets','events','windows','approvals','profiles','notice','timelines']);
 if(m.schema!==SCHEMA)fail('Unsupported manifest');
 exact(m.identity,['function','session','language','voice','edition','source','duration','dsp','mix','kind','returnPolicy']);
 if(!['normal-waking','sleep','preparation-learning'].includes(m.identity.returnPolicy))fail('Unknown return policy');
 if(!['public-recording','mechanical-fixture','private-review'].includes(m.identity.kind))fail('Unknown evidence class');
 for(const key of ['function','session','language','voice','edition','source','dsp','mix'])if(typeof m.identity[key]!=='string'||!m.identity[key])fail('Missing identity');
 if(!finite(m.identity.duration)||m.identity.duration<=0)fail('Invalid duration');
 exact(m.approvals,['mechanical','editorial','listening']);for(const v of Object.values(m.approvals))if(!['verified','pending','fixture-only'].includes(v))fail('Invalid approval');
 exact(m.profiles,['full','A','B']);if(typeof m.notice!=='string'||m.notice.length>2000)fail('Invalid notice');
 if(!Array.isArray(m.assets)||!m.assets.length||m.assets.length>(m.identity.kind==='private-review'?14:10))fail('Invalid assets');
 const assets=new Map();
 for(const a of m.assets){exact(a,['id','path','sha256','bytes','duration','channels','sampleRate','compatibility','content','guards']);if(assets.has(a.id)||typeof a.id!=='string'||!/^[a-z0-9-]+$/.test(a.id)||!/^media\/[a-z0-9.-]+$/.test(a.path)||!/^[a-f0-9]{64}$/.test(a.sha256)||!Number.isSafeInteger(a.bytes)||a.bytes<=0||!finite(a.duration)||a.duration<=0||a.channels!==2||!Number.isSafeInteger(a.sampleRate)||a.sampleRate<8000||a.sampleRate>192000)fail('Invalid asset identity');exact(a.compatibility,['language','voice','edition','dsp','mix','inState','outState']);if(Object.values(a.compatibility).some(v=>typeof v!=='string'||!v))fail('Invalid compatibility identity');exact(a.guards,['leading','trailing']);if(Object.values(a.guards).some(x=>!finite(x)||x<0||x>a.duration))fail('Invalid fade guards');if(!Array.isArray(a.content)||a.content.some(x=>typeof x!=='string'))fail('Invalid asset content');assets.set(a.id,a);}
 exact(m.timelines,['mediaSha256','masterSha256','deliveryMapping','speechBasis','dspBasis','dspWindows']);if(!/^[a-f0-9]{64}$/.test(m.timelines.masterSha256)||!['identity-pcm','verified-delivery-map','unverified'].includes(m.timelines.deliveryMapping)||!Array.isArray(m.timelines.dspWindows)||m.timelines.dspWindows.length>1000||['speechBasis','dspBasis'].some(k=>typeof m.timelines[k]!=='string'||!m.timelines[k]))fail('Missing timeline binding');
 const source=assets.get(m.identity.source);if(!source||Math.abs(source.duration-m.identity.duration)>.05)fail('Source duration mismatch');
 if(m.timelines.mediaSha256!==source.sha256)fail('Timeline media hash mismatch');const protectedDSP=dspIntervals(m.timelines.dspWindows,source.duration);
 for(const k of ['language','voice','edition','dsp','mix'])if(source.compatibility[k]!==m.identity[k])fail('Source identity mismatch');
 if(!Array.isArray(m.events)||!m.events.length||m.events.length>1000)fail('Missing measured ledger');
 const ids=new Set();let last=0;
 for(const e of m.events){exact(e,['id','role','start','end','required','state','measured','speech']);if(ids.has(e.id)||typeof e.id!=='string'||!e.id||typeof e.role!=='string'||!e.role||!finite(e.start)||!finite(e.end)||e.start<last||e.end<=e.start||e.end>source.duration||e.measured!==true||typeof e.required!=='boolean'||typeof e.speech!=='boolean'||typeof e.state!=='string')fail('Ambiguous or unmeasured events');ids.add(e.id);last=e.end;}
 if(!Array.isArray(m.windows)||m.windows.length>20)fail('Invalid windows');
 let end=0;const keys=new Set();
 for(const w of m.windows){exact(w,['id','control','start','end','seek','insert','fade','correlation','required','inState','outState','transitionReviewed','measured','boundarySpeechFree','approved','boundaries',...(Object.hasOwn(w,'variants')?['variants','originalChoice']:[])]);
  if(w.variants){
   const routine=routineWindow(m,w);
   const candidateChoices=routine&&w.control==='energy-ball'?['off','reminder']:variantControls[w.control];
   if(m.identity.kind!=='private-review'||!candidateChoices||w.seek!==null)fail('Variants are not approved for this window');
   if(!routine&&(w.control==='resonant-tuning'?w.originalChoice!=='full':!['off','full'].includes(w.originalChoice)))fail('Wrong original choice');
   const keys=candidateChoices.filter(x=>x!==w.originalChoice);
   exact(w.variants,keys);
   for(const v of Object.values(w.variants)){
     exact(v,['insert','correlation']);
     exact(v.correlation,['entry','exit']);
     if(Object.values(v.correlation).some(x=>!finite(x)||x<-.5||x>1.00001))fail('Unsafe variant correlation');
   }
   if(!Object.values(w.variants).some(x=>x.insert===w.insert))fail('Missing baseline insert');
  }else if(Object.hasOwn(w,'originalChoice'))fail('Missing variants');
  if(typeof w.id!=='string'||!w.id||typeof w.inState!=='string'||typeof w.outState!=='string'||keys.has(w.id)||!['preparation','relaxation','resonant-tuning','affirmation','energy-ball','return'].includes(w.control)||!finite(w.start)||!finite(w.end)||w.start-w.fade<end||w.end<=w.start||w.end>source.duration||w.measured!==true||w.boundarySpeechFree!==true||typeof w.approved!=='boolean'||typeof w.transitionReviewed!=='boolean'||!finite(w.fade)||w.fade<.1||w.fade>.3)fail('Unsafe or overlapping window');keys.add(w.id);end=w.end+w.fade;exact(w.correlation,['entry','exit']);if(Object.values(w.correlation).some(x=>!finite(x)||x<-.5||x>1.00001))fail('Unsafe correlation');if(w.start<w.fade||w.end+w.fade>source.duration||m.events.some(e=>(e.speech||e.required)&&((e.start<w.start&&e.end>w.start-w.fade)||(e.start<w.end+w.fade&&e.end>w.end))))fail('Fade crosses protected content');
  const awake=m.identity.kind==='private-review'&&m.identity.function==='OCF-PRIVATE-AWAKE-DEMO'&&m.identity.session==='quiet-focus'&&m.identity.returnPolicy==='normal-waking'&&!m.events.some(e=>['installation','sleep','reinforcement','closure'].includes(e.role));
  if(['energy-ball','affirmation'].includes(w.control)){
   const namedPreview=awake||(m.identity.kind==='private-review'&&m.identity.function==='OCF-EXP-007'&&m.identity.session==='private-energy-ball'&&m.identity.returnPolicy==='sleep');
   const contents=m.events.filter(e=>e.start<w.end+w.fade&&e.end>w.start-w.fade);
   if((w.control==='energy-ball'?!(awake||routineWindow(m,w)):!(namedPreview||routineWindow(m,w)||(w.originalChoice==='off'&&isPlainCommandPreview(m))))
      ||(w.originalChoice==='off'&&contents.length)
      ||(w.originalChoice==='full'&&(!contents.some(e=>e.speech)||contents.some(e=>e.required||e.role!==w.control||e.start<w.start||e.end>w.end))))
     fail('Optional practice must stay inside its measured private window');
  }
  if(isRoutineCommandPreview(m)&&w.control==='relaxation'){
   const last=m.events.find(e=>e.id===w.boundaries?.lastRetained);
   const first=m.events.find(e=>e.id===w.boundaries?.firstResumed);
   const covered=m.events.filter(e=>e.start<w.end&&e.end>w.start);
   if(w.seek!==null||w.variants||w.inState!=='focus-10'||w.outState!=='focus-10'
      ||last?.role!=='transmutation-box'||!last.required
      ||first?.id!=='focus-ten.begin'||!first.required||covered.length<2
      ||covered.some(e=>e.role!=='relaxation'||e.required||!e.speech)
      ||m.events.some(e=>e.role==='relaxation'&&!covered.includes(e)))
    fail('Short Relax must replace only measured full relaxation');
  }
  if(!Array.isArray(w.required)||w.required.some(x=>!ids.has(x)))fail('Unknown required content');
  exact(w.boundaries,['lastRetained','firstResumed','sourceSha256']);if(w.boundaries.sourceSha256!==source.sha256||m.events.filter(e=>e.end<=w.start-w.fade).at(-1)?.id!==w.boundaries.lastRetained||m.events.find(e=>e.start>=w.end+w.fade)?.id!==w.boundaries.firstResumed||protectedDSP.some(([a,b])=>a<w.end+w.fade&&b>w.start-w.fade))fail('Unbound speech or protected DSP transition');
  const covered=m.events.filter(e=>e.required&&e.start<w.end&&e.end>w.start);if(covered.some(e=>(['installation','reinforcement','closure'].includes(e.role)||e.role==='one-to-ten')||!w.required.includes(e.id)))fail('Required operations omitted');
  if(w.inState!==w.outState&&!w.transitionReviewed)fail('Unvalidated Focus transition');
  if(w.control==='return'){const roles=m.events.filter(e=>e.required&&e.end<=w.start).map(e=>e.role);for(const role of awake?[]:['installation','reinforcement','closure'])if(!roles.includes(role))fail('Return before required closure');const postSleep=m.identity.kind==='private-review'&&m.identity.function==='OCF-EXP-007'
     &&m.identity.session==='private-energy-ball'&&m.identity.returnPolicy==='sleep';
   if(postSleep){
     const ten=m.events.find(e=>e.id==='return.ten'&&e.role==='post-sleep-ten');
     const descent=m.events.find(e=>e.id==='return.descent'&&e.role==='sleep-descent');
     const closer=m.events.find(e=>e.id==='function-closer.block'&&e.role==='closing');
     const c1=m.timelines.dspWindows.find(e=>e.id==='waking-c1');
     if(!ten?.required||!descent?.required||!closer?.required||!c1||w.inState!=='focus-10'||w.outState!=='focus-10'
         ||descent.end>ten.start||ten.end>w.start-w.fade||w.end+w.fade>c1.start||w.end+w.fade>closer.start
         ||w.boundaries.lastRetained!==ten.id||w.boundaries.firstResumed!==closer.id
         ||!m.events.some(e=>e.role==='sleep'&&e.required&&e.end<descent.start)
         ||covered.length!==2||covered[0].id!=='return.count-to-one'||covered[1].id!=='return.alert'
         ||covered.some(e=>e.role!=='waking-return'))fail('Short return must preserve the measured Focus 20-to-10 descent, Ten, and C1');
   }else if(isRoutineCommandPreview(m)&&m.identity.returnPolicy==='sleep'){
     const c1=m.timelines.dspWindows.find(e=>e.id==='waking-c1');
     const before=m.events.find(e=>e.id===w.boundaries.lastRetained);
     const closer=m.events.find(e=>e.id===w.boundaries.firstResumed);
     const spoken=m.events.filter(e=>e.start<w.end&&e.end>w.start);
     if(w.variants||w.seek!==null||w.inState!=='focus-10'||w.outState!=='focus-10'
       ||!before?.required||before.role!=='reinforcement'||closer?.id!=='function-closer.block'
       ||!closer.required||!c1||Math.abs(c1.start-closer.start)>.003
       ||w.end+w.fade>c1.start||!m.events.some(e=>e.role==='sleep'&&e.required&&e.end<=before.start)
       ||spoken.length!==1||spoken[0].id!=='return.begin'||spoken[0].role!=='waking-return'
       ||spoken[0].required||!spoken[0].speech)fail('Routine short waking must preserve the measured sleep and C1 closer');
   }else if(m.identity.returnPolicy!=='normal-waking'||m.events.some(e=>e.role==='sleep'))fail('Return not eligible');if(awake&&(!covered.length||covered.some(e=>e.role!=='waking-return')||m.events.find(e=>e.id===w.boundaries.firstResumed)?.role!=='closing'))fail('Awake return must preserve the closer');}
  if(w.seek!==null){const speechEnd=Math.max(w.start,...m.events.filter(e=>e.start>=w.start&&e.end<=w.end).map(e=>e.end));exact(w.seek,['start','end','retainedActionSeconds']);if(!finite(w.seek.start)||!finite(w.seek.end)||w.seek.start<w.start||w.seek.end>w.end||w.seek.end<=w.seek.start||!finite(w.seek.retainedActionSeconds)||w.seek.retainedActionSeconds<8||w.seek.retainedActionSeconds>w.end-speechEnd-(w.seek.end-w.seek.start)||w.inState!==w.outState||m.events.some(e=>(e.required||e.speech)&&e.start<w.seek.end&&e.end>w.seek.start))fail('Unsafe seek bypass');}
  for(const insert of new Set([w.insert,...Object.values(w.variants||{}).map(v=>v.insert)])){
  const ins=assets.get(insert);if(!ins||ins.guards.leading<w.fade||ins.guards.trailing<w.fade||ins.duration<=2*w.fade||ins.bytes>8*1024*1024)fail('Missing or oversized insert');
  if(w.required.some(id=>!ins.content.includes(id)))fail('Insert omits required content');
  for(const k of ['language','voice','edition','dsp','mix'])if(ins.compatibility[k]!==m.identity[k])fail('Incompatible insert '+k);
  if(ins.compatibility.inState!==w.inState||ins.compatibility.outState!==w.outState)fail('Insert state mismatch');
  }
 }
 for(const mode of ['full','A','B']){if(!finite(m.profiles[mode])||Math.abs(plan(m,mode,Object.fromEntries(m.windows.map(w=>[w.control,true])),true).duration-m.profiles[mode])>.02)fail('Profile duration mismatch');}
 return m;
}
export function usable(m,privateReview=false){if(m.timelines.deliveryMapping==='unverified'||m.timelines.dspBasis==='unavailable')return false;if(m.identity.kind==='private-review')return privateReview===true&&m.approvals.mechanical==='verified'&&m.approvals.editorial==='pending'&&m.approvals.listening==='pending';return m.approvals.mechanical==='verified'&&(m.identity.kind==='mechanical-fixture'?m.approvals.editorial==='fixture-only'&&m.approvals.listening==='fixture-only':m.approvals.editorial==='verified'&&m.approvals.listening==='verified');}
export function plan(m,mode='full',toggles={},unchecked=false,privateReview=false){
 if(!['full','A','B'].includes(mode))fail('Unknown playback mode');
 if(mode!=='full'&&!unchecked&&!usable(m,privateReview))mode='full';
 const segments=[];let cursor=0,t=0;const add=(asset,from,to,overlap=0,window=null)=>{if(to<=from)return;t-=overlap;segments.push({asset,from,to,start:t,end:t+to-from,window});t+=to-from;};
 for(const w of mode==='full'?[]:m.windows.filter(w=>w.approved&&alternative(w,toggles[w.control]))){
  if(mode==='A'){if(!w.seek)continue;add(m.identity.source,cursor,w.seek.start);cursor=w.seek.end;}
  else {add(m.identity.source,cursor,w.start);const v=alternative(w,toggles[w.control]);const a=m.assets.find(a=>a.id===v.insert);add(a.id,0,a.duration,w.fade,{...w,correlation:v.correlation});cursor=w.end;t-=w.fade;}
 }
 add(m.identity.source,cursor,m.identity.duration);return {mode,segments,duration:t,saved:m.identity.duration-t};
}
export function at(p,t){return p.segments.filter(s=>t>=s.start&&t<s.end).map(s=>({...s,media:s.from+t-s.start}));}
export function originalTime(p,t){const active=at(p,t),s=active.find(s=>!s.window)||active[0];return s?s.window?s.window.start+(t-s.start)/(s.end-s.start)*(s.window.end-s.window.start):s.media:p.segments.at(-1).to;}
export function gains(x,rho=0,policy='equal-power'){const a=Math.cos(Math.max(0,Math.min(1,x))*Math.PI/2),b=Math.sin(Math.max(0,Math.min(1,x))*Math.PI/2);const n=policy==='correlation-aware'?Math.sqrt(Math.max(.1,a*a+b*b+2*rho*a*b)):1;return [a/n,b/n];}

export function virtualTime(p,sourceTime){for(const s of p.segments){if(!s.window&&sourceTime>=s.from&&sourceTime<=s.to)return s.start+sourceTime-s.from;if(s.window&&sourceTime>=s.window.start&&sourceTime<=s.window.end)return s.start;}return Math.min(sourceTime,p.duration);}

export function dspIntervals(rows,duration){const out=[];for(const r of rows){exact(r,['id','start','end','approach']);if(!finite(r.start)||!finite(r.end)||r.start<0||r.end<r.start||r.end>duration)fail('Invalid DSP window');if(r.end>r.start)out.push([r.start,r.end]);if(r.approach!==null){exact(r.approach,['start','established','arrival']);const a=r.approach;if(![a.start,a.established,a.arrival].every(finite)||a.start<0||a.established<a.start||a.arrival<a.established||a.arrival>duration)fail('Invalid DSP approach');out.push([a.start,a.arrival]);}}return out;}
