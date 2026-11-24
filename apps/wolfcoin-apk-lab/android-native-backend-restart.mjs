/* Device-level signed backend, SQLite + WebView cookie survival after Android process restart. */
import assert from 'node:assert/strict';
const port=Number(process.env.WOLF_WEBVIEW_CDP_PORT||9242),base='http://127.0.0.1:'+port;
const accountId=process.env.WOLF_ANDROID_ACCOUNT_ID||'android_v09_lab_sports_3',url='http://10.0.2.2:44567/login';
const sleep=t=>new Promise(r=>setTimeout(r,t));
async function until(f,n=65){for(let i=0;i<n;i++){try{const x=await f();if(x)return x;}catch{}await sleep(150)}throw Error('Android restart proof timed out')}
async function connect(t){
 const ws=new WebSocket(t.webSocketDebuggerUrl.replace(/127\.0\.0\.1:\d+/,'127.0.0.1:'+port));
 await new Promise((yes,no)=>{ws.onopen=yes;ws.onerror=no});
 let seq=0;const pending=new Map();
 ws.onmessage=e=>{const m=JSON.parse(e.data);if(m.id&&pending.has(m.id)){const j=pending.get(m.id);pending.delete(m.id);m.error?j.reject(Error(m.error.message)):j.resolve(m.result)}};
 return {eval:async expr=>{
  const r=await new Promise((resolve,reject)=>{const id=++seq;pending.set(id,{resolve,reject});
   ws.send(JSON.stringify({id,method:'Runtime.evaluate',params:{expression:expr,returnByValue:true,awaitPromise:true}}))});
  if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description||r.exceptionDetails.text);
  return r.result?.value;
 },close:()=>ws.close()};
}
const pages=await(await fetch(base+'/json')).json();
const ui=await connect(pages.find(x=>x.url?.includes('appassets.androidplatform.net/assets/wolfcoin.html')));
try{
 const status=await until(async()=>{const r=await ui.eval("window.wolfBackend.status()");return r?.available?r:null});
 assert.equal(status.schema,'wolf.app.bridge.v2');
 const initial=await ui.eval("window.wolfBackend.snapshot()");
 const account=initial.accounts.find(a=>a.account_id===accountId);
 assert(account,'Backend registered account disappeared after process restart');
 assert.equal(account.session_state,'PAUSED');
 assert.equal(account.freshness,'STALE_LAST_KNOWN');
 assert.equal(account.latest_financial?.fields?.cash_balance,'750');
 const history=initial.history.find(h=>h.account_id===accountId);
 assert(history?.observations?.length>=1);
 await ui.eval("(()=>{const a=state.accounts.find(a=>a.id==="+JSON.stringify(accountId)+");if(!a)return false;createTab("+JSON.stringify(url)+","+JSON.stringify(accountId)+");return true})()");
 const snap=await until(async()=>{
  const s=await ui.eval("window.wolfNative.snapshot({accountId:"+JSON.stringify(accountId)+"})");
  return s?.auth==='probable_authenticated'?s:null;
 });
 assert.equal(snap.identity?.displayName,'Alex Example');
 await ui.eval("window.wolfBackend.observeAccount(state.accounts.find(a=>a.id==="+JSON.stringify(accountId)+"))");
 const confirmed=await until(async()=>{
  const x=await ui.eval("window.wolfBackend.snapshot()");
  const a=x.accounts.find(a=>a.account_id===accountId);
  const count=x.history.find(h=>h.account_id===accountId)?.observations?.length||0;
  return a?.session_state==='ACTIVE'&&count>=2?x:null;
 },85);
 const revalidated=confirmed.accounts.find(a=>a.account_id===accountId);
 console.log('WOLF_ANDROID_EMBEDDED_BACKEND_RESTART_PASS '+JSON.stringify({
  account:accountId,backend:status.schema,firstState:account.session_state,
  firstFreshness:account.freshness,persistedBalance:account.latest_financial.fields.cash_balance,
  restoredSessionAuth:snap.auth,revalidatedState:revalidated.session_state,
  history:confirmed.history.find(h=>h.account_id===accountId).observations.length
 }));
}finally{ui.close()}
