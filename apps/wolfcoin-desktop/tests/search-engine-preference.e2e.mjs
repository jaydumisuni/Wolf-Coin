import assert from 'node:assert/strict';
const port=Number(process.env.WOLF_TEST_CDP_PORT||13961);
const pages=async()=>(await(await fetch('http://127.0.0.1:'+port+'/json')).json()).filter(x=>x.type==='page');
const target=(await pages()).find(x=>x.url?.startsWith('file:')||x.url?.includes('appassets.androidplatform.net/assets/wolfcoin.html'));
assert(target,'Wolf-Coin renderer target missing');
const ws=new WebSocket(target.webSocketDebuggerUrl.replace(/127\.0\.0\.1:\d+/,'127.0.0.1:'+port));
await new Promise((yes,no)=>{ws.onopen=yes;ws.onerror=no});
let id=0;const pending=new Map();
ws.onmessage=e=>{const m=JSON.parse(e.data),p=pending.get(m.id);if(p){pending.delete(m.id);m.error?p.no(Error(m.error.message)):p.yes(m.result)}};
const evalJS=async expression=>{
 const result=await new Promise((yes,no)=>{const n=++id;pending.set(n,{yes,no});ws.send(JSON.stringify({id:n,method:'Runtime.evaluate',params:{expression,returnByValue:true,awaitPromise:true}}))});
 if(result.exceptionDetails)throw Error(result.exceptionDetails.exception?.description||result.exceptionDetails.text);
 return result.result?.value;
};
const delay=ms=>new Promise(r=>setTimeout(r,ms));
try{
 let ready=false;
 for(let i=0;i<90;i++){
  try{if(await evalJS("typeof state!=='undefined'&&!!document.querySelector('#app')")){ready=true;break}}catch{}
  await delay(100);
 }
 assert(ready,'Wolf search UI failed to initialize');
 const starting=await evalJS("state.settings.searchEngine");
 assert.equal(starting,'google','Fresh profiles must default to Google');
 await evalJS("state.tab='overview';render();(()=>{const form=document.querySelector('#top-address-form');form.querySelector('[name=address]').value='Lusaka weather forecast';form.requestSubmit();return true})()");
 assert.equal(await evalJS("getActiveBrowser().url"),'https://www.google.com/search?q=Lusaka%20weather%20forecast');
 await evalJS("navigate('settings');state.prefSection='Browser';render()");
 const settings=await evalJS("(()=>{const x=document.querySelector('[data-setting-select=searchEngine]');return {values:[...x.options].map(o=>o.value),selected:x.value}})()");
 assert.deepEqual(settings.values,['google','bing']);
 assert.equal(settings.selected,'google');
 await evalJS("(()=>{const x=document.querySelector('[data-setting-select=searchEngine]');x.value='bing';x.dispatchEvent(new Event('change',{bubbles:true}));return true})()");
 assert.equal(await evalJS("state.settings.searchEngine"),'bing');
 await evalJS("navigate('browser');(()=>{const f=document.querySelector('#browser-address-form');f.querySelector('[name=address]').value='African tech news';f.requestSubmit();return true})()");
 assert.equal(await evalJS("getActiveBrowser().url"),'https://www.bing.com/search?q=African%20tech%20news');
 await evalJS("window.location.reload()");
 for(let i=0;i<80;i++){try{if((await evalJS("state.settings.searchEngine"))==='bing')break;}catch{}await delay(100)}
 assert.equal(await evalJS("state.settings.searchEngine"),'bing','Selected search engine must survive renderer reload');
 await evalJS("navigate('settings');state.prefSection='Browser';render()");
 assert.equal(await evalJS("document.querySelector('[data-setting-select=searchEngine]').value"),'bing');
 await evalJS("(()=>{const x=document.querySelector('[data-setting-select=searchEngine]');x.value='google';x.dispatchEvent(new Event('change',{bubbles:true}));return true})()");
 await evalJS("navigate('browser');(()=>{const f=document.querySelector('#browser-address-form');f.querySelector('[name=address]').value='recovery tooling';f.requestSubmit();return true})()");
 assert.equal(await evalJS("getActiveBrowser().url"),'https://www.google.com/search?q=recovery%20tooling');
 const direct='https://example.org/help?id=7';
 await evalJS("(()=>{const f=document.querySelector('#browser-address-form');f.querySelector('[name=address]').value="+JSON.stringify(direct)+";f.requestSubmit();return true})()");
 assert.equal(await evalJS("getActiveBrowser().url"),direct,'Direct URLs must not become search queries');
 await evalJS("state.settings.searchEngine='unsupported-engine'");
 assert.equal(await evalJS("searchQueryUrl('two words')"),'https://www.google.com/search?q=two%20words','Invalid stored engine must fall back to Google');
 await evalJS("state.settings.searchEngine='google';save()");
 console.log('WOLF_SEARCH_ENGINE_PREFERENCES_PASS',JSON.stringify({default:'Google',alternative:'Bing',changeLocation:'Settings / Browser',addressBars:'top and Browser',persistsAfterReload:true,directAddressesUnchanged:true,invalidSettingFallback:'Google'}));
}finally{ws.close()}
