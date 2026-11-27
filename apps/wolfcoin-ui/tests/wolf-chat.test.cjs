'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const html=fs.readFileSync(new URL('../ui-template.html','file://'+__filename),'utf8');
const code=html.split('// WOLF_CHAT_BEGIN')[1].split('// WOLF_CHAT_END')[0];
const ctx=vm.createContext({});
vm.runInContext(code,ctx);
const answer=ctx.wolfChatAnswer;
(async()=>{
 const calls=[];
 const backend={request:async(op,payload)=>{
  calls.push({op,payload});
  if(op==='accounts.list')return {accounts:[{domain:'sports',account_id:'fixture',display_name:'Fixture',session_state:'ACTIVE',freshness:'CURRENT_UNVERIFIED',observation_count:7,currency:'ZMW',latest_financial:{fields:{cash_balance:'3.5'}}}]};
  assert.equal(op,'financial.history');
  assert.equal(payload.account_id,'fixture');
  return {entries:[]};
 }};
 assert.match(await answer('What is my balance?',backend),/ZMW 3\.5/);
 assert.match(await answer('Account status?',backend),/ACTIVE.*7 observations/);
 assert.match(await answer('Transaction history?',backend),/No transaction records/);
 assert.match(await answer('What can you do?',backend),/COG conversation is not connected/);
 assert.match(await answer('Hello there',backend),/general cognition service/);
 assert.match(await answer('Balance?',null),/Native backend unavailable/);
 assert.equal(calls.length,4);
 assert(calls.every(x=>['accounts.list','financial.history'].includes(x.op)));
 assert.match(html,/<button class="brand" data-action="wolf-chat"/);
 assert.match(html,/id="wolf-chat-form"/);
 assert.match(html,/case 'wolf-chat':openWolfChat\(\)/);
 assert.match(html,/querySelector\('#wolf-chat-form'\)\|\|state.tab/);
 console.log('WOLF_CHAT_READ_ONLY_CONVERSATION_PASS');
})().catch(e=>{console.error(e);process.exitCode=1});

