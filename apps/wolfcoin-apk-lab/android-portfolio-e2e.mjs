/* End-to-end Android WebView application and isolated browser via Android Emulator/CDP. */
import assert from 'node:assert/strict';
const port=Number(process.env.WOLF_WEBVIEW_CDP_PORT||9223);
const endpoint='http://127.0.0.1:'+port;
const sleep=n=>new Promise(r=>setTimeout(r,n));
async function targets(){return(await(await fetch(endpoint+'/json')).json()).filter(x=>x.type==='page')}
async function until(f,n=55){for(let i=0;i<n;i++){const x=await f();if(x)return x;await sleep(180)}throw Error('WebView state timed out')}
async function attach(t){
 let id=0;const pending=new Map(),ws=new WebSocket(t.webSocketDebuggerUrl.replace(/127\.0\.0\.1:\d+/,'127.0.0.1:'+port));
 await new Promise((resolve,reject)=>{ws.onopen=resolve;ws.onerror=reject});
 ws.onmessage=e=>{const m=JSON.parse(e.data);if(m.id&&pending.has(m.id)){const p=pending.get(m.id);pending.delete(m.id);m.error?p.reject(new Error(m.error.message)):p.resolve(m.result)}};
 return {eval:async expression=>{const x=await new Promise((resolve,reject)=>{const n=++id;pending.set(n,{resolve,reject});ws.send(JSON.stringify({id:n,method:'Runtime.evaluate',params:{expression,returnByValue:true,awaitPromise:true}}))});if(x.exceptionDetails)throw Error(x.exceptionDetails.exception?.description||x.exceptionDetails.text);return x.result?.value},close:()=>ws.close()};
}
const ui=await attach(await until(async()=>(await targets()).find(t=>t.url?.includes('appassets.androidplatform.net/assets/wolfcoin.html'))));
const output={};
async function siteLogin(url){
 const page=await until(async()=>(await targets()).find(t=>t.url===url));
 const s=await attach(page);
 try{
  await until(async()=>{try{return await s.eval("!!document.querySelector('[name=user]')")}catch{return false}},70);
  await s.eval("(()=>{document.querySelector('[name=user]').value='fixture';document.querySelector('[name=pass]').value='fixture';document.querySelector('form').requestSubmit();return true})()");
 }finally{s.close()}
}
async function connectAccount(url,name){
 await ui.eval("(()=>{document.querySelector('[data-tab=platforms]').click();document.querySelector('[data-action=add-account]').click();const f=document.querySelector('#account-form');f.querySelector('[name=name]').value="+JSON.stringify(name)+";f.querySelector('[name=url]').value="+JSON.stringify(url)+";f.querySelector('[name=type]').value='Betting';f.requestSubmit();return true})()");
 await until(async()=>await ui.eval("state.tab==='browser'"));
 const account=JSON.parse(await ui.eval("JSON.stringify(state.accounts.find(x=>x.name==="+JSON.stringify(name)+"))"));
 assert(account);
 await siteLogin(url);
 await sleep(350);
 await ui.eval("document.querySelector('[data-action=sync-current]').click()");
 const a=await until(async()=>{
  const x=JSON.parse(await ui.eval("JSON.stringify(state.accounts.find(x=>x.id==="+JSON.stringify(account.id)+"))"));
  return x?.ownerEvidence?.displayName==='Alex Example'&&x?.status==='connected'?x:null;
 },70);
 assert.equal(a.balance,750);
 return {id:a.id,connected:a.status,owner:a.ownerEvidence.displayName};
}
try{
 await until(async()=>await ui.eval("window.WOLF_DXQT?.status==='ready'&&!!window.WolfPortfolio"));
 const host=await ui.eval("window.wolfNative.status()");
 assert.equal(host.multiProfile,true,'Emulator WebView profile isolation unavailable');
 assert.equal(await ui.eval("state.accounts.length"),0);
 output.first=await connectAccount('http://10.0.2.2:44567/login','Android Sports A');
 output.second=await connectAccount('http://10.0.2.2:44568/login','Android Sports B');
 await ui.eval("document.querySelector('[data-tab=accounts]').click()");
 const suggestions=await ui.eval("window.WolfPortfolio.snapshot().matches.length");
 assert.equal(suggestions,1);
 await ui.eval("document.querySelector('[data-pf=link]').click()");
 assert.equal(await ui.eval("state.portfolio.groups.length"),1);
 await ui.eval("document.querySelector('[data-tab=finance]').click()");
 const comparisons=JSON.parse(await ui.eval("JSON.stringify(window.WolfPortfolio.snapshot().comparisons)"));
 assert.equal(comparisons.length,1);
 assert.equal(comparisons[0].best.quote,2.3);
 await ui.eval("document.querySelector('[data-pf=propose]').click()");
 assert.equal(await ui.eval("state.portfolio.proposals.length"),1);
 output.portfolio={suggestions,links:1,bestOdds:2.3,queued:1};
 console.log('WOLF_ANDROID_PORTFOLIO_E2E_PASS '+JSON.stringify(output));
}finally{ui.close()}
