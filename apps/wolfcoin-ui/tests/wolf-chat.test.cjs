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
 assert.match(await answer('What can you do?',backend),/My advanced cognition is not yet available/);
 assert.match(await answer('Hello there',backend),/My advanced cognition/);
 assert.match(await answer('Balance?',null),/Native backend unavailable/);
 assert.equal(calls.length,4);
 assert(calls.every(x=>['accounts.list','financial.history'].includes(x.op)));
 assert.match(html,/<button class="brand" data-action="wolf-chat"/);
 assert.match(html,/id="wolf-chat-form"/);
 assert.match(html,/case 'wolf-chat':openWolfChat\(\)/);
 assert.match(html,/querySelector\('#wolf-chat-form'\)\|\|state.tab/);
 const parse=ctx.wolfChatCommand,run=ctx.wolfChatRunCommand;
 const seen=[],prefs={notifications:true,persist:true,theme:'dark',searchEngine:'google'};
 let collapsed=false;
 const ui={go:async page=>seen.push(['page',page]),action:async(action,dataset)=>{
  seen.push(['action',action]);
  if(action==='toggle-sidebar')collapsed=!collapsed;
  if(action==='toggle-setting')prefs[dataset.key]=!prefs[dataset.key];
 },sidebar:()=>collapsed,preference:key=>prefs[key],select:async(key,value)=>{prefs[key]=value;seen.push(['select',key,value]);}};
 const pages=['overview','browser','accounts','sessions','platforms','financial data','activity','settings','security'];
 for(const page of pages){
  const command=parse('Please open the '+page+' screen.');
  assert.equal(command.kind,'navigate');
  await run(command,ui);
 }
 assert.equal(seen.filter(x=>x[0]==='page').length,9);
 for(const label of ['financial report','notifications','device status','integration status','bookmarks','add account','a new tab']){
  const command=parse('open '+label);assert.equal(command.kind,'dialog');await run(command,ui);
 }
 await run(parse('collapse sidebar'),ui);await run(parse('collapse sidebar'),ui);
 assert(collapsed);assert.equal(seen.filter(x=>x[1]==='toggle-sidebar').length,1);
 await run(parse('expand sidebar'),ui);assert(!collapsed);
 await run(parse('turn off notifications'),ui);await run(parse('turn off notifications'),ui);
 assert.equal(prefs.notifications,false);assert.equal(seen.filter(x=>x[1]==='toggle-setting').length,1);
 await run(parse('set tab restoration off'),ui);assert.equal(prefs.persist,false);
 await run(parse('use high contrast theme'),ui);assert.equal(prefs.theme,'high-contrast');
 await run(parse('set search engine to bing'),ui);assert.equal(prefs.searchEngine,'bing');
 for(const command of ['open __proto__','open constructor','execute javascript','remove all accounts','open financial report and delete accounts','submit a wager','turn on automation','set search engine to arbitrary'])assert.equal(parse(command),null);
 await assert.rejects(()=>run(parse('turn on notifications'),{...ui,action:async()=>{}}),/not applied/);
 console.log('WOLF_CHAT_WORKSPACE_COMMANDS_PASS');
 console.log('WOLF_CHAT_READ_ONLY_CONVERSATION_PASS');
})().catch(e=>{console.error(e);process.exitCode=1});

