/* Native Android WebView partitions -> signed backend, two independent websites. */
import assert from 'node:assert/strict';
const port=Number(process.env.WOLF_WEBVIEW_CDP_PORT||9242),endpoint='http://127.0.0.1:'+port;
const sleep=n=>new Promise(r=>setTimeout(r,n));
const targets=async()=>(await(await fetch(endpoint+'/json')).json()).filter(x=>x.type==='page');
async function until(fn,tries=65){for(let i=0;i<tries;i++){try{const value=await fn();if(value)return value;}catch{}await sleep(160)}throw Error('Timed out waiting for browser state')}
async function attach(t){
 const ws=new WebSocket(t.webSocketDebuggerUrl.replace(/127\.0\.0\.1:\d+/,'127.0.0.1:'+port));
 await new Promise((resolve,reject)=>{ws.onopen=resolve;ws.onerror=reject});
 let seq=0;const pending=new Map();
 ws.onmessage=e=>{const m=JSON.parse(e.data);if(m.id&&pending.has(m.id)){const p=pending.get(m.id);pending.delete(m.id);m.error?p.reject(Error(m.error.message)):p.resolve(m.result)}};
 return {eval:async expression=>{const r=await new Promise((resolve,reject)=>{const id=++seq;pending.set(id,{resolve,reject});
 ws.send(JSON.stringify({id,method:'Runtime.evaluate',params:{expression,returnByValue:true,awaitPromise:true}}))});
 if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description||r.exceptionDetails.text);return r.result?.value;
 },close:()=>ws.close()};
}
const ui=await attach(await until(async()=>(await targets()).find(t=>t.url?.includes('appassets.androidplatform.net/assets/wolfcoin.html'))));
const accounts=[
 {id:'android_v09_pair_sports_a',name:'Local Sports Provider A',url:'http://10.0.2.2:44567/login',type:'Betting',financialCurrency:'ZMW'},
 {id:'android_v09_pair_sports_b',name:'Local Sports Provider B',url:'http://10.0.2.2:44568/login',type:'Betting',financialCurrency:'ZMW'}
];
try{
 for(const account of accounts){
  await ui.eval("(()=>{const a="+JSON.stringify(account)+";if(!state.accounts.some(x=>x.id===a.id))state.accounts.push({...a,known:false,status:'unverified',sync:'Not synchronized',device:'Android Wolf Browser',balance:null,pending:null,pnl:null});createTab(a.url,a.id);return true})()");
  const target=await until(async()=>(await targets()).find(t=>t.url===account.url));
  const web=await attach(target);
  try{
   await until(async()=>await web.eval("!!document.querySelector('[name=pass]')"));
   await web.eval("(()=>{document.querySelector('[name=user]').value='fixture';document.querySelector('[name=pass]').value='fixture';document.querySelector('form').requestSubmit();return true})()");
  }finally{web.close()}
  const snapshot=await until(async()=>{const x=await ui.eval("window.wolfNative.snapshot({accountId:"+JSON.stringify(account.id)+"})");return x?.auth==='probable_authenticated'?x:null});
  assert.equal(snapshot.identity?.displayName,'Alex Example');
  await ui.eval("window.wolfBackend.observeAccount(state.accounts.find(x=>x.id==="+JSON.stringify(account.id)+"))");
 }
 const backend=await ui.eval("window.wolfBackend.snapshot()");
 const selected=accounts.map(x=>backend.accounts.find(y=>y.account_id===x.id));
 assert(selected.every(x=>x?.latest_financial?.fields?.cash_balance==='750'));
 const previous=backend.history.filter(x=>accounts.some(a=>a.id===x.account_id));
 assert.equal(previous.length,2);
 assert(previous.every(x=>x.observations.length>=1));
 const sync=await ui.eval("window.wolfBackend.syncAll(state.accounts.filter(a=>a.id.startsWith('android_v09_pair_')))");
 assert.equal(sync.results.length,2);
 assert(sync.results.every(x=>x.status==='OBSERVED'),JSON.stringify(sync.results));
 const persisted=await ui.eval("window.wolfBackend.snapshot()");
 const histories=persisted.history.filter(x=>accounts.some(a=>a.id===x.account_id));
 assert(histories.every(x=>x.observations.length>=2));
 const matches=await ui.eval("window.WolfPortfolio.snapshot().matches");
 console.log('WOLF_ANDROID_NATIVE_CROSS_PLATFORM_PAIR_SYNC_PASS '+JSON.stringify({
  accounts:accounts.map(x=>x.id),observations:histories.map(x=>x.observations.length),
  sync:sync.results.map(x=>x.status),matches:matches.length,backend:'wolf.app.bridge.v2'
 }));
}finally{ui.close()}
