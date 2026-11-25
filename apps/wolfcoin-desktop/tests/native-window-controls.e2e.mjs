import assert from 'node:assert/strict';
const port=Number(process.env.WOLF_TEST_CDP_PORT||13976);
const roots=async()=>(await(await fetch('http://127.0.0.1:'+port+'/json')).json()).filter(x=>x.type==='page');
const page=(await roots()).find(x=>x.url?.startsWith('file:'));
assert(page,'Wolf window renderer unavailable');
const ws=new WebSocket(page.webSocketDebuggerUrl);
await new Promise((yes,no)=>{ws.onopen=yes;ws.onerror=no});
const p=new Map();let seq=0;
ws.onmessage=e=>{const msg=JSON.parse(e.data);const v=p.get(msg.id);if(!v)return;p.delete(msg.id);msg.error?v.no(Error(msg.error.message)):v.yes(msg.result)};
async function ev(expression) {
 const result=await new Promise((yes,no)=>{
  const id=++seq;p.set(id,{yes,no});
  ws.send(JSON.stringify({id,method:'Runtime.evaluate',params:{expression,returnByValue:true,awaitPromise:true}}));
 });
 if(result.exceptionDetails)throw Error(result.exceptionDetails.exception?.description||result.exceptionDetails.text);
 return result.result?.value;
}
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
try{
 const state=await ev("window.wolfNative.windowState()");
 assert.equal(state.frameless,true,'Native OS title bar was not disabled');
 const top=await ev("(()=>({ctrls:document.querySelectorAll('#topbar .win-button').length,bell:!!document.querySelector('#topbar [data-action=notifications]'),frame:document.querySelector('#topbar').getBoundingClientRect().height}))()");
 assert.equal(top.ctrls,3);
 assert.equal(top.bell,true);
 assert(top.frame>40);
 await ev("window.wolfNative.windowToggleMaximize()");
 assert.equal((await ev("window.wolfNative.windowState()")).maximized,true);
 await ev("window.wolfNative.windowToggleMaximize()");
 assert.equal((await ev("window.wolfNative.windowState()")).maximized,false);
 await ev("navigate('browser')");
 const browser=await ev("(()=>({ctrls:document.querySelectorAll('.browser-tabs .win-button').length,bell:!!document.querySelector('.browser-tabs [data-action=notifications]'),topbar:getComputedStyle(document.querySelector('#topbar')).display}))()");
 assert.equal(browser.ctrls,3);
 assert.equal(browser.bell,true);
 assert.equal(browser.topbar,'none');
 await ev("document.querySelector('.browser-tabs [data-action=window-maximize]').click()");
 await sleep(250);
 assert.equal((await ev("window.wolfNative.windowState()")).maximized,true);
 await ev("document.querySelector('.browser-tabs [data-action=window-maximize]').click()");
 await sleep(250);
 assert.equal((await ev("window.wolfNative.windowState()")).maximized,false);
 await ev("document.querySelector('.browser-tabs [data-action=window-minimize]').click()");
 await sleep(350);
 assert.equal((await ev("window.wolfNative.windowState()")).minimized,true);
 console.log('WOLF_NATIVE_FRAMELESS_WINDOW_CONTROLS_PASS',JSON.stringify({topbarHeight:top.frame,topControls:top.ctrls,browserControls:browser.ctrls,browserTopbarHidden:true,maximizeRestore:true,minimize:true,closeHandler:!!(await ev("window.wolfNative.windowClose"))}));
}finally{ws.close()}
