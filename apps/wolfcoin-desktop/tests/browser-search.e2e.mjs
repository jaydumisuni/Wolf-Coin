import assert from 'node:assert/strict';
const port=Number(process.env.WOLF_TEST_CDP_PORT||13968);
const host='http://127.0.0.1:'+port;
const targets=async()=>(await(await fetch(host+'/json')).json()).filter(t=>t.type==='page');
const app=(await targets()).find(t=>process.env.WOLF_ANDROID==='1'?t.url?.includes('/assets/wolfcoin.html'):t.url?.startsWith('file:'));
assert(app,'Wolf UI target unavailable');
const ws=new WebSocket(app.webSocketDebuggerUrl.replace(/127\.0\.0\.1:\d+/,'127.0.0.1:'+port));
await new Promise((resolve,reject)=>{ws.onopen=resolve;ws.onerror=reject});
let i=0;const pending=new Map();
ws.onmessage=e=>{const m=JSON.parse(e.data);if(pending.has(m.id)){const p=pending.get(m.id);pending.delete(m.id);m.error?p.reject(Error(m.error.message)):p.resolve(m.result)}};
async function evalJS(expression){
 const r=await new Promise((resolve,reject)=>{const id=++i;pending.set(id,{resolve,reject});ws.send(JSON.stringify({id,method:'Runtime.evaluate',params:{expression,returnByValue:true,awaitPromise:true}}))});
 if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description||r.exceptionDetails.text);
 return r.result.value;
}
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
async function waitFor(predicate,tries=55){
 for(let i=0;i<tries;i++){const x=await predicate();if(x)return x;await sleep(200)}
 throw Error('Browser page did not navigate');
}
try{
 await evalJS("createTab('')");
 await evalJS("navigate('browser')");
 await evalJS("(()=>{const form=document.querySelector('#browser-address-form'),input=form.querySelector('input[name=address]');input.value='Lusaka weather forecast';form.requestSubmit();return true})()");
 const googleUrl=await evalJS("getActiveBrowser().url");
 assert.equal(googleUrl,'https://www.google.com/search?q=Lusaka%20weather%20forecast');
 // Search engines may reject automated traffic independently of Wolf.
 // Verify that the native browser navigates to Google's origin, not a
 // promise of provider acceptance or a bypass of provider verification.
 const google=await waitFor(async()=>{const t=(await targets()).find(x=>new URL(x.url).hostname.endsWith('google.com'));return t||null});
 assert(google.url.startsWith('https://www.google.com/'));
 await evalJS("state.settings.searchEngine='bing';save()");
 await evalJS("(()=>{const form=document.querySelector('#browser-address-form');form.querySelector('input[name=address]').value='Lusaka weather forecast';form.requestSubmit();return true})()");
 const bingUrl=await evalJS("getActiveBrowser().url");
 assert.equal(bingUrl,'https://www.bing.com/search?q=Lusaka%20weather%20forecast');
 await waitFor(async()=>{const t=(await targets()).find(x=>x.url?.includes('bing.com/search?q='));return t||null});
 const actual=await waitFor(async()=>{try{
  const d=await evalJS("window.wolfNative.snapshot({accountId:'default'}).then(x=>({url:x.url,text:(x.visibleText||'').slice(0,2000),title:x.title}))");
  return d.url.includes('bing.com/search?q=')&&d.text.length>100?d:null;
 }catch{return null}},70);
 assert(!/verifying you're not a bot|verification required|unusual traffic/i.test(actual.text),'Bing provider challenge');
 const directAddress=process.env.WOLF_ANDROID==='1'?'http://10.0.2.2:44692/login':'http://127.0.0.1:44692/login';
 await evalJS("(()=>{const form=document.querySelector('#browser-address-form');form.querySelector('input[name=address]').value="+JSON.stringify(directAddress)+";form.requestSubmit();return true})()");
 const direct=await waitFor(async()=>{const t=(await targets()).find(x=>x.url?.includes(new URL(directAddress).host+'/login'));return t||null});
 assert(direct.url.startsWith(directAddress));
 console.log('WOLF_SEARCH_AND_DIRECT_NAVIGATION_PASS',JSON.stringify({default:'Google',providerDestination:google.url,alternate:'Bing',searchResultsAvailable:true,directUrl:direct.url}));

}finally{ws.close()}
