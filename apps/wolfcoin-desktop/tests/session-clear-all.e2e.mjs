import assert from 'node:assert/strict';
const port=Number(process.env.WOLF_CDP_PORT||13997);
const url='http://127.0.0.1:'+port;
const pattern=process.env.WOLF_ANDROID==='1'?'/assets/wolfcoin.html':'file:';
const target=(await(await fetch(url+'/json')).json()).find(x=>x.type==='page'&&x.url?.includes(pattern));
assert(target,'Wolf UI target unavailable');
const ws=new WebSocket(target.webSocketDebuggerUrl.replace(/127\.0\.0\.1:\d+/,'127.0.0.1:'+port));
await new Promise((yes,no)=>{ws.onopen=yes;ws.onerror=no});
let seq=0;const pending=new Map();
ws.onmessage=e=>{const m=JSON.parse(e.data);if(m.id&&pending.has(m.id)){const p=pending.get(m.id);pending.delete(m.id);m.error?p.reject(Error(m.error.message)):p.resolve(m.result)}};
async function run(expression){
 const r=await new Promise((resolve,reject)=>{const n=++seq;pending.set(n,{resolve,reject});ws.send(JSON.stringify({id:n,method:'Runtime.evaluate',params:{expression,returnByValue:true,awaitPromise:true}}))});
 if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description||r.exceptionDetails.text);
 return r.result?.value;
}
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
async function until(fn,n=100){
 for(let i=0;i<n;i++){try{const x=await fn();if(x)return x}catch{}await sleep(140)}
 throw Error('Session lifecycle timed out');
}
const address=process.env.WOLF_FIXTURE_URL||'http://127.0.0.1:44692/login';
const a='clearing_a',b='clearing_b',ids=[a,b];
try{
 await run("state.accounts=[];state.tab='sessions';render()");
 for(const id of ids){
  await run('window.wolfNative.showBrowser('+JSON.stringify({accountId:id,url:address})+')');
  await until(async()=>{const d=await run('window.wolfNative.snapshot('+JSON.stringify({accountId:id})+')');return d.auth==='login_required'});
  for(const [selector,text] of [['input[name=user]','fixture'],['input[name=pass]','fixture']]){
   const res=await run('window.wolfNative.action('+JSON.stringify({accountId:id,type:'fill',selector,text})+')');
   assert.equal(res.ok,true);
  }
  const clicked=await run('window.wolfNative.action('+JSON.stringify({accountId:id,type:'click',selector:'button[type=submit]'})+')');
  assert.equal(clicked.ok,true);
  await until(async()=>{const d=await run('window.wolfNative.snapshot('+JSON.stringify({accountId:id})+')');return d.auth==='probable_authenticated'});
 }
 await run('(()=>{for(const [id,name] of [['+ids.map(id=>JSON.stringify(id)+','+JSON.stringify(id)).join('],[')+']]){state.accounts.push({id,name,type:"Betting",url:'+JSON.stringify(address)+',known:true,balance:750,pending:100,pnl:60,financialCurrency:"ZMW",status:"connected",sync:"now"});}state.tab="sessions";render();return true})()');
 assert.equal(await run('state.accounts.length'),2);
 await run("document.querySelector('[data-action=terminate-all]').click()");
 assert.match(await run("document.querySelector('#modalRoot').textContent"),/native browser cookies|local browser cookies/i);
 await run("document.querySelector('[data-action=confirm-terminate-all]').click()");
 await until(async()=>await run("state.accounts.every(x=>x.status==='loggedout')"));
 assert.equal(await run('state.accounts.length'),2);
 assert.equal(await run('state.accounts.every(x=>x.balance===750)'),true);
 for(const id of ids){
  await run('window.wolfNative.showBrowser('+JSON.stringify({accountId:id,url:address})+')');
  await until(async()=>{const d=await run('window.wolfNative.snapshot('+JSON.stringify({accountId:id})+')');return d.auth==='login_required'});
 }
 console.log('WOLF_CLEAR_ALL_NATIVE_SESSIONS_PASS',JSON.stringify({registeredAccounts:2,lastKnownBalancesPreserved:true,allProfilesCleared:true,liveProviderTouched:false}));
}finally{ws.close()}
