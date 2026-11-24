/* Real WebView DevTools proof, requires Android debug APK with WebView debugging enabled. */
import assert from 'node:assert/strict';
const port=Number(process.env.WOLF_WEBVIEW_CDP_PORT||9223);
const base='http://127.0.0.1:'+port;
const list=await(await fetch(base+'/json')).json();
const t=list.find(x=>x.url?.includes('appassets.androidplatform.net/assets/wolfcoin.html'));
assert(t,'Wolf-Coin appassets WebView not present');
let index=0;
const pending=new Map(),ws=new WebSocket(t.webSocketDebuggerUrl.replace(/127\.0\.0\.1:\d+/, '127.0.0.1:'+port));
await new Promise((resolve,reject)=>{ws.onopen=resolve;ws.onerror=reject});
ws.onmessage=e=>{const m=JSON.parse(e.data);if(m.id&&pending.has(m.id)){
 const p=pending.get(m.id);pending.delete(m.id);m.error?p.reject(new Error(m.error.message)):p.resolve(m.result);
}};
async function evaluate(expression){
 const result=await new Promise((resolve,reject)=>{
   const id=++index;pending.set(id,{resolve,reject});
   ws.send(JSON.stringify({id,method:'Runtime.evaluate',params:{expression,awaitPromise:true,returnByValue:true}}))
 });
 if(result.exceptionDetails)throw new Error(result.exceptionDetails.exception?.description||result.exceptionDetails.text);
 return result.result?.value;
}
try{
 let status=null;
 for(let i=0;i<45;i++){
  status=await evaluate('window.WOLF_DXQT?.status');
  if(status==='ready'||status==='error')break;
  await new Promise(r=>setTimeout(r,120));
 }
 const host=await evaluate("typeof window.wolfNative==='object' ? window.wolfNative.status() : null");
 const ui=JSON.parse(await evaluate("JSON.stringify({tabs:NAV.map(x=>x[0]),accounts:state.accounts.length,portfolio:!!window.WolfPortfolio,origin:location.origin,dxqt:window.WOLF_DXQT?.status})"));
 assert.equal(ui.tabs.length,9);
 assert.equal(ui.accounts,0);
 assert.equal(ui.dxqt,'ready','D-XQT not initialized on Android');
 assert(ui.portfolio);
 assert.equal(host?.schema,'wolf.browser.v1');
 assert.equal(host?.host,'android');
 console.log('WOLF_ANDROID_EMULATOR_WEBVIEW_PASS '+JSON.stringify({ui,host}));
}finally{ws.close()}
