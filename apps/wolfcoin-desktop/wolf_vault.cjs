'use strict';
const fs=require('node:fs');
const path=require('node:path');
const {URL}=require('node:url');
function originOf(raw,allowLoopback=false){
 const u=new URL(String(raw));
 if(u.username||u.password||!u.hostname)throw Error('Invalid website origin');
 const loopback=['localhost','127.0.0.1','[::1]'].includes(u.hostname);
 if(u.protocol!=='https:'&&!(allowLoopback&&loopback&&u.protocol==='http:'))
  throw Error('Credential vault requires HTTPS');
 return u.origin;
}
function available(safeStorage){
 return Boolean(safeStorage?.isEncryptionAvailable?.()&&safeStorage.getSelectedStorageBackend?.()!=='basic_text');
}
class WolfVault{
 constructor({safeStorage,userData,allowLoopback=false}){
  this.safeStorage=safeStorage;this.file=path.join(userData,'vault','logins.v1.json');
  this.allowLoopback=allowLoopback;
 }
 requireEncryption(){if(!available(this.safeStorage))throw Error('OS credential encryption unavailable. Set up Windows DPAPI or Linux Secret Service. Plaintext fallback is disabled.');}
 read(){
  this.requireEncryption();
  if(!fs.existsSync(this.file))return {version:1,items:{}};
  if(fs.statSync(this.file).size>1024*1024)throw Error('Vault file exceeds limit');
  const data=JSON.parse(fs.readFileSync(this.file,'utf8'));
  if(data.version!==1||!data.items||typeof data.items!=='object'||Array.isArray(data.items))throw Error('Unsupported vault format');
  return data;
 }
 write(data){
  this.requireEncryption();const dir=path.dirname(this.file);fs.mkdirSync(dir,{recursive:true,mode:0o700});
  const temp=this.file+'.tmp-'+process.pid;
  fs.writeFileSync(temp,JSON.stringify(data),{mode:0o600,flag:'wx'});
  try{fs.renameSync(temp,this.file)}finally{if(fs.existsSync(temp))fs.unlinkSync(temp);}
 }
 list(){
  const data=this.read();
  return {items:Object.entries(data.items).map(([origin,x])=>({origin,username:x.username,autofill:!!x.autofill,updatedAt:x.updatedAt})).sort((a,b)=>b.updatedAt.localeCompare(a.updatedAt))};
 }
 save({url,username,password,autofill=true}){
  const origin=originOf(url,this.allowLoopback);
  if(typeof username!=='string'||!username.trim()||username.length>128)throw Error('Invalid username');
  if(typeof password!=='string'||!password||password.length>4096)throw Error('Invalid password');
  const data=this.read();
  if(!data.items[origin]&&Object.keys(data.items).length>=300)throw Error('Vault entry limit reached');
  const encoded=this.safeStorage.encryptString(password).toString('base64');
  data.items[origin]={username:username.trim(),secret:encoded,autofill:autofill===true,updatedAt:new Date().toISOString()};
  this.write(data);return {ok:true,origin,username:username.trim(),autofill:autofill===true};
 }
 remove({origin}){
  const key=originOf(origin,this.allowLoopback),data=this.read();
  const found=Object.hasOwn(data.items,key);delete data.items[key];if(found)this.write(data);
  return {ok:true,deleted:found,origin:key};
 }
 forUrl(url,{autoOnly=false}={}){
  const key=originOf(url,this.allowLoopback),rec=this.read().items[key];
  if(!rec||autoOnly&&!rec.autofill)return null;
  return {origin:key,username:rec.username,password:this.safeStorage.decryptString(Buffer.from(rec.secret,'base64'))};
 }
 status(){
  return {available:available(this.safeStorage),backend:available(this.safeStorage)?(this.safeStorage.getSelectedStorageBackend?.()||(process.platform==='win32'?'Windows DPAPI':process.platform==='darwin'?'macOS Keychain':'OS keyring')):'unavailable',plaintextFallback:false};
 }
}
const FILL_JS=({username,password,origin})=>`(()=>{if(location.origin!==${JSON.stringify(origin)})return {filled:false,reason:'origin_changed'};const visible=e=>e&&!e.disabled&&!e.readOnly&&e.getClientRects().length>0;
 const pass=[...document.querySelectorAll('input[type=password]')].find(visible);
 if(!pass)return {filled:false,reason:'no_password_field'};
 const form=pass.closest('form')||document;
 const fields=[...form.querySelectorAll('input')].filter(visible);
 const user=fields.find(e=>e!==pass&&e.type!=='password'&&
   /^(?:text|email|tel|search)?$/.test(e.type||'text')&&
   !/otp|one.?time|two.?factor|captcha|verification|card|cvv/i.test(
    [e.name,e.id,e.autocomplete,e.placeholder].join(' ')));
 const set=(el,value)=>{const setter=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value')?.set;
  if(!setter)return false;setter.call(el,value);el.dispatchEvent(new Event('input',{bubbles:true}));
  el.dispatchEvent(new Event('change',{bubbles:true}));return true};
 if(user)set(user,${JSON.stringify(username)});
 set(pass,${JSON.stringify(password)});
 return {filled:true,usernameFilled:!!user,passwordFilled:true,submitted:false};
})()`;
module.exports={WolfVault,originOf,FILL_JS};
