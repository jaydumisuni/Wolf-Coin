import assert from 'node:assert/strict';
const port=Number(process.env.WOLF_WEBVIEW_CDP_PORT||9242);
const pages=await(await fetch('http://127.0.0.1:'+port+'/json')).json();
const t=pages.find(x=>x.type==='page'&&x.url?.includes('appassets.androidplatform.net/assets/wolfcoin.html'));
assert(t);
const ws=new WebSocket(t.webSocketDebuggerUrl.replace(/127\.0\.0\.1:\d+/,'127.0.0.1:'+port));
await new Promise((yes,no)=>{ws.onopen=yes;ws.onerror=no});
let seq=0;const pending=new Map();
ws.onmessage=e=>{const m=JSON.parse(e.data);if(m.id&&pending.has(m.id)){const p=pending.get(m.id);pending.delete(m.id);m.error?p.reject(Error(m.error.message)):p.resolve(m.result)}};
async function run(expression){
 const r=await new Promise((resolve,reject)=>{const id=++seq;pending.set(id,{resolve,reject});ws.send(JSON.stringify({id,method:'Runtime.evaluate',params:{expression,returnByValue:true,awaitPromise:true}}))});
 if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description||r.exceptionDetails.text);
 return r.result?.value;
}
try{
 const initial=JSON.parse(await run("JSON.stringify({ready:window.WolfNativeIntegration?.ready,backend:window.WolfNativeIntegration?.snapshot})"));
 assert.equal(initial.ready,true);
 const accountId=process.env.WOLF_ANDROID_ACCOUNT_ID||'android_v09_lab_sports_3';
 assert(initial.backend.accounts.some(x=>x.account_id===accountId));
 await run("document.querySelector('[data-tab=overview]').click()");
 const overview=await run("document.querySelector('#main').textContent");
 assert(overview.includes('Backend Financial Snapshot'));
 await run("document.querySelector('[data-tab=finance]').click()");
 const finance=await run("document.querySelector('#main').textContent");
 assert(finance.includes('Native backend observations'));
 assert(finance.includes('Balance History'));
 await run("document.querySelector('[data-tab=activity]').click()");
 const activity=await run("document.querySelector('#main').textContent");
 assert(activity.includes('Native backend audit history'));
 assert(activity.includes('observation.ingest'));
 console.log('WOLF_ANDROID_BACKEND_NINE_SCREEN_BINDING_PASS '+JSON.stringify({
  registered:initial.backend.accounts.length,currencies:Object.keys(initial.backend.finance.currency_totals||{}),
  observationHistory:initial.backend.history.reduce((sum,x)=>sum+x.observations.length,0),
  audit:initial.backend.activity.length,
  overview:true,finance:true,history:true,activity:true
 }));
}finally{ws.close()}
