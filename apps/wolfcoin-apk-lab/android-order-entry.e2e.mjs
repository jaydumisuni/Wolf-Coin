import assert from 'node:assert/strict';
const port=Number(process.env.WOLF_WEBVIEW_CDP_PORT||9279);
const target=(await(await fetch('http://127.0.0.1:'+port+'/json')).json()).find(x=>x.type==='page'&&x.url?.includes('/assets/wolfcoin.html'));
assert(target,'Wolf-Coin renderer missing');
const ws=new WebSocket(target.webSocketDebuggerUrl.replace(/127\.0\.0\.1:\d+/,'127.0.0.1:'+port));
await new Promise((yes,no)=>{ws.onopen=yes;ws.onerror=no});
let id=0;const pending=new Map();
ws.onmessage=e=>{const m=JSON.parse(e.data);if(m.id&&pending.has(m.id)){const p=pending.get(m.id);pending.delete(m.id);m.error?p.reject(Error(m.error.message)):p.resolve(m.result)}};
async function run(expression){
 const r=await new Promise((resolve,reject)=>{const n=++id;pending.set(n,{resolve,reject});ws.send(JSON.stringify({id:n,method:'Runtime.evaluate',params:{expression,returnByValue:true,awaitPromise:true}}))});
 if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description||r.exceptionDetails.text);
 return r.result?.value;
}
try{
 await run("state.accounts=[];state.events=[];state.tab='overview';render()");
 assert.equal(await run("document.querySelectorAll('[data-action=start-bet]').length>=2"),true);
 assert.equal(await run("document.querySelectorAll('[data-action=start-trade]').length>=2"),true);
 await run("document.querySelector('[data-action=start-bet]').click()");
 assert.match(await run("document.querySelector('#modalRoot').textContent"),/Register a betting platform/);
 await run("closeModal()");
 await run("state.accounts.push({id:'order-sports',name:'Fixture Sports',type:'Betting',url:'http://10.0.2.2:44692/login',financialCurrency:'ZMW',status:'loggedout',known:false,sync:'Never'});state.accounts.push({id:'order-trading',name:'Fixture Trading',type:'Trading',url:'http://10.0.2.2:44692/login',financialCurrency:'USD',status:'loggedout',known:false,sync:'Never'});render()");
 await run("document.querySelector('[data-action=start-bet]').click()");
 assert.equal(await run("document.querySelector('#financial-start-form [name=kind]').value"),'bet');
 assert.equal(await run("document.querySelectorAll('#financial-start-form [name=accountId] option').length"),1);
 await run("document.querySelector('#financial-start-form').requestSubmit()");
 await new Promise(r=>setTimeout(r,250));
 let state=await run("JSON.stringify({tab:state.tab,acct:getActiveBrowser().accountId,url:getActiveBrowser().url,modal:!!document.querySelector('#financial-start-form')})");
 state=JSON.parse(state);
 assert.equal(state.tab,'browser');assert.equal(state.acct,'order-sports');assert.match(state.url,/44692/);assert.equal(state.modal,false);
 assert.equal(await run("document.querySelectorAll('[data-action=start-bet]').length>=1"),true);
 assert.equal(await run("document.querySelectorAll('[data-action=start-trade]').length>=1"),true);
 await run("document.querySelector('[data-action=start-trade]').click()");
 assert.equal(await run("document.querySelector('#financial-start-form [name=kind]').value"),'trade');
 assert.equal(await run("document.querySelectorAll('#financial-start-form [name=accountId] option').length"),1);
 await run("document.querySelector('#financial-start-form').requestSubmit()");
 await new Promise(r=>setTimeout(r,250));
 state=JSON.parse(await run("JSON.stringify({tab:state.tab,acct:getActiveBrowser().accountId,url:getActiveBrowser().url})"));
 assert.equal(state.acct,'order-trading');
 assert.equal(state.tab,'browser');
 await run("state.tab='sessions';render()");
 console.log('WOLF_ORDER_ENTRY_E2E_PASS',JSON.stringify({betting:'opened registered betting site',trading:'opened registered trading site',noAccount:'registration option',mainActions:true,browserActions:true,accountIsolation:true}));
}finally{ws.close()}
