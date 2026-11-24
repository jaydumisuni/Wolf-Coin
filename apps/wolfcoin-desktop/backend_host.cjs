'use strict';
/* Native Wolf-Coin bridge: backend v0.1.0a10, signed stdin/stdout, host-owned key. */
const fs=require('node:fs');
const path=require('node:path');
const os=require('node:os');
const crypto=require('node:crypto');
const {spawn}=require('node:child_process');
const {StringDecoder}=require('node:string_decoder');
const canon=x=>{
 if(Array.isArray(x))return '['+x.map(canon).join(',')+']';
 if(x!==null&&typeof x==='object')return '{'+Object.keys(x).sort().map(k=>JSON.stringify(k)+':'+canon(x[k])).join(',')+'}';
 return JSON.stringify(x);
};
class WolfNativeBackend{
 constructor({stateDir,moduleDir=path.join(__dirname,'backend-runtime'),python=process.env.WOLF_BACKEND_PYTHON||((process.platform==='win32')?'python':'python3')}={}){
  if(!stateDir)throw Error('Private backend state directory required');
  this.stateDir=stateDir;this.moduleDir=moduleDir;this.python=python;
  this.keyFile=path.join(stateDir,'native-bridge.key');
  this.database=path.join(stateDir,'application.sqlite3');
  this.pending=new Map();this.queue=Promise.resolve();this.seq=0;this.child=null;
  this.onFailure=null;this.started=false;this.stderr='';
 }
 async start(){
  if(this.child)throw Error('Bridge already started');
  fs.mkdirSync(this.stateDir,{recursive:true,mode:0o700});
  if(!fs.existsSync(this.keyFile)){
   try{fs.writeFileSync(this.keyFile,crypto.randomBytes(32),{flag:'wx',mode:0o600});}
   catch(e){if(e.code!=='EEXIST')throw e}
  }
  const stat=fs.lstatSync(this.keyFile);
  if(!stat.isFile()||stat.isSymbolicLink()||stat.size!==32)throw Error('Native bridge key file invalid');
  if(process.platform!=='win32')fs.chmodSync(this.keyFile,0o600);
  this.key=fs.readFileSync(this.keyFile);
  const env={...process.env,PYTHONPATH:[this.moduleDir,process.env.PYTHONPATH||''].filter(Boolean).join(path.delimiter),PYTHONUNBUFFERED:'1'};
  this.child=spawn(this.python,['-m','wolf_app.bridge','--db',this.database,'--key-file',this.keyFile],
    {env,stdio:['pipe','pipe','pipe'],windowsHide:true});
  const child=this.child;
  let buf='';
  const decoder=new StringDecoder('utf8');
  child.stdout.on('data',data=>{
    buf+=decoder.write(data);
    for(let i;(i=buf.indexOf('\n'))!==-1;){
      const line=buf.slice(0,i);buf=buf.slice(i+1);
      if(!line.trim())continue;
      try{
       const msg=JSON.parse(line),p=this.pending.get(msg.request_id);
       if(!p)continue;this.pending.delete(msg.request_id);clearTimeout(p.timer);p.resolve(msg);
      }catch(e){this.fail(e);}
    }
  });
  child.stderr.on('data',data=>{this.stderr=(this.stderr+data.toString('utf8')).slice(-1800)});
  child.on('error',e=>this.fail(e));
  child.on('exit',(code,signal)=>{
    this.fail(Error('Wolf backend child exited '+(code??signal??'unknown')));
    this.child=null;this.started=false;
  });
  const answer=await this.request('host.startup',{host_instance_id:'host_'+crypto.randomUUID().replace(/-/g,'')});
  this.started=true;
  return answer;
 }
 fail(err){for(const p of this.pending.values()){clearTimeout(p.timer);p.reject(err)}this.pending.clear();if(this.onFailure)this.onFailure(err);}
 async request(operation,payload={}){
  if(!this.child||this.child.killed)throw Error('Wolf backend child not started');
  const request_id='n'+(++this.seq).toString(36)+'_'+crypto.randomUUID().replace(/-/g,'');
  const request={schema:'wolf.app.request.v1',request_id,operation,payload};
  const auth_tag=crypto.createHmac('sha256',this.key).update(canon(request),'utf8').digest('hex');
  const line=JSON.stringify({...request,auth_tag})+'\n';
  const response=await new Promise((resolve,reject)=>{
   const timer=setTimeout(()=>{this.pending.delete(request_id);reject(Error('Backend request timed out: '+operation));},20000);
   this.pending.set(request_id,{resolve,reject,timer});
   this.child.stdin.write(line,e=>{if(e){clearTimeout(timer);this.pending.delete(request_id);reject(e)}});
  });
  if(response.schema!=='wolf.app.bridge.v2'||response.request_id!==request_id)throw Error('Backend response contract mismatch');
  if(response.status!=='OK')throw Error('Backend '+operation+': '+(response.data?.error||'operation rejected'));
  return response.data;
 }
 async stop(){
  if(!this.child)return;
  const p=this.child;this.child=null;this.started=false;
  p.stdin.end();await new Promise(resolve=>{p.once('exit',resolve);setTimeout(()=>{if(p.exitCode===null)p.kill();resolve()},1500).unref()});
 }
}
module.exports={WolfNativeBackend,canon};
