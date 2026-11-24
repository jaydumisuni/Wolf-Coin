import assert from 'node:assert/strict';
const port=Number(process.env.WOLF_TEST_CDP_PORT||13927);
const targets=await(await fetch('http://127.0.0.1:'+port+'/json')).json();
const target=targets.find(x=>x.url?.startsWith('file:')&&x.type==='page');
assert(target);
const ws=new WebSocket(target.webSocketDebuggerUrl);
await new Promise((resolve,reject)=>{ws.onopen=resolve;ws.onerror=reject});
const pending=new Map();let id=0;
ws.onmessage=e=>{const m=JSON.parse(e.data);if(m.id&&pending.has(m.id)){
 const p=pending.get(m.id);pending.delete(m.id);
 m.error?p.reject(Error(m.error.message)):p.resolve(m.result);
}};
async function evaljs(expression){
 const r=await new Promise((resolve,reject)=>{
  const n=++id;pending.set(n,{resolve,reject});
  ws.send(JSON.stringify({id:n,method:'Runtime.evaluate',params:{expression,returnByValue:true,awaitPromise:true}}));
 });
 if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description||r.exceptionDetails.text);
 return r.result.value;
}
try{
 const before=JSON.parse(await evaljs('JSON.stringify({ready:window.WolfNativeIntegration?.ready,accounts:state.accounts.length})'));
 assert.equal(before.ready,true);
 assert.equal(before.accounts,2);
 const result=await evaljs('window.wolfBackend.syncAll(state.accounts)');
 assert.equal(result.results.length,2);
 assert(result.results.every(x=>x.status==='OBSERVED'),JSON.stringify(result.results));
 assert.equal(result.backend.accounts.length,2);
 assert(result.backend.history.every(h=>h.observations.length>0));
 await evaljs('window.WolfNativeIntegration.refresh()');
 console.log('WOLF_NATIVE_CROSS_PLATFORM_SYNC_ALL_PASS '+JSON.stringify({
  results:result.results.map(x=>({id:x.id,status:x.status,auth:x.auth})),
  backendAccounts:result.backend.accounts.length,
  observations:result.backend.history.map(x=>x.observations.length)}));
}finally{ws.close()}
