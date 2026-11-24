'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const os=require('node:os');
const path=require('node:path');
const crypto=require('node:crypto');
const {WolfNativeBackend}=require('../backend_host.cjs');
const moduleDir=path.join(__dirname,'..','backend-runtime');
const dir=fs.mkdtempSync(path.join(os.tmpdir(),'wolf-backend-native-test-'));
const date=shift=>new Date(Date.now()+shift*1000).toISOString();
const evidence=crypto.createHash('sha256').update('controlled-local-html-fixture').digest('hex');
const backend=()=>new WolfNativeBackend({stateDir:dir,moduleDir});
(async()=>{
 const one=backend();
 try{
  const start=await one.start();assert.equal(start.accounts_preserved,true);
  const caps=await one.request('bridge.capabilities');
  assert(caps.operations.includes('decision.propose'));
  const A={domain:'sports',account_id:'bet_a'},B={domain:'trading',account_id:'trade_a'};
  await one.request('account.register',{...A,platform_id:'sports_fixture',currency:'ZMW',display_name:'Sports site'});
  await one.request('account.register',{...B,platform_id:'trade_fixture',currency:'USD',display_name:'Trading site'});
  for(const [acct,session] of [[A,'sports_site_tab'],[B,'trading_site_tab']]){
   await one.request('session.record',{...acct,state:'ACTIVE',session_ref:session,observed_at:date(1),device_id:'KRATOS'});
  }
  await one.request('observation.ingest',{...A,observation_id:'sports_obs_1',session_ref:'sports_site_tab',
    observed_at:date(2),source:'DOM',origin:'example.org',evidence_sha256:evidence,
    fields:{cash_balance:'750',pending_bets:'100',realized_pnl:'60'}});
  await one.request('observation.ingest',{...B,observation_id:'trade_obs_1',session_ref:'trading_site_tab',
    observed_at:date(2),source:'DOM',origin:'example.net',evidence_sha256:evidence,
    fields:{cash_balance:'300',realized_pnl:'-10'}});
  const all=await one.request('accounts.list');assert.equal(all.accounts.length,2);
  const totals=await one.request('financial.overview');
  assert.equal(totals.currency_totals.ZMW.cash_balance,'750');
  assert.equal(totals.currency_totals.USD.cash_balance,'300');
  const history=await one.request('financial.history',{...A,kind:'OBSERVATIONS'});
  assert.equal(history.entries.length,1);
  const audit=await one.request('activity.list',{limit:25});assert.equal(audit.hash_chain_checked,true);
  await one.stop();
  const two=backend();try{
   const restarted=await two.start();assert.equal(restarted.sessions_requiring_revalidation,2);
   const restored=await two.request('accounts.list');assert.equal(restored.accounts.length,2);
   assert(restored.accounts.every(a=>a.freshness==='STALE_LAST_KNOWN'));
   assert(restored.accounts.every(a=>a.session_state==='PAUSED'));
   const totalStale=await two.request('financial.overview');assert.deepEqual(totalStale.currency_totals,{});
   const post=await two.request('activity.list');assert(post.events.length>=1);
  }finally{await two.stop();}
  console.log('WOLF_SIGNED_IPC_DESKTOP_PASS '+JSON.stringify({accounts:2,currencies:['ZMW','USD'],persistent:true,staleAfterRestart:true,history:true,audit:true}));
 }finally{await one.stop();fs.rmSync(dir,{recursive:true,force:true})}
})().catch(e=>{console.error('WOLF_SIGNED_IPC_DESKTOP_FAIL',e.stack||String(e));process.exitCode=2});
