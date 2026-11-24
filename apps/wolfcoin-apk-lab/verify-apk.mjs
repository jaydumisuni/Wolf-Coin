#!/usr/bin/env node
/**
 * Cross-host Android APK test adapter (Linux / Windows).
 * Real Android OS supplied by SDK Emulator or ADB physical device.
 * Produces bounded C10-style evidence; does not claim direct Ptah Rust invocation.
 */
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {spawnSync} from 'node:child_process';
import {mkdirSync,readFileSync,writeFileSync} from 'node:fs';
import path from 'node:path';
import os from 'node:os';
const opts={};
for(let i=2;i<process.argv.length;i+=2){if(!process.argv[i].startsWith('--'))throw Error('Use --key value args');opts[process.argv[i].slice(2)]=process.argv[i+1]}
const apk=path.resolve(opts.apk||'');
if(!apk||opts.apk===undefined)throw Error('Required --apk path');
const app='com.thetechguy.wolfcoin';
const activity=app+'/.MainActivity';
const sdk=process.env.ANDROID_SDK_ROOT||process.env.ANDROID_HOME||'';
const suffix=process.platform==='win32'?'.exe':'';
const bin=opts.adb||(sdk?path.join(sdk,'platform-tools','adb'+suffix):'adb');
const digest=data=>createHash('sha256').update(data).digest('hex');
function invoke(args,{timeout=30000,encoding='utf8'}={}){
 const r=spawnSync(bin,args,{timeout,encoding,maxBuffer:16*1024*1024});
 if(r.error)throw Error('adb invocation: '+r.error.message);
 if(r.status!==0)throw Error('adb '+args.join(' ')+' failed ('+r.status+'): '+String(r.stderr||r.stdout).slice(0,1500));
 return r.stdout;
}
function device(serial,args,settings){return invoke(['-s',serial,...args],settings)}
const devices=invoke(['devices','-l']).trim().split(/\r?\n/).slice(1).filter(x=>/\sdevice\s/.test(x));
let serial=opts.serial||process.env.ANDROID_SERIAL||'';
if(!serial){
 assert.equal(devices.length,1,'Multiple/no Android devices. Pass --serial explicitly.');
 serial=devices[0].split(/\s+/)[0];
}
assert(devices.some(x=>x.startsWith(serial+' ')),'Selected Android device is not connected');
const startedAt=new Date().toISOString(),bytes=readFileSync(apk);
assert(bytes.length>100000,'APK file unexpectedly small');
const localHash=digest(bytes);
const prop=n=>String(device(serial,['shell','getprop',n])).trim();
const version=prop('ro.build.version.release');
const api=prop('ro.build.version.sdk');
const arch=prop('ro.product.cpu.abi');
const kind=serial.startsWith('emulator-')?'android-emulator':'physical-android';
device(serial,['install','-r',apk],{timeout:120000});
const packagePathOutput=String(device(serial,['shell','pm','path',app]));
const packagePath=packagePathOutput.split(/\r?\n/).find(x=>x.startsWith('package:'))?.slice(8).trim();
assert(packagePath?.endsWith('base.apk'),'Installed APK package readback missing');
const remoteHashOutput=String(device(serial,['shell','sha256sum',packagePath]));
const remoteHash=remoteHashOutput.trim().split(/\s+/)[0].toLowerCase();
assert.equal(remoteHash,localHash,'Installed package bytes differ from input APK');
device(serial,['shell','am','start','-n',activity],{timeout:25000});
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
let processId='';
for(let i=0;i<50;i++){try{processId=String(device(serial,['shell','pidof',app])).trim()}catch{processId=''}if(processId)break;await sleep(180)}
assert(processId,'Application process did not start');
let activityResumed=false;
for(let i=0;i<25;i++){
 const activities=String(device(serial,['shell','dumpsys','activity','activities']));
 activityResumed=activities.includes('topResumedActivity=ActivityRecord')&&
   /com\.thetechguy\.wolfcoin\/(?:com\.thetechguy\.wolfcoin\.)?MainActivity/.test(activities);
 if(activityResumed)break;
 await sleep(180);
}
assert(activityResumed,'Application did not reach resumed activity');
const port=Number(opts.port||9224);
assert(Number.isInteger(port)&&port>=1024&&port<65536);
device(serial,['forward','tcp:'+port,'localabstract:webview_devtools_remote_'+processId]);
let webview=null;
try{
 let target=null;
 for(let i=0;i<35;i++){
  try{const targets=await(await fetch('http://127.0.0.1:'+port+'/json')).json();
   target=targets.find(x=>x.url?.startsWith('https://appassets.androidplatform.net/assets/wolfcoin.html'));
   if(target)break;
  }catch{}
  await sleep(180);
 }
 assert(target,'Wolf-Coin application WebView target missing');
 const ws=new WebSocket(target.webSocketDebuggerUrl.replace(/127\.0\.0\.1:\d+/,'127.0.0.1:'+port));
 await new Promise((resolve,reject)=>{ws.onopen=resolve;ws.onerror=reject});
 let cid=0;const pending=new Map();
 ws.onmessage=e=>{const m=JSON.parse(e.data);if(m.id&&pending.has(m.id)){const p=pending.get(m.id);pending.delete(m.id);m.error?p.reject(Error(m.error.message)):p.resolve(m.result)}};
 async function evaluate(expression){
  const r=await new Promise((resolve,reject)=>{const id=++cid;pending.set(id,{resolve,reject});ws.send(JSON.stringify({id,method:'Runtime.evaluate',params:{expression,awaitPromise:true,returnByValue:true}}))});
  if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description||r.exceptionDetails.text);
  return r.result?.value;
 }
 try{
   let state=null;
   for(let i=0;i<50;i++){
    try{state=JSON.parse(await evaluate("JSON.stringify({tabs:NAV.map(x=>x[0]),dxqt:window.WOLF_DXQT?.status,portfolio:!!window.WolfPortfolio})"))}
    catch{await sleep(150);continue}
    if(state.dxqt==='ready')break;await sleep(150);
   }
   assert(state,'Application frontend never initialized');
   assert.equal(state.tabs.length,9);
   assert(state.portfolio);
   assert.equal(state.dxqt,'ready','D-XQT WASM failed in Android WebView');
   const host=await evaluate('window.wolfNative.status()');
   assert.equal(host.schema,'wolf.browser.v1');
   assert.equal(host.host,'android');
   assert.equal(host.multiProfile,true,'WebView device does not support isolated profiles');
   webview={url:target.url,tabs:state.tabs.length,dxqt:state.dxqt,portfolio:state.portfolio,multiProfile:host.multiProfile};
 }finally{ws.close()}
}finally{
 try{device(serial,['forward','--remove','tcp:'+port])}catch{}
}
const screenshot=device(serial,['exec-out','screencap','-p'],{encoding:null,timeout:25000});
assert(screenshot.subarray(0,8).equals(Buffer.from([137,80,78,71,13,10,26,10])),'Android screenshot not PNG');
const evidence=path.resolve(opts.evidence||path.join(process.cwd(),'wolf-apk-evidence'));
mkdirSync(evidence,{recursive:true});
const screenPath=path.join(evidence,'wolfcoin-android.png');
writeFileSync(screenPath,screenshot);
const receipt={
 schema:'wolf.apk.lab.proof.v1',basis:'Ptah C10-shaped DeviceSession / PackageReadBack / ApplicationLaunchReadBack / ScreenContext evidence',
 assertedAt:new Date().toISOString(),startedAt,
 host:{platform:process.platform,arch:os.arch()},device:{serial,kind,version,api,arch,hardwareId:prop('ro.hardware')},
 application:{package:app,activity,localSha256:localHash,installedSha256:remoteHash,installedReadbackMatch:true,resumedActivity:true},
 webview,screen:{kind:'png',sha256:digest(screenshot),bytes:screenshot.length,filename:'wolfcoin-android.png'},
 outcomes:{packageInstall:true,packageReadBack:true,activityLaunch:true,webviewBridge:true,dXqt:true,nineTabs:true,multiProfile:true},
 acceptance:'isolated lab / debug APK; physical platform/provider qualification separate'
};
writeFileSync(path.join(evidence,'wolf-apk-proof.json'),JSON.stringify(receipt,null,2)+'\n');
console.log('WOLF_APK_C10_STYLE_PROOF_PASS '+JSON.stringify({serial,kind,sha256:localHash,webview,resumedActivity:true,evidenceDir:evidence}));
