import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
const port=Number(process.env.WOLF_EFFECT_PORT||15140);
const dir=process.env.WOLF_EFFECT_DIR;
assert(dir);fs.mkdirSync(dir,{recursive:true});
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
let target;
for(let i=0;i<100;i++){try{target=(await(await fetch('http://127.0.0.1:'+port+'/json')).json()).find(x=>x.type==='page'&&x.url.startsWith('file:'));if(target)break}catch{}await sleep(100)}
assert(target,'isolated app unavailable');
const ws=new WebSocket(target.webSocketDebuggerUrl);await new Promise((r,j)=>{ws.onopen=r;ws.onerror=j});
let seq=0;const pending=new Map();
ws.onmessage=e=>{const m=JSON.parse(e.data),p=pending.get(m.id);if(p){pending.delete(m.id);m.error?p.reject(Error(m.error.message)):p.resolve(m.result)}};
const send=(method,params={})=>new Promise((resolve,reject)=>{const id=++seq;pending.set(id,{resolve,reject});ws.send(JSON.stringify({id,method,params}));});
const ev=async expression=>{const r=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description||r.exceptionDetails.text);return r.result.value};
async function until(fn,label){for(let i=0;i<60;i++){try{if(await fn())return}catch{}await sleep(150)}throw Error(label)}
async function click(selector){const point=await ev('(()=>{const e=document.querySelector('+JSON.stringify(selector)+');if(!e)throw Error("missing control");e.scrollIntoView({block:"center"});const r=e.getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2}})()');await send('Input.dispatchMouseEvent',{type:'mousePressed',...point,button:'left',clickCount:1});await send('Input.dispatchMouseEvent',{type:'mouseReleased',...point,button:'left',clickCount:1});}
async function ask(text){await ev('document.querySelector("#wolf-chat-form textarea").value='+JSON.stringify(text)+';document.querySelector("#wolf-chat-form").requestSubmit()');}
function clipboardIs(expected){
 const p=process.platform==='win32'?spawnSync('powershell.exe',['-NoProfile','-NonInteractive','-Command',"$v=Get-Clipboard -Raw; if($v -ceq $env:WOLF_EXPECT_CLIP){exit 0};exit 1"],{env:{...process.env,WOLF_EXPECT_CLIP:expected},stdio:'ignore'}):spawnSync('python3',['-c','import tkinter as t,sys,os; r=t.Tk();r.withdraw();sys.exit(0 if r.clipboard_get()==os.environ["WOLF_EXPECT_CLIP"] else 1)'],{env:{...process.env,WOLF_EXPECT_CLIP:expected},stdio:'ignore'});
 return p.status===0;
}
try{
 await until(()=>ev('!!document.querySelector(".brand")'),'UI not loaded');
 await send('Page.bringToFront');
 await send('Emulation.setDeviceMetricsOverride',{width:1440,height:900,deviceScaleFactor:1,mobile:false});
 await ev('document.querySelector(".brand").click()');
 await until(()=>ev('!!document.querySelector("#wolf-chat-form")'),'chat not open');
 await ask('hi');const greeting='Hi. What do you need?';
 await until(()=>ev('document.querySelector(".wolf-answer-block")?.textContent.includes("Hi. What do you need?")'),'greeting missing');
 await click('.wolf-answer-block:nth-of-type(3) [aria-label="Copy"]');
 await until(()=>clipboardIs(greeting),'independent OS clipboard mismatch');
 console.log('OS_CLIPBOARD_COPY_PASS');
 await ask('help');
 await until(()=>ev('document.querySelectorAll(".wolf-answer-block").length===2'),'second response absent');
 const other=await ev('[...document.querySelectorAll(".wolf-answer-block")].at(-1).querySelector(".wolf-chat-message").textContent');
 assert.notEqual(other,greeting);
 await click('.wolf-answer-block:last-of-type [aria-label="Copy"]');
 await until(()=>clipboardIs(other),'second independent clipboard readback mismatch');
 const nativeShare=await ev('typeof navigator.share==="function"');
 if(nativeShare){console.log('NATIVE_SHARE_PRESENT_REQUIRES_HOST_SHARE_SHEET_ACCEPTANCE');}
 else {
  await click('.wolf-answer-block:nth-of-type(3) [aria-label="Share"]');
  await until(()=>clipboardIs(greeting),'share clipboard fallback mismatch');
  console.log('OS_SHARE_CLIPBOARD_FALLBACK_PASS');
 }
 try{await send('Browser.setDownloadBehavior',{behavior:'allow',downloadPath:dir});}
 catch{await send('Page.setDownloadBehavior',{behavior:'allow',downloadPath:dir});}
 assert(!fs.existsSync(path.join(dir,'wolf-response.txt')),'stale export file');
 await click('.wolf-answer-block:nth-of-type(3) [aria-label="More"]');
 await click('.wolf-answer-block:nth-of-type(3) .wolf-answer-popover button');
 const f=path.join(dir,'wolf-response.txt');
 await until(()=>fs.existsSync(f)&&fs.readFileSync(f,'utf8')===greeting,'export bytes not confirmed');
 console.log('FILESYSTEM_EXPORT_PASS',JSON.stringify({bytes:fs.statSync(f).size,nativeShare}));
}finally{ws.close()}
