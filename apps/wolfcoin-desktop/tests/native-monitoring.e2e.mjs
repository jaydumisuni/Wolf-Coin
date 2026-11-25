import assert from 'node:assert/strict';
const port=Number(process.env.WOLF_TEST_CDP_PORT||13991);
const endpoint='http://127.0.0.1:'+port;
const sleep=n=>new Promise(resolve=>setTimeout(resolve,n));
const targets=async()=>(await(await fetch(endpoint+'/json')).json()).filter(x=>x.type==='page');
const uiTarget=(await targets()).find(x=>x.url?.startsWith('file:'));
assert(uiTarget,'Wolf UI target missing');
const ws=new WebSocket(uiTarget.webSocketDebuggerUrl);
await new Promise((yes,no)=>{ws.onopen=yes;ws.onerror=no});
let seq=0;const pending=new Map();
ws.onmessage=e=>{const m=JSON.parse(e.data);const p=pending.get(m.id);if(p){pending.delete(m.id);m.error?p.reject(Error(m.error.message)):p.resolve(m.result)}};
const evaluate=async expression=>{
 const result=await new Promise((resolve,reject)=>{const id=++seq;pending.set(id,{resolve,reject});ws.send(JSON.stringify({id,method:'Runtime.evaluate',params:{expression,returnByValue:true,awaitPromise:true}}))});
 if(result.exceptionDetails)throw Error(result.exceptionDetails.exception?.description||result.exceptionDetails.text);
 return result.result?.value;
};
async function until(fn,n=65){for(let i=0;i<n;i++){try{const v=await fn();if(v)return v}catch{}await sleep(150)}throw Error('Native account evidence not ready')}
const id='wolf_native_monitor_095_'+Date.now();
const url='http://127.0.0.1:44692/login';
try{
 await evaluate("state.accounts.push("+JSON.stringify({id,name:'Local monitoring QA',type:'Betting',url,user:'QA',financialCurrency:'ZMW',status:'unverified',balance:null,pending:null,pnl:null,known:false,sync:'Not synchronized',device:'Wolf Browser'})+");createTab("+JSON.stringify(url)+","+JSON.stringify(id)+")");
 await until(async()=>{const s=await evaluate("window.wolfNative.snapshot({accountId:"+JSON.stringify(id)+"})");return s?.auth==='login_required'});
 for(const [selector,text] of [['input[name=user]','fixture'],['input[name=pass]','fixture']]){
  const r=await evaluate("window.wolfNative.action("+JSON.stringify({accountId:id,type:'fill',selector,text})+")");
  assert.equal(r.ok,true,JSON.stringify(r));
 }
 const click=await evaluate("window.wolfNative.action("+JSON.stringify({accountId:id,type:'click',selector:'button[type=submit]'})+")");
 assert.equal(click.ok,true,JSON.stringify(click));
 await until(async()=>{const s=await evaluate("window.wolfNative.snapshot({accountId:"+JSON.stringify(id)+"})");return s?.auth==='probable_authenticated'});
 await evaluate("syncNativeAccount("+JSON.stringify(id)+")");
 const connected=await until(async()=>{
  const a=await evaluate("state.accounts.find(a=>a.id==="+JSON.stringify(id)+")");
  return a?.status==='connected'&&a.balance===750?a:null;
 });
 assert.equal(connected.pending,100);
 const before=await evaluate("window.wolfBackend.snapshot()");
 const historyFor=s=>(s.history||[]).find(h=>h.account_id===id);
 const startObs=(historyFor(before)?.observations||[]).length;
 await evaluate("state.settings.autosync=false;state.settings.enableAutomation=true;state.settings.background=true;state.settings.syncInterval='15';configureWolfAutoSync()");
 assert.equal(await evaluate("wolfAutoTimer!==null"),true);
 await sleep(16600);
 const after=await evaluate("window.wolfBackend.snapshot()");
 const afterObs=(historyFor(after)?.observations||[]).length;
 assert(afterObs>startObs,'Automated native backend observations did not grow after 15-second interval: '+startObs+' vs '+afterObs);
 await evaluate("runAction('pause-session',{dataset:{id:"+JSON.stringify(id)+"}},null)");
 const paused=await until(async()=>{
  const a=await evaluate("state.accounts.find(a=>a.id==="+JSON.stringify(id)+")");
  const b=await evaluate("window.wolfBackend.snapshot()");
  const rec=b.accounts?.find(x=>x.account_id===id);
  return a?.status==='paused'&&rec?.session_state==='PAUSED'?{a,rec}:null;
 });
 await evaluate("runAction('resume-session',{dataset:{id:"+JSON.stringify(id)+"}},null)");
 const resumed=await until(async()=>{
  const a=await evaluate("state.accounts.find(a=>a.id==="+JSON.stringify(id)+")");
  const b=await evaluate("window.wolfBackend.snapshot()");
  const rec=b.accounts?.find(x=>x.account_id===id);
  return a?.status==='unverified'&&rec?.session_state==='OFFLINE'?{a,rec}:null;
 });
 await evaluate("state.settings.enableAutomation=false;configureWolfAutoSync()");
 console.log('WOLF_REAL_SCHEDULED_BACKEND_SESSION_PASS',JSON.stringify({initialObservations:startObs,after15Seconds:afterObs,accountCash:connected.balance,pausedBackend:paused.rec.session_state,resumedBackend:resumed.rec.session_state,loginStillInProfile:true,schedulerStopped:await evaluate('wolfAutoTimer===null')}));
}finally{ws.close()}
