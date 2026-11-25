/**
 * UI-initiated local browser fixture test over Chromium CDP.
 * Run only against a locally launched Electron --remote-debugging-port test host.
 * Never use a remote debugging port for real account sessions.
 */
import assert from 'node:assert/strict';
const port=Number(process.env.WOLF_TEST_CDP_PORT||13879);
const fixture=process.env.WOLF_FIXTURE_URL||'http://127.0.0.1:44567/login';
const endpoint='http://127.0.0.1:'+port;
const sleep=n=>new Promise(r=>setTimeout(r,n));
async function targets(){return(await(await fetch(endpoint+'/json')).json()).filter(x=>x.type==='page')}
async function connect(t){
  let id=0;const pending=new Map();const ws=new WebSocket(t.webSocketDebuggerUrl);
  await new Promise((yes,no)=>{ws.onopen=yes;ws.onerror=no});
  ws.onmessage=e=>{const m=JSON.parse(e.data);if(m.id&&pending.has(m.id)){
    const q=pending.get(m.id);pending.delete(m.id);m.error?q.reject(new Error(m.error.message)):q.resolve(m.result);
  }};
  return {eval:async expression=>{
     const result=await new Promise((resolve,reject)=>{let n=++id;pending.set(n,{resolve,reject});ws.send(JSON.stringify({id:n,method:'Runtime.evaluate',params:{expression,awaitPromise:true,returnByValue:true}}))});
     if(result.exceptionDetails)throw new Error(result.exceptionDetails.text+' '+result.result?.description);
     return result.result?.value;
   },close:()=>ws.close()};
}
const uiTarget=(await targets()).find(x=>x.url.startsWith('file:'));
assert(uiTarget,'UI page missing');
const ui=await connect(uiTarget);
const result={};
try{
 for(let i=0;i<40;i++){if((await ui.eval("window.WOLF_DXQT?.status"))==='ready')break;await sleep(100)}
 const initial=JSON.parse(await ui.eval("JSON.stringify({accounts:state.accounts.length,demoMode:state.demoMode,dxqt:window.WOLF_DXQT.status})"));
 assert.equal(initial.accounts,0,'Native app must start without sample financial accounts');
 assert.equal(initial.demoMode,false);
 assert.equal(initial.dxqt,'ready');
 result.boot=initial;
 // All nine real tab render paths must remain available before adding accounts.
 for(const tab of ['overview','browser','accounts','sessions','platforms','finance','activity','settings','security']){
   const outcome=JSON.parse(await ui.eval("(()=>{const tab="+JSON.stringify(tab)+";const nav=document.querySelector('[data-tab=\"'+tab+'\"]');if(!nav)return JSON.stringify({tab,missing:true});nav.click();return JSON.stringify({tab,actual:state.tab,len:document.querySelector('#main')?.textContent.length||0})})()"));
   assert.equal(outcome.actual,tab,'Tab did not navigate: '+tab);
   assert(outcome.len>30,'Tab rendered blank: '+tab);
 }
 result.navigation='9/9';
 // Register account using actual UI controls.
 await ui.eval("document.querySelector('[data-tab=platforms]').click()");
 await ui.eval("document.querySelector('[data-action=add-account]').click()");
 assert.equal(await ui.eval("!!document.querySelector('#account-form')"),true);
 await ui.eval("(()=>{let f=document.querySelector('#account-form');f.querySelector('[name=name]').value='E2E Fixture Sports';f.querySelector('[name=url]').value="+JSON.stringify(fixture)+";f.querySelector('[name=type]').value='Betting';f.requestSubmit()})()");
 await sleep(250);
 let state=JSON.parse(await ui.eval("JSON.stringify({tab:state.tab,accounts:state.accounts})"));
 assert.equal(state.accounts.length,1);assert.equal(state.tab,'browser');assert(['unverified','loggedout'].includes(state.accounts[0].status),'New registration must require login or verification');
 result.add={status:state.accounts[0].status,accounts:state.accounts.length};
 // Real browser login (test fixture has test-only login fields).
 let site;
 for(let i=0;i<30;i++){site=(await targets()).find(x=>x.url.includes(new URL(fixture).host+'/login'));if(site)break;await sleep(100)}
 assert(site,'The native managed website did not open');
 const page=await connect(site);
 try{
   // Target URL can appear before its form elements are hydrated in Chromium.
   let formReady=false;
   for(let attempt=0;attempt<50;attempt++){
     try{formReady=await page.eval("!!document.querySelector('[name=user]')&&!!document.querySelector('[name=pass]')");}
     catch(_){}
     if(formReady)break;
     await sleep(120);
   }
   assert(formReady,'Fixture login fields did not appear after navigation');
   await page.eval("(()=>{document.querySelector('[name=user]').value='fixture';document.querySelector('[name=pass]').value='fixture';document.querySelector('form').requestSubmit();return true})()");
 }finally{page.close()}
 await sleep(450);
 await ui.eval("document.querySelector('[data-action=browser-panel-tools]').click()");
 await ui.eval("document.querySelector('[data-action=sync-current]').click()");
 await sleep(600);
 state=JSON.parse(await ui.eval("JSON.stringify({tab:state.tab,accounts:state.accounts})"));
 assert.equal(state.accounts[0].status,'connected',JSON.stringify(state.accounts[0]));
 assert.equal(state.accounts[0].balance,750);
 assert.equal(state.accounts[0].pending,100);
 assert.equal(state.accounts[0].pnl,60);
 result.sync={status:state.accounts[0].status,balance:state.accounts[0].balance,pending:state.accounts[0].pending,pnl:state.accounts[0].pnl};
 // Verify the Browser Tools menu has real native effects, not placeholder toasts.
 await ui.eval("document.querySelector('[data-action=browser-panel-tools]').click()");
 assert.equal(await ui.eval("!!document.querySelector('[data-action=native-snapshot]')"),true);
 await ui.eval("document.querySelector('[data-action=native-snapshot]').click()");
 await sleep(130);
 assert.equal(await ui.eval("document.querySelector('#modalRoot').textContent.includes('Read-only Page Snapshot')"),true);
 assert.equal(await ui.eval("document.querySelector('#modalRoot textarea').value.includes('750')"),true);
 await ui.eval("document.querySelector('[data-action=close-modal]').click()");
 await sleep(90);
 await ui.eval("document.querySelector('[data-action=browser-panel-tools]').click()");
 await ui.eval("document.querySelector('[data-action=native-dom]').click()");
 await sleep(110);
 assert.equal(await ui.eval("document.querySelector('#modalRoot textarea').value.includes('nodes')"),true);
 await ui.eval("document.querySelector('[data-action=close-modal]').click()");
 await sleep(90);
 await ui.eval("document.querySelector('[data-action=browser-panel-tools]').click()");
 await ui.eval("document.querySelector('[data-action=native-network]').click()");
 await sleep(110);
 assert.equal(await ui.eval("document.querySelector('#modalRoot textarea').value.includes('records')"),true);
 await ui.eval("document.querySelector('[data-action=close-modal]').click()");
 await sleep(90);
 await ui.eval("document.querySelector('[data-action=browser-panel-tools]').click()");
 await ui.eval("document.querySelector('[data-action=native-screenshot]').click()");
 await sleep(250);
 assert.equal(await ui.eval("document.querySelector('#modalRoot img')?.src.startsWith('data:image/png;base64,')"),true);
 await ui.eval("document.querySelector('[data-action=close-modal]').click()");
 await sleep(90);
 await ui.eval("document.querySelector('[data-action=browser-panel-tools]').click()");
 await ui.eval("document.querySelector('[data-action=native-action]').click()");
 assert.equal(await ui.eval("!!document.querySelector('#native-action-form')"),true);
 await ui.eval("document.querySelector('#native-action-form').requestSubmit()");
 await sleep(140);
 result.browserTools={snapshot:true,dom:true,network:true,screenshot:true,scrollAction:true};
 await ui.eval("document.querySelector('[data-tab=accounts]').click()");
 await ui.eval("document.querySelector('[data-action=account-actions]').click()");
 await ui.eval("document.querySelector('[data-action=terminate-session]').click()");
 // Native session cleanup and signed backend reconciliation are asynchronous.
 // Accept only the fully converged UI+backend result, not a fixed-delay guess.
 let backState=null;
 for(let attempt=0;attempt<55;attempt++){
  state=JSON.parse(await ui.eval("JSON.stringify({accounts:state.accounts})"));
  backState=JSON.parse(await ui.eval("JSON.stringify(window.WolfNativeIntegration?.snapshot?.accounts||[])"));
  if(state.accounts[0]?.status==='loggedout' && backState[0]?.session_state==='LOGGED_OUT')break;
  await sleep(120);
 }
 assert.equal(state.accounts.length,1);
 assert.equal(state.accounts[0].status,'loggedout');
 assert.equal(backState[0]?.session_state,'LOGGED_OUT');
 assert.equal(state.accounts[0].balance,750);
 result.logout={accounts:state.accounts.length,status:state.accounts[0].status,lastKnown:state.accounts[0].balance};
 console.log('WOLF_NATIVE_UI_E2E_PASS '+JSON.stringify(result));
}finally{ui.close()}
