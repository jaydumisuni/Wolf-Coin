'use strict';
/* Wolf Browser desktop host; controls are not filtered by platform category. */
const {app,BrowserWindow,WebContentsView,ipcMain,session,shell,dialog}=require('electron');
const path=require('node:path');
const crypto=require('node:crypto');
const {URL,fileURLToPath}=require('node:url');
const fs=require('node:fs');
const {WolfNativeBackend}=require('./backend_host.cjs');
const {WolfAppIntegration}=require('./backend_integration.cjs');
let appBackend=null,appAdapter=null,backendInitError=null;
async function startAppBackend(){
 const own=path.join(__dirname,'backend-runtime');
 const unpacked=path.join(process.resourcesPath||'','app.asar.unpacked','backend-runtime');
 const moduleDir=fs.existsSync(path.join(own,'wolf_app','bridge.py'))?own:unpacked;
 const stateDir=process.env.WOLF_BACKEND_STATE_DIR||path.join(app.getPath('userData'),'backend');
 const host=new WolfNativeBackend({stateDir,moduleDir});
 try{
  await host.start();appBackend=host;appAdapter=new WolfAppIntegration(host);
  return {ok:true,schema:'wolf.app.bridge.v2'};
 }catch(e){
  backendInitError=e.message;console.error('WOLF_BACKEND_START_FAIL',e.message);
  await host.stop().catch(()=>{});return {ok:false,error:e.message};
 }
}
function requireAdapter(){if(!appAdapter)throw Error('Wolf backend unavailable: '+(backendInitError||'initializing'));return appAdapter;}
let mainWindow=null, activeView=null, activeAccount=null;
const views=new Map(), networkHistory=new Map(), events=new Map();
let region={x:0,y:0,width:0,height:0};
const TEST_MODE=process.env.WOLF_TEST_MODE==='1';
if(TEST_MODE && process.env.WOLF_TEST_USER_DATA)app.setPath('userData',process.env.WOLF_TEST_USER_DATA);
const CONTRACT='wolf.browser.v1';
const MAX_TEXT=16000;
function safeUrl(x){
 try{const u=new URL(String(x));if(u.username||u.password)throw Error();
  if(!['http:','https:'].includes(u.protocol))throw Error();
  return u.href;
 }catch{throw Error('Only HTTP(S) websites are supported.');}
}
function idOf(x){const s=String(x||'');if(!s || s.length>128 || !/^[A-Za-z0-9_:-]+$/.test(s))throw Error('Invalid account ID');return s;}
function partitionFor(id){return 'persist:wolf-'+crypto.createHash('sha256').update(idOf(id)).digest('hex').slice(0,32);}
function getSession(id){return session.fromPartition(partitionFor(id),{cache:true});}
function sessionEvent(id,type,details={}){
 const event={schema:CONTRACT,type,id:crypto.randomUUID(),accountId:id,observedAt:new Date().toISOString(),...details};
 const list=events.get(id)||[];list.push(event);if(list.length>100)list.shift();events.set(id,list);
 return event;
}
function trusted(e){if(!mainWindow||mainWindow.isDestroyed()||e.sender!==mainWindow.webContents)throw Error('Untrusted IPC sender');}
function requireActive(id){id=idOf(id);if(activeAccount!==id||!activeView)throw Error('Account/browser session mismatch');return activeView.webContents;}
function rectOf(r){if(!r||!['x','y','width','height'].every(k=>Number.isFinite(r[k])))throw Error('Invalid bounds');const [w,h]=mainWindow.getContentSize();const x=Math.max(0,Math.floor(r.x)),y=Math.max(0,Math.floor(r.y));return {x:Math.min(x,w),y:Math.min(y,h),width:Math.max(0,Math.min(Math.floor(r.width),w-x)),height:Math.max(0,Math.min(Math.floor(r.height),h-y))};}
function inform(w,id){if(w!==activeView?.webContents||mainWindow?.isDestroyed())return;mainWindow.webContents.send('wolf:page-state',{schema:CONTRACT,accountId:id,url:w.getURL(),title:w.getTitle(),observedAt:new Date().toISOString()});}
function captureRequest(id,details){const list=networkHistory.get(id)||[];let url;
 try{url=new URL(details.url);}catch{return;}
 if(!['http:','https:'].includes(url.protocol))return;
 const safePath=url.pathname.split('/').map(seg=>seg.length>28||/^[a-f0-9]{24,}$/i.test(seg)?':opaque':seg).join('/').slice(0,200);
 list.push({at:new Date().toISOString(),method:details.method,statusCode:details.statusCode||null,resourceType:details.resourceType,url:url.origin+safePath});
 if(list.length>120)list.splice(0,list.length-120);networkHistory.set(id,list);
}
function browserView(id){
 const ses=getSession(id);
 ses.setPermissionRequestHandler((wc,permission,done)=>{
  let origin='the current website';
  try{origin=new URL(wc.getURL()).origin}catch{}
  dialog.showMessageBox(mainWindow||undefined,{
    type:'question',title:'Website permission',
    message:origin+' requests '+String(permission)+' access',
    detail:'Wolf Browser website permission request',
    buttons:['Allow','Deny'],defaultId:0,cancelId:1,noLink:true
  }).then(result=>done(result.response===0)).catch(()=>done(false));
 });
 ses.webRequest.onCompleted(details=>captureRequest(id,details));
 ses.on('will-download',(_event,item)=>{ // Never silently write to Downloads.
  const proposed=path.basename(item.getFilename()).replace(/[^a-zA-Z0-9_.() -]/g,'_').slice(0,128)||'download';
  const dir=path.join(app.getPath('downloads'),'Wolf-Coin');fs.mkdirSync(dir,{recursive:true});
  item.setSavePath(path.join(dir,Date.now()+'-'+proposed));sessionEvent(id,'download.started',{filename:proposed});
 });
 const v=new WebContentsView({webPreferences:{session:ses,sandbox:true,contextIsolation:true,nodeIntegration:false,webSecurity:true,allowRunningInsecureContent:false}});
 // Popup/OAuth flows stay inside a Wolf-owned Chromium window with the same isolated profile.
 v.webContents.setWindowOpenHandler(({url})=>{
  try{safeUrl(url);}catch{return {action:'deny'};}
  return {action:'allow',overrideBrowserWindowOptions:{width:700,height:740,webPreferences:{session:ses,sandbox:true,contextIsolation:true,nodeIntegration:false,webSecurity:true}}};
 });
 for(const name of ['did-navigate','did-navigate-in-page','did-finish-load'])v.webContents.on(name,()=>inform(v.webContents,id));
 v.webContents.on('did-fail-load',(_e,code,description,attempted,isMainFrame)=>{if(isMainFrame)sessionEvent(id,'navigation.failure',{code,description,url:attempted?.slice(0,500)});});
 // Do not permit authenticated pages to pivot into file:, data:, or other privileged protocols.
 for(const name of ['will-navigate','will-redirect'])v.webContents.on(name,(event,target)=>{try{safeUrl(target);}catch{event.preventDefault();}});
 v.webContents.on('did-create-window',popup=>{
   for(const name of ['will-navigate','will-redirect'])popup.webContents.on(name,(event,target)=>{try{safeUrl(target);}catch{event.preventDefault();}});
   popup.webContents.setWindowOpenHandler(()=>({action:'deny'}));
 });
 v.webContents.on('render-process-gone',(_e,details)=>sessionEvent(id,'renderer.failure',{reason:details.reason}));
 return v;
}
function attach(v,id){
 if(activeView&&activeView!==v&&mainWindow.contentView.children.includes(activeView))mainWindow.contentView.removeChildView(activeView);
 activeView=v;activeAccount=v?id:null;
 if(v){if(!mainWindow.contentView.children.includes(v))mainWindow.contentView.addChildView(v);v.setBounds(region);}
}
function getView(id){const p=partitionFor(id);let v=views.get(p);if(!v){v=browserView(id);views.set(p,v);}return v;}
function receipt(id,action,ok,extra={}){return sessionEvent(id,action,{ok,...extra});}
const SNAPSHOT_SCRIPT=fs.readFileSync(path.join(__dirname,'wolf_snapshot.js'),'utf8');
async function snapshot(id){const wc=requireActive(id);const url=safeUrl(wc.getURL());const d=await wc.executeJavaScript(SNAPSHOT_SCRIPT,true);
 const source={type:CONTRACT,accountId:id,url,observedAt:d.observedAt,verification:'candidate_only',currencyHint:'ZMW',evidenceOrigin:'visible_dom'};
 return {...d,source,accountId:id,url,contract:CONTRACT};}
async function backgroundSnapshot(id){
 const wc=getView(id).webContents,url=safeUrl(wc.getURL());
 const d=await wc.executeJavaScript(SNAPSHOT_SCRIPT,true);
 return {...d,accountId:id,url,contract:CONTRACT,source:{type:CONTRACT,accountId:id,url,observedAt:d.observedAt,verification:'candidate_only',evidenceOrigin:'visible_dom'}};
}
async function domSnapshot(id){const wc=requireActive(id);const data=await wc.executeJavaScript(`(()=>{const nodes=[];const sel='a,button,input,select,textarea,[role=button]';for(const el of document.querySelectorAll(sel)){
 if(nodes.length>=250)break; if(!el.getClientRects().length)continue;
 const type=(el.getAttribute('type')||'').toLowerCase(), name=(el.getAttribute('name')||'').toLowerCase();
 if(/password|hidden|file/.test(type)||/pass|token|secret|otp|card/.test(name))continue;
 const text=(el.innerText||el.getAttribute('aria-label')||'').replace(/\\s+/g,' ').slice(0,130);
 nodes.push({tag:el.tagName.toLowerCase(),role:el.getAttribute('role'),type, name:name.slice(0,75),text,disabled:!!el.disabled});
 }return {title:document.title,url:location.href,nodes};})()`,true);
 return {contract:CONTRACT,accountId:id,observedAt:new Date().toISOString(),...data};}
function ensureSelector(selector){if(typeof selector!=='string'||selector.length>512||!selector.trim())throw Error('Invalid CSS selector');return selector;}
async function action(id,type,payload={}){
 const wc=requireActive(id);const at=new Date().toISOString();
 if(type==='navigate'){await wc.loadURL(safeUrl(payload.url));return receipt(id,'navigate',true,{startedAt:at,url:wc.getURL()});}
 if(type==='scroll'){const pixels=Math.max(-1500,Math.min(1500,Math.floor(Number(payload.pixels)||0)));await wc.executeJavaScript(`window.scrollBy(0,${pixels})`,true);return receipt(id,'scroll',true,{startedAt:at,pixels});}
 if(type==='click'||type==='fill'){
  const selector=ensureSelector(payload.selector);
  const text=String(payload.text||'');
  if(type==='fill'&&text.length>4096)throw Error('Input exceeds 4096 characters');
  const res=await wc.executeJavaScript(`(()=>{
   const el=document.querySelector(${JSON.stringify(selector)});
   if(!el || !el.getClientRects().length)return {ok:false,reason:'not_visible'};

   if(${JSON.stringify(type)}==='click'){
     const href=el.closest('a[href]')?.getAttribute('href')||'';
     if(/^javascript:|^data:|^file:/i.test(href))return {ok:false,reason:'unsafe_navigation'};
   }
   if(${JSON.stringify(type)}==='fill'){
    if(!['INPUT','TEXTAREA','SELECT'].includes(el.tagName)||el.type==='file')return {ok:false,reason:el.type==='file'?'file_picker_required':'unsupported_input'};
    const proto=el.tagName==='TEXTAREA'?HTMLTextAreaElement.prototype:el.tagName==='SELECT'?HTMLSelectElement.prototype:HTMLInputElement.prototype;
    const setter=Object.getOwnPropertyDescriptor(proto,'value')?.set;
    if(!setter)return {ok:false,reason:'input_unavailable'};
    setter.call(el,${JSON.stringify(text)});el.dispatchEvent(new Event('input',{bubbles:true}));el.dispatchEvent(new Event('change',{bubbles:true}));
   }else el.click();return {ok:true};
  })()`,true);
  return receipt(id,type,res?.ok===true,{startedAt:at,selector,reason:res.reason||null});
 }
 throw Error('Unsupported action');
}
async function clearSession(id){id=idOf(id);const p=partitionFor(id);const v=views.get(p);
 if(v){if(activeView===v)attach(null,null);views.delete(p);v.webContents.close();}
 const ses=getSession(id);await ses.clearStorageData();await ses.clearCache();events.delete(id);networkHistory.delete(id);
 return {ok:true,accountId:id,localSessionCleared:true,serverRevocationNotGuaranteed:true};}
async function synchronizeAccounts(accountList){
 const backend=requireAdapter();
 if(!Array.isArray(accountList))throw Error('Account list required');
 const results=[];
 const seen=new Set();
 for(const a of accountList.slice(0,200)){
  const id=idOf(a.id);
  if(seen.has(id))continue;seen.add(id);
  if(!a.url){results.push({id,status:'NO_WEBSITE'});continue;}
  let website;
  try{
   const v=getView(id),url=safeUrl(a.url);
   const existing=v.webContents.getURL();
   if(existing!==url&&v.webContents.isLoadingMainFrame()===false)await v.webContents.loadURL(url);
   website=await backgroundSnapshot(id);
   const result=await backend.observe(a,website);
   results.push({id,status:'OBSERVED',auth:website.auth,identity:website.identity||null,
    opportunities:website.opportunities||[],backend:result.account,skippedStale:!!result.skippedStale});
  }catch(e){results.push({id,status:'ERROR',message:String(e.message||e).slice(0,200)})}
 }
 return {schema:'wolf.host.sync.v1',results,backend:await backend.snapshot()};
}
function setupBackendIPC(){
 const on=(channel,fn)=>ipcMain.handle(channel,async(e,p)=>{trusted(e);return fn(p||{});});
 on('wolf:backend-status',()=>({available:!!appAdapter,schema:'wolf.app.bridge.v2',error:backendInitError}));
 on('wolf:backend-request',p=>requireAdapter().request(p.operation,p.payload||{}));
 on('wolf:backend-register',p=>requireAdapter().ensureAccount(p));
 on('wolf:backend-observe',p=>snapshot(idOf(p.id)).then(d=>requireAdapter().observe(p,d)));
 on('wolf:backend-session',p=>requireAdapter().session(p.account,p.state));
 on('wolf:backend-remove',p=>requireAdapter().remove(p));
 on('wolf:backend-snapshot',()=>requireAdapter().snapshot());
 on('wolf:backend-propose',p=>requireAdapter().proposal(p));
 on('wolf:backend-sync-all',p=>synchronizeAccounts(p.accounts));
}
function setupIPC(){
 const on=(channel,fn)=>ipcMain.handle(channel,async(e,payload)=>{trusted(e);return fn(payload||{});});
 on('wolf:status',()=>({schema:CONTRACT,host:'electron',version:app.getVersion(),browserOpen:!!activeView,accountId:activeAccount,mode:'browser_controls_available'}));
 on('wolf:bounds',r=>{region=rectOf(r);if(activeView)activeView.setBounds(region);return {ok:true};});
 on('wolf:hide-browser',()=>{attach(null,null);return {ok:true};});
 on('wolf:show-browser',async({url,accountId})=>{const id=idOf(accountId),address=safeUrl(url);const v=getView(id);attach(v,id);
  if(v.webContents.getURL()!==address&&v._wolfRequestedUrl!==address){v._wolfRequestedUrl=address;await v.webContents.loadURL(address);}
  return {ok:true,url:v.webContents.getURL(),accountId:id,partition:'persistent isolated profile'};
 });
 on('wolf:back',()=>{const wc=requireActive(activeAccount);if(wc.navigationHistory.canGoBack())wc.navigationHistory.goBack();return {ok:true};});
 on('wolf:forward',()=>{const wc=requireActive(activeAccount);if(wc.navigationHistory.canGoForward())wc.navigationHistory.goForward();return {ok:true};});
 on('wolf:reload',()=>{requireActive(activeAccount).reload();return {ok:true};});
 on('wolf:snapshot',p=>snapshot(idOf(p.accountId)));
 on('wolf:dom',p=>domSnapshot(idOf(p.accountId)));
 on('wolf:network',p=>{const id=idOf(p.accountId);requireActive(id);return {schema:CONTRACT,accountId:id,observedAt:new Date().toISOString(),records:(networkHistory.get(id)||[]).slice(-50)};});
 on('wolf:action',p=>action(idOf(p.accountId),p.type,p));
 on('wolf:screenshot',async p=>{const id=idOf(p.accountId);const img=await requireActive(id).capturePage();const bytes=img.toPNG();if(bytes.length>4*1024*1024)throw Error('Screenshot too large');return {schema:CONTRACT,accountId:id,observedAt:new Date().toISOString(),mimeType:'image/png',dataUrl:'data:image/png;base64,'+bytes.toString('base64')};});
 on('wolf:events',p=>({schema:CONTRACT,accountId:idOf(p.accountId),records:(events.get(idOf(p.accountId))||[]).slice(-50)}));
 on('wolf:clear-session',p=>clearSession(p.accountId));
 on('wolf:open-external',p=>shell.openExternal(safeUrl(p.url)).then(()=>({ok:true})));
}
async function testFlow(){
 const assert=require('node:assert/strict');
 const id='fixture-sports-1',address=safeUrl(process.env.WOLF_TEST_FIXTURE),stage=process.env.WOLF_TEST_STAGE||'fresh';
 const v=getView(id);attach(v,id);v.setBounds({x:0,y:0,width:1050,height:700});await v.webContents.loadURL(address);
 let s=await snapshot(id);
 if(stage==='fresh'){
  assert.equal(s.auth,'login_required');
  const dom=await domSnapshot(id);assert(dom.nodes.some(n=>n.tag==='button'));
  assert.equal((await action(id,'fill',{selector:'input[name=user]',text:'fixture'})).ok,true);
  // Controlled local fixture: prove normal form fields and submit buttons work via Wolf Browser.
  assert.equal((await action(id,'fill',{selector:'input[name=pass]',text:'fixture'})).ok,true);
  const loginLoaded=new Promise(resolve=>v.webContents.once('did-finish-load',resolve));
  assert.equal((await action(id,'click',{selector:'button[type=submit]'})).ok,true);
  await loginLoaded;
  s=await snapshot(id);
  assert.equal(s.auth,'probable_authenticated');assert.equal(s.candidates.balance?.value,750);
  assert.equal(s.candidates.pending?.value,100);assert.equal(s.candidates.pnl?.value,60);
  assert((await requireActive(id).capturePage()).toPNG().length>1000);
  assert((networkHistory.get(id)||[]).length>0);
  assert.equal((await action(id,'click',{selector:'button'})).ok,true); // Log Out on controlled fixture
  await new Promise(resolve=>v.webContents.once('did-finish-load',resolve));
  s=await snapshot(id);assert.equal(s.auth,'login_required');
  // Login again so restart tests verify persisted HTTP-only cookie.
  await v.webContents.executeJavaScript(`document.querySelector('input[name=user]').value='fixture';document.querySelector('input[name=pass]').value='fixture';document.querySelector('form').requestSubmit()`,true);
  await new Promise(resolve=>v.webContents.once('did-finish-load',resolve));
  s=await snapshot(id);assert.equal(s.auth,'probable_authenticated');
  const id2='fixture-second-account';
  const second=getView(id2);attach(second,id2);second.setBounds({x:0,y:0,width:1050,height:700});await second.webContents.loadURL(address);
  const s2=await snapshot(id2);assert.equal(s2.auth,'login_required','Account profiles share website authentication');
  attach(v,id);const s1=await snapshot(id);assert.equal(s1.auth,'probable_authenticated');
  console.log('WOLF_NATIVE_FIXTURE_PASS',JSON.stringify({contract:CONTRACT,auth:s.auth,candidates:s.candidates,domCount:dom.nodes.length,networkItems:(networkHistory.get(id)||[]).length,secondAccountAuth:s2.auth}));
 }else if(stage==='restore'){
  assert.equal(s.auth,'probable_authenticated','Persistent profile cookie missing after restart');
  await clearSession(id);
  const vv=getView(id);attach(vv,id);await vv.webContents.loadURL(address);s=await snapshot(id);assert.equal(s.auth,'login_required');
  console.log('WOLF_NATIVE_RESTART_AND_REMOVE_PASS',JSON.stringify({auth:s.auth}));
 }else throw Error('Unknown test stage');
 setTimeout(()=>app.quit(),150);
}
app.whenReady().then(async()=>{
 await startAppBackend();
 mainWindow=new BrowserWindow({width:1540,height:1024,minWidth:720,minHeight:500,autoHideMenuBar:true,
  webPreferences:{preload:path.join(__dirname,'preload.cjs'),contextIsolation:true,nodeIntegration:false,sandbox:true,webSecurity:true}});
 setupIPC();setupBackendIPC();const html=path.join(__dirname,'app.html');
 mainWindow.webContents.on('will-navigate',(event,url)=>{try{const u=new URL(url);if(u.protocol!=='file:'||path.resolve(fileURLToPath(u))!==html)event.preventDefault();}catch{event.preventDefault();}});
 mainWindow.webContents.setWindowOpenHandler(()=>({action:'deny'}));
 mainWindow.loadFile(html);
 mainWindow.on('closed',()=>{mainWindow=null;for(const v of views.values())if(!v.webContents.isDestroyed())v.webContents.close();views.clear();});
 if(TEST_MODE)mainWindow.webContents.once('did-finish-load',()=>{console.log('WOLF_NATIVE_READY');if(process.env.WOLF_TEST_FIXTURE)testFlow().catch(e=>{console.error('WOLF_NATIVE_TEST_FAIL',e.stack||e);app.exit(2);});});
}).catch(e=>{console.error('WOLF_INIT_FAIL',e.stack||e);app.exit(3);});
app.on('will-quit',()=>{appBackend?.child?.stdin?.end()});
app.on('window-all-closed',()=>app.quit());
