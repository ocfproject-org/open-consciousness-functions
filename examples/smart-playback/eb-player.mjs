import {validate,plan,originalTime,virtualTime,availableChoices} from './eb-model.mjs';

const clamp=(value,high)=>Math.max(0,Math.min(value,high));
const controlsFor=m=>[...new Set(m.windows.filter(w=>w.approved).map(w=>w.control))];
const signature=m=>JSON.stringify({assets:m.assets.map(a=>a.sha256),windows:m.windows});
const bookmarkKey=m=>'ocf-private-review-mount-resume:'+m.assets[0].sha256;
const original=m=>m.assets.find(a=>a.id===m.identity.source);

// Bind the single native stream to the exact verified edit list. Legacy true
// means the measured w.insert alternative, not necessarily the first variant.
export function nativeStream(m,p,toggles={}){
 const master=original(m);
 if(!p.segments.some(s=>s.window))return {path:master.path,edited:false};
 const ordinals=controlsFor(m).map(control=>{
   const choices=availableChoices(m,control);
   const windows=m.windows.filter(w=>w.approved&&w.control===control);
   const selected=windows.map(w=>p.segments.find(s=>s.window?.id===w.id)?.asset??null);
   const matching=choices.filter((choice,index)=>windows.every((w,i)=>{
     const asset=index===0?null:w.variants?.[choice]?.insert??(!w.variants&&choice==='short'?w.insert:null);
     return asset===selected[i];
   }));
   const desired=toggles[control];
   const choice=matching.includes(desired)?desired:matching[0];
   if(!choice)throw Error('No verified audio stream matches these guidance choices');
   return choices.indexOf(choice);
 });
 if(!/^[a-z0-9-]+$/.test(m.identity.session)||!ordinals.length)throw Error('Unknown session stream');
 return {path:'media/native-'+m.identity.session+'-'+ordinals.join('')+'.wav',edited:true};
}

export class SmartPlayer{
 constructor(source,insert,notify=()=>{}){
  this.media=[source,insert];this.notify=notify;
  this.native=document.createElement('audio');
  this.native.preload='metadata';this.native.hidden=true;
  source.after(this.native);
  this.session=navigator.mediaSession;
  this.running=false;this.nativePlaying=false;this.loadingPlay=null;this.generation=0;
  this.interruption=null;this.t=0;this.toggles={};this.stream=null;this.buffering=null;this.lastSavedAt=0;
  this.stats={verified:[],fallbacks:0,transitions:[],requests:[],initialLatencyMs:null};
  this.native.addEventListener('waiting',()=>this.buffer());
  this.native.addEventListener('stalled',()=>{if(this.native.readyState<3)this.buffer();});
  this.native.addEventListener('playing',()=>this.clearBuffer(true));
  this.native.addEventListener('canplay',()=>{if(this.native.readyState>=3)this.clearBuffer(this.running);});
  this.native.addEventListener('timeupdate',()=>this.timeUpdate());
  this.native.addEventListener('loadedmetadata',()=>this.checkDuration());
  this.native.addEventListener('durationchange',()=>this.checkDuration());
  this.native.addEventListener('error',()=>{
   if(this.running||this.loadingPlay!==null)this.fallback(this.stream?.edited?'The selected stream could not be loaded':'The original stream could not be loaded');
  });
  this.native.addEventListener('ended',()=>{
   if(!this.running||!this.native.ended)return;
   this.pause();this.t=this.p.duration;this.setMediaSession('paused');this.save();this.notify('Playback complete.');
  });
  this.native.addEventListener('pause',()=>{
   if(!this.running||!this.native.paused||this.native.ended)return;
   this.pause();this.notify('Playback paused. Press Play to resume.');
  });
  this.transportHandlers={
   play:()=>this.play(),pause:()=>this.pause(),stop:()=>this.pause(),
   seekbackward:({seekOffset=10}={})=>this.seekFromSession(this.current()-seekOffset),
   seekforward:({seekOffset=10}={})=>this.seekFromSession(this.current()+seekOffset),
   seekto:({seekTime}={})=>{if(Number.isFinite(seekTime))this.seekFromSession(seekTime);},
  };
  for(const [action,handler] of Object.entries(this.transportHandlers))try{this.session?.setActionHandler(action,handler);}catch{}
  this.pagehide=()=>this.destroy();
  this.visibility=()=>{if(document.hidden)this.save();else this.setMediaSession(this.running?'playing':'paused');};
  window.addEventListener('pagehide',this.pagehide);
  document.addEventListener('visibilitychange',this.visibility);
 }
 setMediaSession(state){
  if(!this.session)return;
  try{
   this.session.playbackState=state;
   if(this.p?.duration>0&&state!=='none')this.session.setPositionState?.({duration:this.p.duration,playbackRate:1,position:clamp(this.current(),this.p.duration)});
   else this.session.setPositionState?.();
  }catch{}
 }
 async seekFromSession(t){
  try{await this.seek(t);}catch{this.notify('Could not change position. Try again.');}
 }
 async verifyAsset(a){
  const t=performance.now(),url=new URL(a.path,import.meta.url);
  const r=await fetch(url,{method:'HEAD',cache:'no-store',signal:AbortSignal.timeout(4000)});
  if(!r.ok||r.headers.get('etag')!==`"${a.sha256}"`||Number(r.headers.get('content-length'))!==a.bytes||r.headers.get('accept-ranges')!=='bytes')throw Error('Original audio identity could not be verified');
  const range=await fetch(url,{headers:{Range:'bytes=0-1'},cache:'no-store',signal:AbortSignal.timeout(4000)});
  if(range.status!==206||range.headers.get('content-range')!==`bytes 0-1/${a.bytes}`||(await range.arrayBuffer()).byteLength!==2)throw Error('The server did not provide a valid audio range');
  this.stats.verified.push(a.id);this.stats.requests.push({asset:a.id,ms:performance.now()-t});
 }
 async load(m,{privateReview=false}={}){
  this.pause();this.hasInteracted=false;this.interruption=null;this.stream=null;this.t=0;
  this.native.removeAttribute('src');this.native.load();
  this.privateReview=privateReview===true;const generation=++this.generation;
  this.m=validate(m);this.p=plan(m);this.toggles={};this.stats.verified=[];
  await this.verifyAsset(original(m));
  if(generation!==this.generation)return;
  if(this.session&&typeof MediaMetadata==='function'){
   try{this.session.metadata=new MediaMetadata({title:m.identity.session==='quiet-focus'?'Quiet Focus':'Energy Ball',artist:'Open Consciousness Functions'});}catch{}
  }
  this.setMediaSession('none');this.notify(m.notice);return this;
 }
 setProfile(mode,toggles){
  const old=this.p?originalTime(this.p,this.current()):0;
  this.pause();
  this.toggles={...toggles};
  // The native pack represents verified insert edits, not legacy seek-only previews.
  const usableMode=mode==='A'?'B':mode;
  this.p=plan(this.m,usableMode,toggles,false,this.privateReview);
  this.interruption=null;this.t=virtualTime(this.p,old);this.hasInteracted=true;
  this.setMediaSession('paused');this.save();
  this.notify(usableMode!==this.p.mode?'No compatible edits are available for this recording.':'Guidance updated. Press Play when ready.');
  return this.p;
 }
 current(){
  if(this.running&&Number.isFinite(this.native.currentTime))return clamp(this.native.currentTime,this.p.duration);
  return this.t;
 }
 checkDuration(){
  if(!this.stream||!this.p||(!this.running&&this.loadingPlay===null)||this.native.readyState<1)return true;
  if(!Number.isFinite(this.native.duration)||Math.abs(this.native.duration-this.p.duration)>.12){
   this.fallback('The audio duration does not match this session');return false;
  }
  return true;
 }
 clearBuffer(notify=false){
  if(this.buffering===null)return;
  clearTimeout(this.buffering);this.buffering=null;
  if(notify)this.notify(this.stream?.edited?'Playing with your selected guidance.':'Playing Full Guidance.');
 }
 buffer(){
  if((!this.running&&this.loadingPlay===null)||this.buffering!==null)return;
  this.notify('Buffering this session…');
  const generation=this.generation;
  this.buffering=setTimeout(()=>{
   this.buffering=null;
   if(generation===this.generation&&(this.running||this.loadingPlay!==null)&&this.native.readyState<3)
    this.fallback('The audio took too long to buffer');
  },8000);
 }
 timeUpdate(){
  if(!this.running)return;
  if(this.native.readyState>=3)this.clearBuffer(true);
  if(performance.now()-this.lastSavedAt>=5000){this.setMediaSession('playing');this.save();}
 }
 async play(){
  if(this.running||!this.m||this.loadingPlay!==null)return;
  const generation=++this.generation,start=performance.now();
  this.hasInteracted=true;this.loadingPlay=generation;this.interruption=null;
  let timer;
  try{
   const selected=nativeStream(this.m,this.p,this.toggles);
   const url=new URL(selected.path,import.meta.url).href;
   this.stream=selected;
   if(this.native.src!==url)this.native.src=url;
   else if(this.native.error)this.native.load();
   const begin=this.t>=this.p.duration-.001?0:this.t;
   this.native.currentTime=begin;
   // Invoke play before any asynchronous work so mobile grants the user gesture.
   const playback=this.native.play();
   this.buffer();
   await Promise.race([playback,new Promise((_,reject)=>{timer=setTimeout(()=>reject(Error('The audio took too long to start')),12000);})]);
   if(generation!==this.generation||!this.checkDuration())return;
   this.running=true;this.nativePlaying=true;this.clearBuffer();
   this.stats.initialLatencyMs=performance.now()-start;this.setMediaSession('playing');
   this.notify(selected.edited?'Playing with your selected guidance.':'Playing Full Guidance.');this.save();
  }catch(e){
   if(generation!==this.generation)return;
   const reason=e?.name==='NotAllowedError'?'The browser blocked playback. Tap Play again':
      /^The audio took too long/.test(e?.message)?e.message:'This audio stream could not be started';
   this.fallback(reason);
  }finally{clearTimeout(timer);if(this.loadingPlay===generation)this.loadingPlay=null;}
 }
 pause(){
  if(this.running)this.t=this.current();
  this.running=false;this.nativePlaying=false;this.loadingPlay=null;++this.generation;
  this.clearBuffer();this.native.pause();this.setMediaSession('paused');this.save();
 }
 async seek(value){
  if(!this.p)return;
  this.hasInteracted=true;const target=clamp(Number(value)||0,Math.max(0,this.p.duration-.001));
  if(this.running){
   this.native.currentTime=target;
  }else if(this.loadingPlay!==null){
   // Invalidate the pending native start; this is only a position change.
   this.pause();this.notify('Position changed. Press Play when ready.');
  }
  // If paused, do not touch the native currentTime: Chrome may issue a Range request.
  this.t=target;this.setMediaSession(this.running?'playing':'paused');this.save();
 }
 fallback(reason){
  this.pause();this.stats.fallbacks++;
  this.interruption={reason};
  this.notify('Playback paused: '+reason+'. Your guidance choices are unchanged.');
 }
 save(){
  if(!this.m||!this.p||!this.hasInteracted)return;
  this.lastSavedAt=performance.now();
  try{localStorage.setItem(bookmarkKey(this.m),JSON.stringify({sha:this.m.assets[0].sha256,signature:this.privateReview?signature(this.m):null,mode:this.p.mode,toggles:this.toggles,t:this.current()}));}
  catch{}
 }
 restore(){
  try{
   const s=JSON.parse(localStorage.getItem(bookmarkKey(this.m)));
   if(this.privateReview&&s?.signature!==signature(this.m))return false;
   if(s?.sha!==this.m.assets[0].sha256||!s.toggles||Object.keys(s.toggles).some(k=>typeof s.toggles[k]!=='boolean'&&!availableChoices(this.m,k).includes(s.toggles[k]))||!['full','A','B'].includes(s.mode)||!Number.isFinite(s.t))return false;
   const source=s.mode==='A'?originalTime(plan(this.m,'A',s.toggles,false,this.privateReview),s.t):null;
   this.setProfile(s.mode,s.toggles);this.t=clamp(source===null?s.t:virtualTime(this.p,source),this.p.duration);
   this.setMediaSession('paused');this.save();return true;
  }catch{return false;}
 }
 destroy(){
  this.pause();this.setMediaSession('none');
  if(this.session){try{this.session.metadata=null;}catch{}for(const action of Object.keys(this.transportHandlers))try{this.session.setActionHandler(action,null);}catch{}}
  this.native.removeAttribute('src');this.native.load();this.native.remove();
  window.removeEventListener('pagehide',this.pagehide);
  document.removeEventListener('visibilitychange',this.visibility);
 }
}
