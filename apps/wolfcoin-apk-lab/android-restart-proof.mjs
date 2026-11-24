/* Verify state persistence + native WebView session isolation across Android restart. */
import assert from 'node:assert/strict';
const port=Number(process.env.WOLF_WEBVIEW_CDP_PORT||9223);
const endpoint='http://127.0.0.1:'+port;
const sleep=n=>new Promise(r=>setTimeout(r,n));
const list=()=>fetch(endpoint+'/json').then(r=>r.json());
async function attach(t){
 let id=0;const pending=new Map(),ws=new WebSocket(t.webSocketDebuggerUrl.replace(/127\.0\.0\.1:\d+/,'127.0.0.1:'+port));
 await new Promise((resolve,reject)=>{ws.onopen=resolve;ws.onerror=reject});
 ws.onmessage=e=>{const m=JSON.parse(e.data);if(m.id&&pending.has(m.id)){
 const p=pending.get(m.id);pending.delete(m.id);m.error?p.reject(new Error(m.error.message)):p.resolve(m.result)}};
 return {eval:async expression=>{const r=await new Promise((resolve,reject)=>{const n=++id;pending.set(n,{resolve,reject});ws.send(JSON.stringify({id:n,method:'Runtime.evaluate',params:{expression,awaitPromise:true,returnByValue:true}}))});if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description||r.exceptionDetails.text);return r.result?.value;},close:()=>ws.close()};
}
async function until(f,n=55){for(let i=0;i<n;i++){const d=await f();if(d)return d;await sleep(200)}throw Error('Timed out waiting for WebView state')}
const ui=await attach(await until(async()=>(await list()).find(x=>x.url?.includes('appassets.androidplatform.net/assets/wolfcoin.html'))));
const result={};
try{
 await until(async()=>await ui.eval("window.WOLF_DXQT?.status==='ready'&&!!window.WolfPortfolio"));
 const state=JSON.parse(await ui.eval("JSON.stringify({accounts:state.accounts.map(a=>({id:a.id,status:a.status,balance:a.balance})),groups:state.portfolio?.groups?.length,proposals:state.portfolio?.proposals?.length})"));
 assert.equal(state.accounts.length,2);
 assert.equal(state.groups,1);
 assert.equal(state.proposals,1);
 assert(state.accounts.every(a=>a.status==='unverified'&&a.balance===750),'Restored values must be stale until revalidated');
 result.persisted=state;
 await ui.eval("window.wolfNative.browserBounds({x:0,y:90,width:350,height:520})");
 const first=state.accounts[0].id;
 await ui.eval("window.wolfNative.showBrowser({accountId:"+JSON.stringify(first)+",url:'http://10.0.2.2:44567/login'})");
 const known=await until(async()=>{try{const a=await ui.eval("window.wolfNative.snapshot({accountId:"+JSON.stringify(first)+"})");return a?.auth==='probable_authenticated'?a:null;}catch{return null}},65);
 assert.equal(known.identity?.displayName,'Alex Example');
 result.cookieRestore={accountId:first,auth:known.auth,owner:known.identity.displayName};
 await ui.eval("window.wolfNative.hideBrowser()");
 const probe='lab_new_unpaired_account';
 await ui.eval("window.wolfNative.showBrowser({accountId:"+JSON.stringify(probe)+",url:'http://10.0.2.2:44567/login'})");
 const fresh=await until(async()=>{try{const a=await ui.eval("window.wolfNative.snapshot({accountId:"+JSON.stringify(probe)+"})");return a?.auth==='login_required'?a:null;}catch{return null}},65);
 assert.equal(fresh.auth,'login_required','Unregistered native profile must not inherit owner cookie');
 await ui.eval("window.wolfNative.clearSession("+JSON.stringify(probe)+")");
 result.isolation={probeAuth:fresh.auth,crossProfileCookieLeak:false};
 console.log('WOLF_ANDROID_RESTART_AND_PROFILE_PROOF_PASS '+JSON.stringify(result));
}finally{ui.close()}
