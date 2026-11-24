/* Android native OAuth-style WebView popup, account-profile cookie sharing. */
import assert from 'node:assert/strict';
const port=Number(process.env.WOLF_WEBVIEW_CDP_PORT||9223);
const url='http://127.0.0.1:'+port;
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
async function targets(){return(await(await fetch(url+'/json')).json()).filter(x=>x.type==='page')}
async function until(f,tries=55){for(let i=0;i<tries;i++){const d=await f();if(d)return d;await sleep(150)}throw Error('Timed out waiting for WebView popup')}
async function attach(t){
 let id=0;const pending=new Map(),ws=new WebSocket(t.webSocketDebuggerUrl.replace(/127\.0\.0\.1:\d+/,'127.0.0.1:'+port));
 await new Promise((resolve,reject)=>{ws.onopen=resolve;ws.onerror=reject});
 ws.onmessage=e=>{const m=JSON.parse(e.data);if(m.id&&pending.has(m.id)){const p=pending.get(m.id);pending.delete(m.id);m.error?p.reject(Error(m.error.message)):p.resolve(m.result)}};
 return {eval:async expression=>{const r=await new Promise((resolve,reject)=>{
   const n=++id;pending.set(n,{resolve,reject});ws.send(JSON.stringify({id:n,method:'Runtime.evaluate',params:{expression,returnByValue:true,awaitPromise:true}}))});
  if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description||r.exceptionDetails.text);
  return r.result?.value;},close:()=>ws.close()};
}
const ui=await attach(await until(async()=>(await targets()).find(x=>x.url?.includes('appassets.androidplatform.net/assets/wolfcoin.html'))));
const id=process.env.WOLF_POPUP_ACCOUNT_ID||'oauth_lab_account_01';
let parent=null,popup=null;
try{
 await ui.eval("window.wolfNative.showBrowser({accountId:"+JSON.stringify(id)+",url:'http://10.0.2.2:44567/login'})");
 const main=await until(async()=>(await targets()).find(x=>x.url==='http://10.0.2.2:44567/login'));
 parent=await attach(main);
 await until(async()=>{try{return await parent.eval("!!document.querySelector('form')")}catch{return false}});
 await parent.eval("(()=>{window.open('http://10.0.2.2:44567/login','wolf_oauth_lab_popup');return true})()");
 const popTarget=await until(async()=>(await targets()).find(x=>x.url?.includes('10.0.2.2:44567/login')&&x.id!==main.id));
 popup=await attach(popTarget);
 await until(async()=>{try{return await popup.eval("!!document.querySelector('[name=pass]')")}catch{return false}});
 await popup.eval("(()=>{document.querySelector('[name=user]').value='fixture';document.querySelector('[name=pass]').value='fixture';document.querySelector('form').requestSubmit();return true})()");
 await until(async()=>{try{return await popup.eval("document.title==='Fixture Sports Wallet'")}catch{return false}},65);
 await popup.eval("window.close();true");
 // Original browser shares named profile with popup. A reload now sees login cookie.
 await ui.eval("window.wolfNative.reload()");
 const snap=await until(async()=>{try{
   const x=await ui.eval("window.wolfNative.snapshot({accountId:"+JSON.stringify(id)+"})");
   return x?.auth==='probable_authenticated'?x:null;
  }catch{return null}},65);
 assert.equal(snap.identity?.displayName,'Alex Example');
 assert.equal(snap.candidates?.balance?.value,750);
 console.log('WOLF_ANDROID_OAUTH_POPUP_PROFILE_PASS '+JSON.stringify({
  popupOpened:true,popupAuthenticated:true,originalProfileAuthenticated:true,
  balance:snap.candidates.balance.value,accountId:id,provider:'local_fixture'
 }));
}finally{popup?.close();parent?.close();ui.close()}
