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
 const ui=JSON.parse(await evalJS("JSON.stringify({tab:state.tab,url:getActiveBrowser().url})"));
 assert.equal(ui.tab,'browser');
 assert.equal(ui.url,'https://www.google.com/search?q=Lusaka%20weather%20forecast');
 await waitFor(async()=>{const t=(await targets()).find(x=>x.url?.includes('google.com/search?q='));return t||null});
 await sleep(2500);
 const actual=await waitFor(async()=>{try{
 const d=await evalJS("window.wolfNative.snapshot({accountId:'default'}).then(x=>({url:x.url,text:(x.visibleText||'').slice(0,2000),title:x.title}))");
 return d.url.includes('google.com/search?q=')&&d.text.length>100?d:null;
 }catch{return null}},70);
 assert(actual.url.includes('google.com/search?q='));
 assert(actual.text.length>100,'Search returned no visible results');
 assert(!/verifying you're not a bot|verification required|unusual traffic/i.test(actual.text),'Search was blocked by a provider challenge');
 assert(/Lusaka|weather|result/i.test(actual.text),'Search text did not reflect query');
 const directAddress=process.env.WOLF_ANDROID==='1'?'http://10.0.2.2:44692/login':'http://127.0.0.1:44692/login';
 await evalJS("(()=>{const form=document.querySelector('#browser-address-form');form.querySelector('input[name=address]').value="+JSON.stringify(directAddress)+";form.requestSubmit();return true})()");
 const direct=await waitFor(async()=>{const t=(await targets()).find(x=>x.url?.includes(new URL(directAddress).host+'/login'));return t||null});
 assert(direct.url.startsWith(directAddress));
 console.log('WOLF_SEARCH_AND_DIRECT_NAVIGATION_PASS',JSON.stringify({engine:'Google',queryUrl:ui.url,returnedResults:true,title:actual.title,independentAccount:true,directUrl:direct.url}));
}finally{ws.close()}
