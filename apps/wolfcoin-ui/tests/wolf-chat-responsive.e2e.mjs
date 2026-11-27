import assert from 'node:assert/strict';
const port=Number(process.env.WOLF_CHAT_QA_PORT||15128);
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
let target;
for(let i=0;i<100;i++){
 try{target=(await(await fetch('http://127.0.0.1:'+port+'/json')).json()).find(x=>x.type==='page'&&x.url.startsWith('file:'));if(target)break}catch{}
 await sleep(100);
}
assert(target,'preview browser unavailable');
const ws=new WebSocket(target.webSocketDebuggerUrl);
await new Promise((r,j)=>{ws.onopen=r;ws.onerror=j});
const pending=new Map();let id=0;
ws.onmessage=e=>{const m=JSON.parse(e.data),p=pending.get(m.id);if(p){pending.delete(m.id);m.error?p.reject(Error(m.error.message)):p.resolve(m.result)}};
const send=(method,params={})=>new Promise((resolve,reject)=>{const i=++id;pending.set(i,{resolve,reject});ws.send(JSON.stringify({id:i,method,params}));});
const evaluate=async expression=>{const r=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description||r.exceptionDetails.text);return r.result.value};
async function until(expression){for(let i=0;i<60;i++){if(await evaluate(expression))return;await sleep(100)}throw Error('Not ready: '+expression)}
const click=selector=>evaluate('document.querySelector('+JSON.stringify(selector)+').click()');
async function ask(text){
 await evaluate('document.querySelector("#wolf-chat-form textarea").value='+JSON.stringify(text)+';document.querySelector("#wolf-chat-form").requestSubmit()');
}
try{
 await until('!!document.querySelector(".brand")');
 await send('Emulation.setDeviceMetricsOverride',{width:1440,height:900,deviceScaleFactor:1,mobile:false});
 await click('.brand');await until('!!document.querySelector("#wolf-chat-form")');
 await ask('Open Settings');await until('state.tab==="settings" && !document.querySelector("#wolf-chat-form")');
 await click('.brand');await until('document.querySelector("#wolf-chat-log").textContent.includes("Opened settings.")');
 await ask('What are your capabilities?');await until('document.querySelector("#wolf-chat-log").textContent.includes("My advanced cognition is not yet available")');
 const panel=await evaluate('(()=>{const r=document.querySelector(".wolf-chat-panel").getBoundingClientRect();return {w:r.width,h:r.height,right:r.right}})()');
 assert(panel.w<=390&&panel.h<=540);
 assert.equal(await evaluate('!!document.querySelector(".modal-backdrop")'),false);
 assert.deepEqual(await evaluate('[...document.querySelector(".wolf-answer-actions").children].map(b=>b.getAttribute("aria-label"))'),['Copy','Helpful','Not helpful','Share','Sources','More']);
 await click('.wolf-answer-action[data-vote="helpful"]');
 assert.equal(await evaluate('document.querySelector("[data-vote=helpful]").getAttribute("aria-pressed")'),'true');
 await click('.wolf-answer-action[data-vote="not-helpful"]');
 assert.equal(await evaluate('document.querySelector("[data-vote=helpful]").getAttribute("aria-pressed")'),'false');
 await click('.wolf-answer-action[aria-label="Sources"]');
 assert(await evaluate('!document.querySelector(".wolf-answer-popover").hidden && document.querySelector(".wolf-answer-popover").textContent.includes("Local Wolf")'));
 await click('.wolf-answer-action[aria-label="More"]');
 assert(await evaluate('document.querySelector(".wolf-answer-popover").textContent.includes("Save response")'));
 await click('#modalRoot [data-action="close-modal"]');
 await send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
 await until('getComputedStyle(document.querySelector("#wolfChatLauncher button")).display==="flex"');
 const dims=await evaluate('(()=>{const b=document.querySelector("#wolfChatLauncher button"),r=b.getBoundingClientRect();return {position:getComputedStyle(b).position,width:r.width,height:r.height,right:r.right,bottom:r.bottom,viewport:innerWidth}})()');
 assert.equal(dims.position,'fixed');assert(dims.height>=44&&dims.right<=dims.viewport);
 await click('#wolfChatLauncher button');await until('!!document.querySelector("#wolf-chat-form")');
 await ask('Open Browser');await until('state.tab==="browser" && !document.querySelector("#wolf-chat-form")');
 assert.equal(await evaluate('document.querySelector("#wolfChatLauncher").childElementCount'),0);
 await until('getComputedStyle(document.querySelector(".browser-tabs .wolf-chat-mobile")).display==="flex"');
 await click('.browser-tabs .wolf-chat-mobile');await until('document.querySelector("#wolf-chat-log").textContent.includes("Opened browser.")');
 await ask('Use high contrast theme');await until('state.settings.theme==="high-contrast"');
 assert(await evaluate('!!document.querySelector("#wolf-chat-form")'));
 await click('#wolf-chat-clear');assert.equal(await evaluate('document.querySelectorAll(".wolf-chat-message").length'),1);
 console.log('WOLF_CHAT_DESKTOP_MOBILE_PREVIEW_PASS',JSON.stringify(dims));
}finally{ws.close()}

