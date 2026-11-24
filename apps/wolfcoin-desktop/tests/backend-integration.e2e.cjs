'use strict';
const assert=require('node:assert/strict');
const path=require('node:path');
const fs=require('node:fs');
const os=require('node:os');
const {WolfNativeBackend}=require('../backend_host.cjs');
const {WolfAppIntegration}=require('../backend_integration.cjs');
const stateDir=fs.mkdtempSync(path.join(os.tmpdir(),'wolf-host-integration-'));
const backend=new WolfNativeBackend({stateDir,moduleDir:path.join(__dirname,'..','backend-runtime')});
(async()=>{
 try{
 await backend.start();
 const app=new WolfAppIntegration(backend);
 const acct={id:'sports_acc_1',name:'Fixtures Sports',url:'http://127.0.0.1:44567/login',type:'Betting',currency:'ZMW'};
 const stamp=new Date(Date.now()+1000).toISOString();
 const snapshot={accountId:acct.id,url:'http://127.0.0.1:44567/dashboard',observedAt:stamp,auth:'probable_authenticated',candidates:{
   balance:{value:750,currency:'ZMW'},pending:{value:100,currency:'ZMW'},pnl:{value:60,currency:'ZMW'}
 },identity:{displayName:'Alex Example',label:'Account Holder'},opportunities:[]};
 const observation=await app.observe(acct,snapshot);
 assert.equal(observation.account.latest_financial.fields.cash_balance,'750');
 assert.equal(observation.overview.currency_totals.ZMW.cash_balance,'750');
 const full=await app.snapshot();
 assert.equal(full.accounts.length,1);
 assert.equal(full.history[0].observations.length,1);
 assert(full.activity.length>=3);
 const candidate={id:'test_bet_01',accountId:acct.id,platform:acct.name,
   candidate:{kind:'bet',side:'back',market:'Fixture Match',selection:'Home',quote:2.1,currency:'ZMW'},
   proposed_amount:'10',money_budget:'100',
   browser_capabilities:['PLACE_BET'],platform_permissions:['TRANSACT']};
 const decision=await app.proposal(candidate);
 assert.equal(decision.status,'BROWSER_HANDOFF_READY',JSON.stringify(decision));
 assert.equal(decision.browser_action_executed,false);
 const receipt=await app.request('decision.receipt',{
   domain:'sports',account_id:acct.id,decision_id:decision.decision_id,
   result_ref:'fixture_no_money_effect_001',outcome:'NOT_EXECUTED'
 });
 assert.equal(receipt.status,'NOT_EXECUTED');
 console.log('WOLF_NATIVE_DECISION_RECEIPT_PASS '+JSON.stringify({
  decision:decision.status,receipt:receipt.status,
  source:'synthetic_backend_only',actualFinancialAction:false
 }));
 await app.session(acct,'LOGGED_OUT');
 const after=await app.snapshot();
 assert.equal(after.accounts[0].session_state,'LOGGED_OUT');
 assert.equal(after.accounts[0].freshness,'STALE_LAST_KNOWN');
 await backend.stop();
 const again=new WolfNativeBackend({stateDir,moduleDir:path.join(__dirname,'..','backend-runtime')});
 try{await again.start();const read=await new WolfAppIntegration(again).snapshot();
 assert.equal(read.accounts.length,1);
 assert.equal(read.history[0].observations.length,1);
 }finally{await again.stop()}
 console.log('WOLF_REAL_BACKEND_BINDING_PASS '+JSON.stringify({hostSigned:true,registered:1,financialSnapshot:true,activity:true,logoutPreserved:true,restartPreserved:true}));
 }finally{await backend.stop();fs.rmSync(stateDir,{recursive:true,force:true})}
})().catch(e=>{console.error('FAIL',e.stack||e);process.exitCode=2});
