import assert from 'node:assert/strict';
const port=Number(process.env.WOLF_TEST_CDP_PORT||13997);
const fixture=process.env.WOLF_TEST_FIXTURE||'http://127.0.0.1:44727/login';
assert.equal(new URL(fixture).hostname,'127.0.0.1','local fixture only');
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));
let target;
for(let i=0;i<80;i++){try{target=(await(await fetch('http://127.0.0.1:'+port+'/json')).json()).find(x=>x.type==='page'&&x.url?.startsWith('file:'));if(target)break;}catch{}await sleep(100)}
assert(target);
const ws=new WebSocket(target.webSocketDebuggerUrl);
await new Promise((yes,no)=>{ws.onopen=yes;ws.onerror=no});
let seq=0;const pending=new Map();
ws.onmessage=e=>{const m=JSON.parse(e.data);const p=pending.get(m.id);if(p){pending.delete(m.id);m.error?p.reject(Error(m.error.message)):p.resolve(m.result)}};
const evaluate=async expression=>{
 const result=await new Promise((resolve,reject)=>{const id=++seq;pending.set(id,{resolve,reject});ws.send(JSON.stringify({id,method:'Runtime.evaluate',params:{expression,returnByValue:true,awaitPromise:true}}))});
 if(result.exceptionDetails)throw Error(result.exceptionDetails.exception?.description||result.exceptionDetails.text);
 return result.result?.value;
};
async function until(fn,n=90){for(let i=0;i<n;i++){try{const v=await fn();if(v)return v}catch{}await sleep(150)}throw Error('Read-only native account evidence not ready')}
const id='compact-wallet-fixture';
const a={id,name:'Controlled wallet',type:'Betting',url:fixture,user:'Fixture',financialCurrency:'ZMW',status:'unverified',balance:null,pending:null,pnl:null,known:false,sync:'Not synchronized',device:'Wolf Browser'};
const snap=()=>evaluate("window.wolfNative.snapshot({accountId:"+JSON.stringify(id)+"})");
const account=async()=>(await evaluate('window.wolfBackend.snapshot()')).accounts.find(x=>x.account_id===id);
try{
 await until(()=>evaluate('window.WolfNativeIntegration?.ready'));
 await evaluate('state.accounts.push('+JSON.stringify(a)+');createTab('+JSON.stringify(fixture)+','+JSON.stringify(id)+')');
 await until(async()=>(await snap())?.auth==='login_required');
 for(const [selector,text] of [['input[name=user]','fixture'],['input[name=pass]','fixture']]){
  const r=await evaluate('window.wolfNative.action('+JSON.stringify({accountId:id,type:'fill',selector,text})+')');
  assert.equal(r.ok,true);
 }
 assert.equal((await evaluate('window.wolfNative.action('+JSON.stringify({accountId:id,type:'click',selector:'button[type=submit]'})+')')).ok,true);
 await until(async()=>(await snap())?.auth==='probable_authenticated');
 const panel=new URL('/compact-wallet',fixture).href;
 await evaluate('visitAddress('+JSON.stringify(panel)+')');
 const observed=await until(async()=>{const s=await snap();return s?.authEvidence?.accountPanelAuthenticated?s:null});
 assert.equal(observed.candidates.balance.value,3.5);
 await evaluate('syncNativeAccount('+JSON.stringify(id)+')');
 const connected=await until(async()=>{const x=await account();return x?.session_state==='ACTIVE'&&x.latest_financial?.fields?.cash_balance==='3.5'?x:null});
 await evaluate("window.wolfBackend.request('host.startup',{host_instance_id:'fixture_restart_revalidation'}).then(()=>window.WolfNativeIntegration.refresh())");
 assert.equal((await account()).session_state,'PAUSED');
 assert.equal(await evaluate("state.accounts.find(a=>a.id==="+JSON.stringify(id)+").status"),'unverified');
 await evaluate('syncAll()');
 const recovered=await until(async()=>{const x=await account();return x?.session_state==='ACTIVE'&&x.latest_financial?.fields?.cash_balance==='3.5'?x:null});
 assert.equal(new URL((await snap()).url).pathname,'/compact-wallet','read-only refresh must preserve same-origin account page');
 assert(recovered.observation_count>connected.observation_count);
 console.log('WOLF_COMPACT_WALLET_SIGNED_NATIVE_RECOVERY_PASS',JSON.stringify({balance:3.5,currency:'ZMW',previousState:'PAUSED',recoveredState:'ACTIVE',observations:recovered.observation_count,accountPagePreserved:true,syntheticFixture:true}));
}finally{ws.close()}
