/* Screenshot each actual nine-screen native renderer; baseline comparison still requires owner approval. */
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
const port=Number(process.env.WOLF_TEST_CDP_PORT||13930);
const out=path.resolve(process.env.WOLF_VISUAL_OUTPUT||'/tmp/wolf-nine-screens');
fs.mkdirSync(out,{recursive:true});
const target=(await(await fetch('http://127.0.0.1:'+port+'/json')).json()).find(x=>x.type==='page'&&x.url.startsWith('file:'));
assert(target,'No native UI DevTools page');
const ws=new WebSocket(target.webSocketDebuggerUrl);
await new Promise((resolve,reject)=>{ws.onopen=resolve;ws.onerror=reject});
let seq=0;const waits=new Map();
ws.onmessage=e=>{const m=JSON.parse(e.data);if(m.id&&waits.has(m.id)){
 const p=waits.get(m.id);waits.delete(m.id);m.error?p.reject(Error(m.error.message)):p.resolve(m.result)}};
const call=(method,params={})=>new Promise((resolve,reject)=>{const id=++seq;waits.set(id,{resolve,reject});ws.send(JSON.stringify({id,method,params}))});
const evaljs=async expression=>{
 const r=await call('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});
 if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description||r.exceptionDetails.text);
 return r.result.value;
};
try{
 await call('Emulation.setDeviceMetricsOverride',{width:1440,height:900,deviceScaleFactor:1,mobile:false});
 const shots=[];
 for(const tab of ['overview','accounts','sessions','platforms','finance','activity','settings','security','browser']){
  const state=JSON.parse(await evaljs("(()=>{document.querySelector('[data-tab="+tab+"]')?.click();return JSON.stringify({active:window.state?.tab||state.tab,len:document.querySelector('#main')?.textContent.length||0})})()"));
  assert.equal(state.active,tab);
  assert(state.len>40);
  await new Promise(r=>setTimeout(r,140));
  const result=await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});
  const png=Buffer.from(result.data,'base64');
  assert.equal(png.toString('hex',0,8),'89504e470d0a1a0a');
  const file=path.join(out,tab+'.png');fs.writeFileSync(file,png);
  shots.push({tab,bytes:png.length,characters:state.len});
 }
 fs.writeFileSync(path.join(out,'visual-evidence.json'),JSON.stringify({
  schema:'wolf.visual.cdp.v1',capturedAt:new Date().toISOString(),
  viewport:{width:1440,height:900},screens:shots,
  acceptance:'rendered screen and viewport evidence; not pixel-by-pixel mockup approval'
 },null,2)+'\n');
 console.log('WOLF_NINE_SCREEN_VISUAL_CAPTURE_PASS '+JSON.stringify(shots.map(x=>x.tab)));
}finally{ws.close()}
