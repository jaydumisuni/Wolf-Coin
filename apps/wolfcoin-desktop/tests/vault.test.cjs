'use strict';
const assert=require('node:assert/strict');
const crypto=require('node:crypto');
const fs=require('node:fs');
const os=require('node:os');
const path=require('node:path');
const {WolfVault,originOf,FILL_JS}=require('../wolf_vault.cjs');
const dir=fs.mkdtempSync(path.join(os.tmpdir(),'wolf-vault-test-'));
const secret=crypto.randomBytes(32);
const storage={
 isEncryptionAvailable:()=>true,
 getSelectedStorageBackend:()=> 'dpapi',
 encryptString:value=>{
  const iv=crypto.randomBytes(12),cipher=crypto.createCipheriv('aes-256-gcm',secret,iv);
  return Buffer.concat([iv,cipher.update(value,'utf8'),cipher.final(),cipher.getAuthTag()]);
 },
 decryptString:bytes=>{
  const decipher=crypto.createDecipheriv('aes-256-gcm',secret,bytes.subarray(0,12));
  decipher.setAuthTag(bytes.subarray(bytes.length-16));
  return Buffer.concat([decipher.update(bytes.subarray(12,bytes.length-16)),decipher.final()]).toString('utf8');
 }
};
try{
 const v=new WolfVault({safeStorage:storage,userData:dir,allowLoopback:true});
 assert.equal(v.list().items.length,0);
 assert.throws(()=>v.save({url:'http://some-site.example/login',username:'a',password:'b'}),/HTTPS/);
 v.save({url:'https://wolf.example/sign-in',username:'engineer',password:'sample-test-secret',autofill:true});
 const list=v.list();assert.equal(list.items.length,1);assert.equal(list.items[0].origin,'https://wolf.example');
 assert(!JSON.stringify(list).includes('sample-test-secret'));
 const stored=fs.readFileSync(path.join(dir,'vault','logins.v1.json'),'utf8');
 assert(!stored.includes('sample-test-secret'));
 assert.equal(v.forUrl('https://wolf.example/account').password,'sample-test-secret');
 assert.equal(v.forUrl('https://other.example'),null);
 assert.equal(v.forUrl('https://evil.wolf.example'),null);
 assert.equal(v.forUrl('https://wolf.example:8443'),null);
 const script=FILL_JS(v.forUrl('https://wolf.example'));
 assert(script.includes('submitted:false'));assert(script.includes('type=password'));
 assert.equal(v.remove({origin:'https://wolf.example'}).deleted,true);
 assert.equal(v.list().items.length,0);
 const unsafe=new WolfVault({safeStorage:{...storage,getSelectedStorageBackend:()=> 'basic_text'},userData:dir});
 assert.throws(()=>unsafe.list(),/encryption unavailable/);
 console.log('WOLF_VAULT_NATIVE_CONTRACT_PASS',JSON.stringify({encryptedAtRest:true,exactOrigin:true,autofillNoSubmit:true,plaintextFallback:false}));
}finally{fs.rmSync(dir,{recursive:true,force:true})}
