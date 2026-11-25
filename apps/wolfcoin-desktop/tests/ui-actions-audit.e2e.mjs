import assert from 'node:assert/strict';
import fs from 'node:fs';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
const port=Number(process.env.WOLF_TEST_CDP_PORT||13993),url='http://127.0.0.1:'+port+'/json';
const target=(await(await fetch(url)).json()).find(x=>x.type==='page'&&x.url?.startsWith('file:'));
assert(target,'Wolf UI not running');
const ws=new WebSocket(target.webSocketDebuggerUrl);
await new Promise((yes,no)=>{ws.onopen=yes;ws.onerror=no});
let id=0;const callbacks=new Map();
ws.onmessage=e=>{const p=JSON.parse(e.data);const fn=callbacks.get(p.id);if(fn){callbacks.delete(p.id);p.error?fn.no(Error(p.error.message)):fn.yes(p.result)}};
const run=async expression=>{
 const x=await new Promise((yes,no)=>{const n=++id;callbacks.set(n,{yes,no});ws.send(JSON.stringify({id:n,method:'Runtime.evaluate',params:{expression,returnByValue:true,awaitPromise:true}}))});
 if(x.exceptionDetails)throw Error(x.exceptionDetails.exception?.description||x.exceptionDetails.text);
 return x.result.value;
};
try{
 const audit=await run("(()=>{const names=new Set();const byView={};const gather=label=>{const found=[...document.querySelectorAll('button[data-action], [role=button][data-action]')].map(x=>x.dataset.action).filter(Boolean);for(const a of found)names.add(a);byView[label]=found.length};for(const tab of ['overview','accounts','sessions','platforms','finance','activity','browser','settings','security']){navigate(tab);gather(tab)}for(const section of PREFS){state.prefSection=section;navigate('settings');gather('settings:'+section)}for(const section of SEC){state.securitySection=section;navigate('security');gather('security:'+section)}for(const section of ['history','bookmarks','tools','vault','downloads']){state.browserToolsOpen=true;state.browserToolTab=section;navigate('browser');gather('browser:'+section)}return {actions:[...names].sort(),byView,views:9,settings:PREFS.length,security:SEC.length,panes:5}})()");
 const source=fs.readFileSync(path.join(path.dirname(fileURLToPath(import.meta.url)),'../../wolfcoin-ui/ui-template.html'),'utf8');
 const handlers=new Set([...source.matchAll(/case '([^']+)'/g)].map(x=>x[1]));handlers.add('backend-event-details');handlers.add('backend-refresh');
 audit.unknown=audit.actions.filter(x=>!handlers.has(x));
 assert.deepEqual(audit.unknown,[],'Undispatched visible controls');
 assert(audit.actions.length>=40,'Unexpectedly few working controls');
 assert(audit.byView['browser:tools']>=12);
 console.log('WOLF_ALL_VISIBLE_ACTIONS_DISPATCH_AUDIT_PASS',JSON.stringify({uniqueActions:audit.actions.length,views:audit.views,settings:audit.settings,security:audit.security,panes:audit.panes,unknown:audit.unknown}));
}finally{ws.close()}
