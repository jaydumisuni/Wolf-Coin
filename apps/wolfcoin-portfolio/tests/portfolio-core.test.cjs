'use strict';
const assert=require('node:assert/strict');
const core=require('../portfolio.js');
const at=new Date().toISOString();
const acct=(id,name,owner,currency='ZMW')=>({id,name,status:'connected',known:true,balance:100,pending:10,pnl:5,
  financialCurrency:currency,
  ownerEvidence:owner?{displayName:owner,label:'Account Holder',observedAt:at,
    auth:'probable_authenticated',url:'https://'+id+'.example.org',verification:'browser_observation_only'}:null});
const state={accounts:[acct('sports-a','Sports A','Alex Example'),acct('sports-b','Sports B','Alex   Example'),
  acct('unrelated','Unrelated','Morgan Other'),acct('no-evidence','Unknown',null)]};
let p=core.initState(state);
assert.equal(core.matchCandidates(state.accounts).length,1,'must suggest only actual matching observations');
assert.throws(()=>core.groupPair(state,'sports-a','unrelated'),/matching authenticated/);
const group=core.groupPair(state,'sports-a','sports-b');
assert.equal(group.accountIds.length,2);
assert.equal(core.matchCandidates(state.accounts).length,0);
let summary=core.summaries(state)[0];
assert.equal(summary.totals.ZMW.balance,200);
assert.equal(summary.totals.ZMW.stale,0);
state.accounts[1].financialCurrency='USD';
summary=core.summaries(state)[0];
assert.equal(summary.totals.ZMW.balance,100);
assert.equal(summary.totals.USD.balance,100);
state.accounts[1].financialCurrency='ZMW';
state.accounts[1].status='loggedout';
assert.equal(core.summaries(state)[0].totals.ZMW.stale,1);
state.accounts[1].status='connected';
const obs=(account,quote)=>({accountId:account,auth:'probable_authenticated',observedAt:at,
  url:'https://'+account+'.example.org',
  identity:{displayName:'Alex Example',label:'Account Holder'},
  opportunities:[{market:'Fixture Match 2026-12-01',selection:'Home',
    kind:'bet',side:'back',currency:'ZMW',quote}],
  candidates:{balance:{value:100,currency:'ZMW'}}});
const oa=state.accounts[0],ob=state.accounts[1];
core.ingest(state,oa,obs('sports-a',2.1));
core.ingest(state,ob,obs('sports-b',2.3));
assert.equal(core.comparisons(state).length,1,'same-market opportunity comparison');
let cmp=core.comparisons(state)[0];
assert.equal(cmp.best.accountId,'sports-b');
assert(Math.abs(cmp.spread-0.2)<1e-9);
const proposal=core.requestAction(state,cmp.key);
assert.equal(proposal.status,'pending_backend');
assert.equal(proposal.source.verification,'candidate_only');
assert.equal(core.requestAction(state,cmp.key).id,proposal.id,'idempotent proposal');
assert.equal(p.proposals.length,1);
state.accounts[1].status='loggedout';
assert.equal(core.comparisons(state).length,0,'stale/logout observation unavailable for active comparison');
assert.equal(core.summaries(state)[0].accounts.length,2,'logout retains linked portfolio membership');
assert(core.unlinkAccount(state,'sports-b'));
assert.equal(p.groups.length,0,'single member group retired');
assert(state.accounts.every(a=>!a.ownerGroupId),'unlink does not delete account');
assert.throws(()=>core.ingest(state,oa,{accountId:'wrong',observedAt:at}),/mismatch/);
console.log('WOLF_PORTFOLIO_CORE_PASS',JSON.stringify({matches:1,currencyIsolation:true,stale:true,
  bestQuote:2.3,spread:0.2,idempotency:true,logoutRetention:true,unlink:true}));
