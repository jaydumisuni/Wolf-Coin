import assert from 'node:assert/strict';
const port=Number(process.env.WOLF_WEBVIEW_CDP_PORT||9268);
const root='http://127.0.0.1:'+port;
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const getTargets=async()=>(await(await fetch(root+'/json')).json()).filter(x=>x.type==='page');
async function attach(t){
 const ws=new WebSocket(t.webSocketDebuggerUrl.replace(/127\.0\.0\.1:\d+/,'127.0.0.1:'+port));
 await new Promise((yes,no)=>{ws.onopen=yes;ws.onerror=no});
 let n=0;const pending=new Map();
 ws.onmessage=e=>{const m=JSON.parse(e.data);if(m.id&&pending.has(m.id)){const p=pending.get(m.id);pending.delete(m.id);m.error?p.reject(Error(m.error.message)):p.resolve(m.result)}};
 return {eval:async expression=>{
  const r=await new Promise((resolve,reject)=>{const id=++n;pending.set(id,{resolve,reject});ws.send(JSON.stringify({id,method:'Runtime.evaluate',params:{expression,returnByValue:true,awaitPromise:true}}))});
  if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description||r.exceptionDetails.text);return r.result?.value;
 },close:()=>ws.close()};
}
async function until(fn,n=110){for(let i=0;i<n;i++){try{const value=await fn();if(value)return value}catch{}await sleep(150)}throw Error('Android vault acceptance timed out')}
const ui=await attach(await until(async()=>(await getTargets()).find(x=>x.url?.includes('/assets/wolfcoin.html'))));
const primary='http://10.0.2.2:44567/login',foreign='http://10.0.2.2:44568/login';
const username='wolf-v093-vault-canary',password='V093TemporaryCanary!';
const mode=process.env.WOLF_VAULT_TEST_MODE||'first';
const runId=String(Date.now());
const account='wolf_v093_vault_primary_'+runId,foreignAccount='wolf_v093_vault_other_'+runId;
let page=null;
try{
 const status=await ui.eval('window.wolfNative.vaultStatus()');
 assert.equal(status.available,true);
 assert.equal(status.plaintextFallback,false);
 assert.match(status.backend,/AndroidKeyStore/);
 if(mode==='first'){
  const saved=await ui.eval('window.wolfNative.vaultSave('+JSON.stringify({url:primary,username,password,autofill:true})+')');
  assert.equal(saved.ok,true);
 }
 const list=await ui.eval('window.wolfNative.vaultList()');
 assert(list.items.some(x=>x.username===username && x.origin==='http://10.0.2.2:44567'));
 assert(!JSON.stringify(list).includes(password),'Password leaked through list metadata');
 await ui.eval('createTab('+JSON.stringify(primary)+','+JSON.stringify(account)+')');
 const first=await until(async()=>(await getTargets()).find(x=>x.url===primary));
 page=await attach(first);
 const filled=await until(async()=>{
   const x=await page.eval("(()=>{const u=document.querySelector('[name=user]'),p=document.querySelector('[name=pass]');return {form:!!u&&!!p,user:u?.value,pass:p?.value,url:location.href}})()");
   return x?.user===username&&x?.pass===password?x:false;
 });
 assert.equal(filled.url,primary,'Autofill must never submit a login');
 const manual=await ui.eval('window.wolfNative.vaultFill('+JSON.stringify({accountId:account})+')');
 assert.equal(manual.filled,true);
 assert.equal(manual.submitted,false);
 page.close();page=null;
 await ui.eval('createTab('+JSON.stringify(foreign)+','+JSON.stringify(foreignAccount)+')');
 const other=await until(async()=>(await getTargets()).find(x=>x.url===foreign));
 page=await attach(other);
 const foreignBlank=await until(async()=>{
  const x=await page.eval("(()=>{const u=document.querySelector('[name=user]'),p=document.querySelector('[name=pass]');return {ready:!!u&&!!p,user:u?.value,pass:p?.value}})()");
  return x.ready?x:null;
 });
 assert.notEqual(foreignBlank.pass,password,'Secret injected into different origin');
 assert.notEqual(foreignBlank.user,username,'Username injected into different origin');
 const mismatch=await ui.eval('window.wolfNative.vaultFill('+JSON.stringify({accountId:foreignAccount})+')');
 assert.equal(mismatch.filled,false);
 if(mode==='restart'){
  const deleted=await ui.eval('window.wolfNative.vaultDelete('+JSON.stringify({origin:primary})+')');
  assert.equal(deleted.deleted,true);
  const after=await ui.eval('window.wolfNative.vaultList()');
  assert(!after.items.some(x=>x.username===username));
 }
 console.log('WOLF_ANDROID_KEYSTORE_VAULT_ORIGIN_PASS',JSON.stringify({mode,backend:status.backend,encryptedAtRest:true,exactOrigin:true,autofill:true,manualFill:true,submitted:false,crossOriginLeak:false,listedPassword:false,deleted:mode==='restart'}));
}finally{page?.close();ui.close()}
