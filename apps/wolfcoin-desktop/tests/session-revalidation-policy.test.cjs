'use strict';
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
const path=require('node:path');
const ui=fs.readFileSync(path.join(__dirname,'..','backend_ui.js'),'utf8');
const template=fs.readFileSync(path.join(__dirname,'..','..','wolfcoin-ui','ui-template.html'),'utf8');
const calls=[];
let tick;
const state={accounts:[
 {id:'restore',url:'https://example.invalid/account',type:'Other',status:'paused'},
 {id:'manual',url:'https://example.invalid/account',type:'Other',status:'paused'},
],monitorPausedIds:{manual:true},settings:{autosync:true,enableAutomation:true,background:true,syncInterval:'15'}};
const ctx=vm.createContext({state,window:{wolfNative:{},wolfBackend:{syncAll:async accounts=>{calls.push(['all',accounts.map(a=>a.id)]);return {results:[]}}},WolfNativeIntegration:{refresh:async()=>{}}},document:{hidden:false},setInterval:(f)=>{tick=f;return 1},clearInterval:()=>{},getActiveBrowser:()=>({accountId:'restore'}),getAccount:id=>state.accounts.find(a=>a.id===id),syncNativeAccount:async id=>calls.push(['one',id]),logEvent:()=>{},console});
vm.runInContext(ui.slice(ui.indexOf('function updateAccount('),ui.indexOf('async function refresh(')),ctx);
for(const id of ['restore','manual'])vm.runInContext('updateAccount('+JSON.stringify({account_id:id,domain:'sports',display_name:'Fixture',currency:'ZMW',session_state:'PAUSED',freshness:'STALE_LAST_KNOWN'})+')',ctx);
assert.equal(state.accounts[0].status,'unverified');
assert.equal(state.accounts[0].sync,'Revalidation required');
assert.equal(state.accounts[1].status,'paused');
vm.runInContext(template.slice(template.indexOf('let wolfAutoTimer='),template.indexOf('function render(){',template.indexOf('let wolfAutoTimer=')))+'\nconfigureWolfAutoSync();',ctx);
(async()=>{await tick();assert.equal(JSON.stringify(calls),JSON.stringify([['one','restore'],['all',['restore']]]));console.log('WOLF_SESSION_REVALIDATION_POLICY_PASS')})().catch(e=>{console.error(e);process.exitCode=1});
