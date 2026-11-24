/* Provider-independent market cues, tested in actual Chromium WebContentsView. */
import assert from 'node:assert/strict';
const port=Number(process.env.WOLF_TEST_CDP_PORT||13924);
const url='http://127.0.0.1:'+port;
const target=(await(await fetch(url+'/json')).json()).find(x=>x.type==='page'&&x.url.startsWith('file:'));
assert(target);
const ws=new WebSocket(target.webSocketDebuggerUrl);
await new Promise((resolve,reject)=>{ws.onopen=resolve;ws.onerror=reject});
let i=0;const jobs=new Map();
ws.onmessage=e=>{const m=JSON.parse(e.data);if(m.id&&jobs.has(m.id)){
 const j=jobs.get(m.id);jobs.delete(m.id);m.error?j.reject(Error(m.error.message)):j.resolve(m.result)}};
async function evaljs(expression){
 const r=await new Promise((resolve,reject)=>{const id=++i;jobs.set(id,{resolve,reject});
  ws.send(JSON.stringify({id,method:'Runtime.evaluate',params:{expression,returnByValue:true,awaitPromise:true}}))});
 if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description||r.exceptionDetails.text);
 return r.result.value;
}
try{
 await evaljs("createTab('http://127.0.0.1:44618/market','market_a')");
 let data;
 for(let i=0;i<35;i++){
  try{data=await evaljs("window.wolfNative.snapshot({accountId:'market_a'})");if(data?.opportunities?.length>=2)break;}catch{}
  await new Promise(r=>setTimeout(r,130));
 }
 assert(data,'No browser snapshot');
 assert.equal(data.platformDiscovery?.category,'betting');
 assert(data.opportunities.some(x=>x.market==='Fixture Match 2026-12-01'&&x.selection==='Home'&&x.quote===2.1));
 assert(data.opportunities.some(x=>x.selection==='Draw'&&x.quote===3.15));
 assert(data.opportunities.every(x=>x.source==='inferred_visible_control'));
 console.log('WOLF_GENERIC_MARKET_BROWSER_PASS '+JSON.stringify({title:data.title,classification:data.platformDiscovery.category,quotes:data.opportunities.map(x=>[x.selection,x.quote]),source:'ordinary HTML data-odds'}));
}finally{ws.close()}
