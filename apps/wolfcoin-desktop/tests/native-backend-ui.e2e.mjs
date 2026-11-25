/* Read actual UI/backend state from an already exercised isolated Chromium fixture. */
import assert from 'node:assert/strict';
const port=Number(process.env.WOLF_TEST_CDP_PORT||13923);
const url='http://127.0.0.1:'+port;
const targets=await(await fetch(url+'/json')).json();
const item=targets.find(x=>x.type==='page'&&x.url.startsWith('file:'));
assert(item,'Wolf UI not open');
const ws=new WebSocket(item.webSocketDebuggerUrl);
await new Promise((yes,no)=>{ws.onopen=yes;ws.onerror=no});
let id=0;const pending=new Map();
ws.onmessage=e=>{const m=JSON.parse(e.data);if(m.id&&pending.has(m.id)){
 const a=pending.get(m.id);pending.delete(m.id);m.error?a.reject(Error(m.error.message)):a.resolve(m.result);
}};
const evaluate=async expression=>{
 const r=await new Promise((resolve,reject)=>{const n=++id;pending.set(n,{resolve,reject});
 ws.send(JSON.stringify({id:n,method:'Runtime.evaluate',params:{expression,returnByValue:true,awaitPromise:true}}))});
 if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description||r.exceptionDetails.text);
 return r.result?.value;
};
try{
 let snap;
 for(let i=0;i<30;i++){
  snap=JSON.parse(await evaluate("JSON.stringify({ready:window.WolfNativeIntegration?.ready, data:window.WolfNativeIntegration?.snapshot})"));
  if(snap.ready&&snap.data?.history?.length)break;
  await new Promise(r=>setTimeout(r,100));
 }
 assert.equal(snap.ready,true);
 assert.equal(snap.data.accounts.length,1);
 assert(snap.data.history[0].observations.length>0);
 assert(snap.data.activity.length>0);
 await evaluate("document.querySelector('[data-tab=overview]').click()");
 const overviewText=await evaluate("document.querySelector('#main').textContent");
 assert(overviewText.includes('Backend Financial Snapshot'));
 assert(overviewText.includes('Balance History'));
 assert(!overviewText.includes('Demo data · not live'));
 await evaluate("document.querySelector('[data-tab=finance]').click()");
 const financeText=await evaluate("document.querySelector('#main').textContent");
 assert(financeText.includes('Native backend observations'));
 assert(financeText.includes('Transactions'));
 assert(financeText.includes('Balance History'));
 assert(!financeText.includes('Recorded Deposits (illustrative)'));
 await evaluate("document.querySelector('[data-tab=activity]').click()");
 const activityText=await evaluate("document.querySelector('#main').textContent");
 assert(activityText.includes('Recorded bets, trades, transaction outcomes and signed audit trail'));
 assert(activityText.includes('observation.ingest'));
 assert.equal(await evaluate("document.querySelectorAll('[data-action=backend-event-details]').length>0"),true);
 await evaluate("document.querySelector('[data-action=backend-event-details]').click()");
 const detailText=await evaluate("document.querySelector('#modalRoot').textContent");
 assert(detailText.includes('Event')&&detailText.includes('Timestamp'),detailText);
 console.log('WOLF_NATIVE_FINANCIAL_ACTIVITY_UI_PASS '+JSON.stringify({registered:1,observations:snap.data.history[0].observations.length,auditEvents:snap.data.activity.length,financeReal:true,activityReal:true}));
}finally{ws.close()}
