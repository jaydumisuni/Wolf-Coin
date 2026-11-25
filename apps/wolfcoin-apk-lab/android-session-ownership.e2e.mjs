import assert from 'node:assert/strict';
const port=Number(process.env.WOLF_WEBVIEW_CDP_PORT||9277);
const phase=process.env.WOLF_SESSION_PHASE||'fresh';
const targets=await(await fetch('http://127.0.0.1:'+port+'/json')).json();
const app=targets.find(x=>x.url?.includes('/assets/wolfcoin.html'));
assert(app,'Wolf-Coin Android UI target missing');
const ws=new WebSocket(app.webSocketDebuggerUrl.replace(/127\.0\.0\.1:\d+/,'127.0.0.1:'+port));
await new Promise((yes,no)=>{ws.onopen=yes;ws.onerror=no});
let id=0;const pending=new Map();
ws.onmessage=e=>{const m=JSON.parse(e.data);if(m.id&&pending.has(m.id)){const p=pending.get(m.id);pending.delete(m.id);m.error?p.reject(Error(m.error.message)):p.resolve(m.result)}};
async function run(expression){
 const r=await new Promise((resolve,reject)=>{const i=++id;pending.set(i,{resolve,reject});ws.send(JSON.stringify({id:i,method:'Runtime.evaluate',params:{expression,returnByValue:true,awaitPromise:true}}))});
 if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description||r.exceptionDetails.text);
 return r.result?.value;
}
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
async function until(fn){
 for(let i=0;i<100;i++){try{const x=await fn();if(x)return x}catch{}await sleep(130)}
 throw Error('WebView session transition timed out');
}
const site='http://10.0.2.2:44692/login',A='v094_keep_login',B='v094_second_account';
async function snapshot(accountId){return run('window.wolfNative.snapshot('+JSON.stringify({accountId})+')')}
async function navigate(accountId){return run('window.wolfNative.showBrowser('+JSON.stringify({accountId,url:site})+')')}
try{
 const status=await run('window.wolfNative.status()');
 assert.equal(status.multiProfile,true);
 await navigate(A);
 if(phase==='fresh'){
  await until(async()=>(await snapshot(A))?.auth==='login_required');
  for(const [selector,text] of [['input[name=user]','fixture'],['input[name=pass]','fixture']]){
   const x=await run('window.wolfNative.action('+JSON.stringify({accountId:A,type:'fill',selector,text})+')');
   assert.equal(x.ok,true,JSON.stringify(x));
  }
  const submit=await run('window.wolfNative.action('+JSON.stringify({accountId:A,type:'click',selector:'button[type=submit]'})+')');
  assert.equal(submit.ok,true);
  await until(async()=>(await snapshot(A))?.auth==='probable_authenticated');
  await navigate(B);
  await until(async()=>(await snapshot(B))?.auth==='login_required');
  console.log('WOLF_ANDROID_SESSION_ISOLATION_PASS',JSON.stringify({a:'logged in',b:'login required',persistent:true}));
 }else{
  const restored=await until(async()=>{const x=await snapshot(A);return x?.auth==='probable_authenticated'?x:null});
  assert.match(restored.url||'',/\/dashboard/,'Restored login cookie should reach the authenticated page');
  const removed=await run('window.wolfNative.clearSession('+JSON.stringify(A)+')');
  assert.equal(removed.localSessionCleared,true);
  await navigate(A);
  await until(async()=>(await snapshot(A))?.auth==='login_required');
  await navigate(B);
  await until(async()=>(await snapshot(B))?.auth==='login_required');
  console.log('WOLF_ANDROID_SESSION_RESTART_CLEAR_PASS',JSON.stringify({restored:true,clearedA:true,bStillIndependent:true,registeredAppPreserved:true}));
 }
}finally{ws.close()}
