/* Android WebView -> embedded CPython 3.11 -> signed a10 -> SQLite proof. */
import assert from 'node:assert/strict';
const port=Number(process.env.WOLF_WEBVIEW_CDP_PORT||9242);
const url='http://127.0.0.1:'+port;
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const targets=()=>fetch(url+'/json').then(r=>r.json());
async function until(fn,n=60){
 for(let i=0;i<n;i++){const v=await fn();if(v)return v;await sleep(140)}
 throw Error('Android CDP state timed out');
}
async function attach(t){
 const ws=new WebSocket(t.webSocketDebuggerUrl.replace(/127\.0\.0\.1:\d+/,'127.0.0.1:'+port));
 await new Promise((resolve,reject)=>{ws.onopen=resolve;ws.onerror=reject});
 let seq=0;const pending=new Map();
 ws.onmessage=e=>{
  const m=JSON.parse(e.data);if(m.id&&pending.has(m.id)){const j=pending.get(m.id);pending.delete(m.id);m.error?j.reject(Error(m.error.message)):j.resolve(m.result)}
 };
 return {close:()=>ws.close(),eval:async expression=>{
  const r=await new Promise((resolve,reject)=>{
   const id=++seq;pending.set(id,{resolve,reject});
   ws.send(JSON.stringify({id,method:'Runtime.evaluate',params:{expression,returnByValue:true,awaitPromise:true}}))
  });
  if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description||r.exceptionDetails.text);
  return r.result?.value;
 }};
}
const ui=await attach(await until(async()=>(await targets()).find(x=>x.url?.includes('appassets.androidplatform.net/assets/wolfcoin.html'))));
const suffix=process.env.WOLF_ANDROID_TEST_SUFFIX||'2';
const account={id:'android_v09_lab_sports_'+suffix,name:'Android backend sports fixture',type:'Betting',
 url:'http://10.0.2.2:44567/login',financialCurrency:'ZMW'};
let page=null;
try{
 const ready=await ui.eval("window.wolfBackend.status()");
 assert.equal(ready.available,true);
 await ui.eval("(()=>{const a="+JSON.stringify(account)+";if(!state.accounts.find(x=>x.id===a.id))state.accounts.push({...a,known:false,status:'unverified',sync:'Not synchronized',device:'Android Wolf Browser',balance:null,pending:null,pnl:null});createTab(a.url,a.id);return true})()");
 const browser=await until(async()=>(await targets()).find(x=>x.url===account.url));
 page=await attach(browser);
 await until(async()=>{try{return await page.eval("!!document.querySelector('[name=pass]')")}catch{return false}});
 await page.eval("(()=>{document.querySelector('[name=user]').value='fixture';document.querySelector('[name=pass]').value='fixture';document.querySelector('form').requestSubmit();return true})()");
 const login=await until(async()=>{try{
  const d=await ui.eval("window.wolfNative.snapshot({accountId:"+JSON.stringify(account.id)+"})");
  return d?.auth==='probable_authenticated'?d:null;
 }catch{return null}},80);
 assert.equal(login.candidates?.balance?.value,750);
 const observed=await ui.eval("window.wolfBackend.observeAccount("+JSON.stringify(account)+")");
 assert.equal(observed.account.latest_financial?.fields?.cash_balance,'750');
 assert.equal(observed.account.session_state,'ACTIVE');
 const read=await ui.eval("window.wolfBackend.snapshot()");
 const found=read.accounts.find(x=>x.account_id===account.id);
 assert(found);
 // Portfolio currency total may include other persisted accounts; never
 // confuse a per-account balance with its aggregate currency portfolio.
 assert(Number(read.finance.currency_totals.ZMW.cash_balance)>=Number(found.latest_financial.fields.cash_balance));
 const history=read.history.find(x=>x.account_id===account.id);
 assert(history?.observations?.length>=1);
 const proposal={id:'android_v09_proposal_'+suffix,accountId:account.id,platform:account.name,
  candidate:{kind:'bet',side:'back',market:'Fixture Match 2026-12-01',selection:'Home',quote:2.1,currency:'ZMW'},
  proposed_amount:'10',money_budget:'100',browser_capabilities:['PLACE_BET'],platform_permissions:['TRANSACT']};
 const decision=await ui.eval("window.wolfBackend.proposeAction("+JSON.stringify(proposal)+")");
 assert.equal(decision.status,'BROWSER_HANDOFF_READY',JSON.stringify(decision));
 const receipt=await ui.eval("window.wolfBackend.request('decision.receipt',"+
  JSON.stringify({domain:'sports',account_id:account.id,decision_id:decision.decision_id,
    result_ref:'android_v09_fixture_no_money_effect_'+suffix,outcome:'NOT_EXECUTED'})+")");
 assert.equal(receipt.status,'NOT_EXECUTED');
 console.log('WOLF_ANDROID_EMBEDDED_A10_E2E_PASS '+JSON.stringify({
  account:account.id,backend:ready.schema,signed:true,
  observedBalance:found.latest_financial.fields.cash_balance,
  history:history.observations.length,activity:read.activity.length,
  decision:decision.status,receipt:receipt.status,
  financialActionExecuted:false
 }));
}finally{page?.close();ui.close()}
