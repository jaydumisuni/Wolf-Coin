/* Bind the nine-screen desktop UI to the existing signed native backend. */
(function(){
'use strict';
const back=window.wolfBackend;
if(!back)return;
let cached=null,connected=false,busy=null;
const html=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt=(v,c)=>v==null?'—':(c==='ZMW'?'K':c+' ')+Number(v).toLocaleString('en-US',{maximumFractionDigits:2});
function updateAccount(x){
 let a=state.accounts.find(y=>y.id===x.account_id);
 if(!a){
  a={id:x.account_id,name:x.display_name,url:'',type:x.domain==='trading'?'Trading':'Betting',
    user:x.account_id,known:false,status:'unverified',sync:'Recovered from backend',device:'Wolf Browser'};
  state.accounts.push(a);
 }
 const values=x.latest_financial?.fields||{};
 a.name=x.display_name;
 a.financialCurrency=x.currency;
 a.balance=values.cash_balance!==undefined?Number(values.cash_balance):null;
 a.pending=values.pending_bets!==undefined?Number(values.pending_bets):null;
 a.pnl=values.realized_pnl!==undefined?Number(values.realized_pnl):null;
 a.known=a.balance!==null&&Number.isFinite(a.balance);
 a.status=state.monitorPausedIds?.[a.id]?'paused':x.session_state==='PAUSED'?'paused':x.session_state==='LOGGED_OUT'?((Number(x.observation_count)>0||a.status==='loggedout'||Date.parse(x.session_changed_at)>Date.parse(x.registered_at))?'loggedout':'unverified'):x.session_state==='ACTIVE'&&x.freshness==='CURRENT_UNVERIFIED'?'connected':'unverified';
 a.sync=x.freshness;
 a.lastObserved=x.latest_financial?.observed_at||null;
}
async function refresh(){
 if(busy)return busy;
 busy=(async()=>{
  cached=await back.snapshot();
  for(const a of cached.accounts||[])updateAccount(a);
  state.lastSync='Native backend · '+new Date().toLocaleTimeString();
  render();
  return cached;
 })();
 try{return await busy}finally{busy=null}
}
function currencySummary(){
 const totals=cached?.finance?.currency_totals||{};
 const rows=Object.entries(totals);
 if(!rows.length)return '<div class="notice">No current backend financial observations.</div>';
 return rows.map(([c,x])=>'<div class="mini-stat"><b>'+html(c)+'</b> <span>Cash '+html(fmt(x.cash_balance,c))+' · Pending '+html(fmt(x.pending_bets,c))+
  ' · P/L '+html(fmt(x.realized_pnl,c))+'</span></div>').join('');
}
function transactions(){
 const all=(cached?.history||[]).flatMap(a=>(a.transactions||[]).map(t=>({...t,account:a.account_id})));
 all.sort((a,b)=>(b.occurred_at||'').localeCompare(a.occurred_at||''));
 return all.length?all.slice(0,100).map(x=>'<div class="mini-stat"><span>'+html(x.occurred_at)+' '+html(x.account)+' '+html(x.kind)+
  ' '+html(x.status)+'</span><b>'+html(x.amount)+'</b></div>').join(''):'<div class="notice">No backend transactions recorded.</div>';
}
let detailRecords=[];
function activityRecords(){
 const accounts=new Map((cached?.accounts||[]).map(x=>[x.account_id,x]));
 const rows=[];
 for(const h of cached?.history||[]){
  const account=accounts.get(h.account_id),isTrade=account?.domain==='trading';
  for(const tx of h.transactions||[]){
   rows.push({type:isTrade?'Trades':'Bets',kind:'transaction',title:(isTrade?'Trade':'Bet')+' · '+String(tx.kind||'Transaction'),
    when:tx.occurred_at||'',accountName:account?.display_name||h.account_id,accountId:h.account_id,
    currency:account?.currency||'',detail:tx,status:tx.status||'Not stated',amount:tx.amount});
  }
 }
 for(const item of cached?.activity||[]){
  const data=item.detail||{},aid=data.account_id||null,account=accounts.get(aid);
  const isTrade=account?.domain==='trading',financial=/(?:decision|bet|trade|transaction|settlement|receipt)/i.test(item.kind||'');
  const type=financial&&account?(isTrade?'Trades':'Bets'):'System';
  rows.push({type,kind:'audit',title:String(item.kind||'Audit event'),
   when:item.occurred_at||'',accountName:account?.display_name||aid||'Wolf-Coin',accountId:aid,
   currency:account?.currency||'',detail:item,status:data.status||data.outcome||'Recorded',amount:data.amount??data.proposed_amount??null});
 }
 return rows.sort((x,y)=>String(y.when).localeCompare(String(x.when)));
}
function renderActivityRows(limit=150){
 detailRecords=activityRecords();
 const f=state.activityFilter||'All',q=String(state.activityQuery||'').toLowerCase().trim();
 const chosen=detailRecords.map((row,id)=>({...row,id})).filter(x=>
   (f==='All'||f===x.type)&&(!q||[x.title,x.accountName,x.status,x.when,JSON.stringify(x.detail)].join(' ').toLowerCase().includes(q)));
 return chosen.slice(0,limit).map(x=>`<button type="button" class="backend-activity-entry" data-action="backend-event-details" data-record-index="${x.id}">
  <span class="backend-activity-main"><b>${html(x.title)}</b><small>${html(x.accountName)} · ${html(x.when)}</small></span>
  <span>${html(x.status)}</span>${x.amount==null?'':`<strong>${html(fmt(x.amount,x.currency))}</strong>`}
  ${icon('chevron','sm')}</button>`).join('')||'<div class="empty">No matching transactions or activity recorded.</div>';
}
function audit(){return renderActivityRows(35);}
function eventDetailDialog(record){
 if(!record)return;
 const x=record.detail||{},details=record.kind==='audit'?(x.detail||{}):x;
 const accountId=record.accountId;
 const fields=[
  ['Event',record.title],['Category',record.type],['Platform',record.accountName],
  ['Timestamp',record.when],['Status',record.status],['Amount',record.amount==null?'Not recorded':fmt(record.amount,record.currency)],
  ['Transaction ID',details.transaction_id],['Action / kind',details.action_kind||details.kind],
  ['Market or instrument',details.instrument||details.market],
  ['Selection / side',details.selection||details.side],
  ['Odds / quote',details.quote||details.odds],
  ['Decision ID',details.decision_id],
  ['Result reference',details.result_ref],
  ['Recorded evidence',details.source_observation_id||details.observation_id],
  ['Audit sequence',x.seq],
  ['Verification',record.kind==='audit'?'Signed local audit; platform outcome requires readback':'Unverified platform-reported record']
 ].filter(([label,val])=>val!==undefined&&val!==null&&val!=='');
 const safeDetails=Object.fromEntries(Object.entries(details||{}).filter(([key])=>!/(password|secret|cookie|token|credential|api.?key|private.?key)/i.test(key)));
 const known=new Set(['transaction_id','action_kind','kind','instrument','market','selection','side','quote','odds','decision_id','result_ref','source_observation_id','observation_id','amount','proposed_amount','status','outcome']);
 for(const [key,value] of Object.entries(safeDetails)){
  if(known.has(key))continue;if(fields.length>=32)break;
  fields.push([key,typeof value==='object'?JSON.stringify(value).slice(0,2000):String(value).slice(0,300)]);
 }
 modal(record.kind==='audit'?'Activity record':'Transaction details',`<div class="stack">${fields.map(([label,value])=>
  `<div class="mini-stat"><span class="muted">${html(label)}</span><strong style="overflow-wrap:anywhere;max-width:65%;text-align:right">${html(value)}</strong></div>`).join('')}
  ${!('instrument' in safeDetails||'market' in safeDetails||'selection' in safeDetails||'side' in safeDetails)?'<div class="notice">The source did not record a specific market/selection for this event. No details have been invented.</div>':''}
  </div>`,accountId&&state.accounts.some(a=>a.id===accountId)?
    btn('View account','inspect-account','',`data-id="${html(accountId)}"`)+btn('Close','close-modal'):
    btn('Close','close-modal'));
}
function evidenceChart(){
 const groups=(cached?.history||[]).map(h=>({
  account:cached?.accounts?.find(a=>a.account_id===h.account_id),
  points:(h.observations||[]).filter(o=>o.fields?.cash_balance!==undefined)
    .map(o=>({when:o.observed_at,value:Number(o.fields.cash_balance)}))
    .filter(o=>Number.isFinite(o.value)).sort((a,b)=>a.when.localeCompare(b.when))
 })).filter(h=>h.points.length>0);
 if(!groups.length)return '<div class="notice">No financial history observed yet.</div>';
 const plots=[];
 for(const h of groups){
  const x=h.points,max=Math.max(...x.map(v=>v.value)),min=Math.min(...x.map(v=>v.value));
  const span=Math.max(1,max-min),last=x[x.length-1];
  const points=x.map((v,i)=>(14+i*432/Math.max(1,x.length-1)).toFixed(1)+','+(136-119*(v.value-min)/span).toFixed(1)).join(' ');
  const label=html(h.account?.display_name||h.account?.account_id||'Account');
  const curr=html(h.account?.currency||'');
  plots.push('<div class="panel-body"><strong>'+label+' · '+curr+'</strong> · '+
   x.length+' observations · latest '+html(fmt(last.value,curr))+
   '<svg viewBox="0 0 460 150" style="width:100%;height:150px;margin-top:8px" role="img" aria-label="Historical cash balances for '+label+'"><polyline points="'+points+'" fill="none" stroke="#26c8ff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>'+
   (x.length===1?'<circle cx="14" cy="136" r="4" fill="#26c8ff"/>':'')+'</svg></div>');
 }
 return plots.join('');
}
function nativeMetrics(){
 const rows=Object.entries(cached?.finance?.currency_totals||{});
 const only=rows.length===1?rows[0]:null;
 const labelValue=field=>only?fmt(only[1][field],only[0]):rows.length?'By currency':'—';
 const detail=rows.length===1?only[0]:rows.length?'See currency breakdown':'Awaiting observations';
 const a=cached?.accounts||[];
 const active=a.filter(x=>x.session_state==='ACTIVE').length;
 return '<div class="metrics">'+
  metric('Total Balance',labelValue('cash_balance'),'balance',detail)+
  metric('Total Profit/Loss',labelValue('realized_pnl'),'profit',detail)+
  metric('Total Pending',labelValue('pending_bets'),'pending',detail)+
  metric('Connected Accounts',String(active)+' / '+a.length,'accounts',
    (a.length-active)+' not active')+'</div>';
}
function nativeSessionRows(){
 const accounts=(cached?.accounts||[]).slice(0,5);
 if(!accounts.length)return '<div class="empty">No registered accounts yet.</div>';
 return accounts.map(a=>{
  const active=a.session_state==='ACTIVE';
  const statusText=a.session_state==='LOGGED_OUT'?'Logged out':
    a.session_state==='PAUSED'?'Paused':active?'Active':'Unverified';
  const statusClass=active?'status':a.session_state==='LOGGED_OUT'?'status out':'status warn';
  return '<div class="session-row backend-session-row">'+
    '<span class="backend-session-dot '+(active?'is-active':'')+'"></span>'+
    '<div><div class="session-name">'+html(a.display_name)+'</div><div class="session-sub">'+
    html(a.platform_id||a.domain)+' · '+html(a.freshness||'')+'</div></div>'+
    '<span class="'+statusClass+'">'+html(statusText)+'</span></div>';
 }).join('');
}
function nativeQuickActions(){
 return '<div class="backend-quick-actions">'+[
  ['globe','Place Bet','start-bet'],
  ['activity','Trade','start-trade'],
  ['plus','Add Account','add-account'],
  ['refresh','Sync All Data','sync-all'],
  ['file','View Reports','reports']
 ].map(([ic,label,action])=>
  '<button class="backend-quick-button" data-action="'+action+'">'+
   icon(ic,'sm')+'<span>'+label+'</span>'+icon('chevron','sm')+'</button>'
 ).join('')+'</div>';
}
function nativeHealth(){
 const a=cached?.accounts||[],h=cached?.history||[],events=cached?.activity||[];
 const dx=window.WOLF_DXQT?.status;
 const items=[
  ['Native browser',!!window.wolfNative,'Chromium host'],
  ['Application backend',connected,'Signed local bridge'],
  ['D-XQT runtime',dx==='ready',dx==='ready'?'Initialized':'Initializing'],
  ['Account registry',true,a.length+' registered'],
  ['Audit history',true,events.length+' events']
 ];
 return '<div class="backend-health">'+items.map(([label,ok,detail])=>
  '<div><span>'+html(label)+'</span><span class="'+(ok?'positive':'muted')+'">'+
  html(detail)+'</span></div>').join('')+'</div>';
}
const oldOverview=overview;
overview=function(){
 if(!connected)return oldOverview();
 return '<div class="overview-page backend-overview">'+
  pageHeader('Overview','All platforms, accounts and financial activity in one place.',
   btn('Place Bet','start-bet','primary')+btn('Trade','start-trade','primary')+btn('Sync Now','sync-all'),false)+nativeMetrics()+
  '<div class="backend-dashboard-top">'+
    panel('Account Summary','users',accountTable(true),
      '<button class="linklike" data-action="go" data-tab="accounts">View All →</button>')+
    panel('Session Health','monitor','<div class="panel-body">'+nativeSessionRows()+'</div>',
      '<button class="linklike" data-action="go" data-tab="sessions">View All →</button>')+
    panel('Quick Actions','activity','<div class="panel-body">'+nativeQuickActions()+'</div>')+
  '</div><div class="backend-dashboard-bottom">'+
    panel('Balance History','chart',evidenceChart())+
    panel('Activity Feed','list','<div class="panel-body">'+audit()+'</div>',
      '<button class="linklike" data-action="go" data-tab="activity">View All →</button>')+
    panel('Backend Financial Snapshot','wallet',
      '<div class="panel-body">'+currencySummary()+nativeHealth()+'</div>')+
  '</div>'+note()+'</div>';
};
RENDER.overview=overview;
const oldFinance=financePage;
financePage=function(){
 if(!connected)return oldFinance();
 return pageHeader('Financial Data','Native backend observations and transaction history',btn('Refresh','backend-refresh','primary')+
  btn('Export CSV','export-csv'))+panel('Balances by currency','wallet','<div class="panel-body">'+currencySummary()+'</div>')+
  panel('Balance History','chart',evidenceChart())+
  panel('Transactions','list','<div class="panel-body">'+transactions()+'</div>')+note();
};
const oldActivity=activityPage;
activityPage=function(){
 if(!connected)return oldActivity();
 const filters=['All','Bets','Trades','System'];
 const n=activityRecords();
 return pageHeader('Activity','Recorded bets, trades, transaction outcomes and signed audit trail',btn('Refresh','backend-refresh','primary')+
  btn('Export log','export-events'))+
  panel('Recorded Activity ('+n.length+')','list',`<div class="panel-body">
   <div class="inline-row spread" style="margin-bottom:12px"><div class="chip-row">${filters.map(f=>`<button class="chip ${f===state.activityFilter?'active':''}" data-action="activity-filter" data-filter="${f}">${f}</button>`).join('')}</div>
    <label class="search-field">${icon('search','sm')}<input id="activity-search" placeholder="Search account, event or outcome..." value="${html(state.activityQuery)}"></label></div>
  ${renderActivityRows()}</div>`)+note();
};
RENDER.finance=financePage;RENDER.activity=activityPage;
const oldReport=showReport;
showReport=function(){
 if(!connected)return oldReport();
 modal('Backend Financial Report','<div class="stack">'+currencySummary()+transactions()+audit()+'</div>',
  btn('Export CSV','export-csv','primary')+btn('Close','close-modal'));
};
const oldCsv=exportCsv;
exportCsv=function(){
 if(!connected)return oldCsv();
 const q=x=>'"'+String(x??'').replaceAll('"','""')+'"';
 const rows=[['Account','Domain','Currency','Date','Cash','Pending','P/L','Freshness']];
 for(const a of cached?.accounts||[])rows.push([a.account_id,a.domain,a.currency,a.latest_financial?.observed_at,
   a.latest_financial?.fields?.cash_balance,a.latest_financial?.fields?.pending_bets,
   a.latest_financial?.fields?.realized_pnl,a.freshness]);
 exportFile('wolfcoin-backend-financial.csv',rows.map(r=>r.map(q).join(',')).join('\r\n'),'text/csv');
};
const oldEvents=exportEvents;
exportEvents=function(){
 if(!connected)return oldEvents();
 exportFile('wolfcoin-backend-activity.json',JSON.stringify(cached?.activity||[],null,2));
};
const oldSyncAll=syncAll;
syncAll=async function(){
 if(!connected)return oldSyncAll();
 try{
  const sync=await back.syncAll(state.accounts.filter(a=>a.url&&a.status!=='paused'&&!state.monitorPausedIds?.[a.id]&&['Betting','Trading'].includes(a.type)));
  for(const item of sync.results){
   const a=state.accounts.find(x=>x.id===item.id);
   if(!a)continue;
   if(item.identity&&window.WolfPortfolio){
    window.WolfPortfolio.ingest(a,{
      accountId:a.id,url:a.url,auth:item.auth,observedAt:new Date().toISOString(),
      identity:item.identity,opportunities:item.opportunities||[],candidates:{}
    });
   }
   if(item.status==='ERROR')a.sync='Sync error: '+item.message;
  }
  await refresh();
  toast('Cross-platform sync: '+sync.results.filter(x=>x.status==='OBSERVED').length+' accounts observed');
 }catch(e){toast('Sync All: '+String(e),'warn')}
};
const oldSync=syncNativeAccount;
syncNativeAccount=async function(id,opts={}){
 await oldSync(id,opts);
 if(!connected)return;
 const a=getAccount(id);
 if(!a||a.type==='Other')return;
 try{
  if(a.status==='connected')await back.observeAccount(a);
  else if(a.status==='loggedout')await back.recordSession(a,'LOGGED_OUT');
  await refresh();
 }catch(e){if(!opts.quiet)toast('Backend sync: '+String(e),'warn')}
};
const oldAction=runAction;
document.addEventListener('click',e=>{
 const button=e.target.closest('[data-action="backend-event-details"]');
 if(!button)return;
 e.preventDefault();e.stopImmediatePropagation();
 eventDetailDialog(detailRecords[Number(button.dataset.recordIndex)]);
},true);

runAction=async function(action,el,event){
 const selected=el?.dataset?.id?getAccount(el.dataset.id):getAccount(state.selectedAccount);
 const result=await oldAction(action,el,event);
 if(!connected||!selected)return result;
 try{
  if(action==='terminate-session')await back.recordSession(selected,'LOGGED_OUT');
  else if(action==='pause-session'||action==='resume-session'||action==='pause-all'||action==='resume-all')return result;
  else if(action==='confirm-remove-account')await back.removeAccount(selected);
  else return result;
  await refresh();
 }catch(e){toast('Backend state: '+String(e),'warn')}
 return result;
};
document.addEventListener('submit',e=>{
 if(e.target?.id!=='account-form'||!connected)return;
 const id=e.target.querySelector('[name=account_id]')?.value;
 const name=e.target.querySelector('[name=name]')?.value?.trim();
 queueMicrotask(async()=>{
  const a=id?getAccount(id):state.accounts.findLast(x=>x.name===name);
  if(!a||a.type==='Other')return;
  try{await back.registerAccount(a);await refresh()}catch(e){toast('Backend register: '+String(e),'warn')}
 });
});
document.addEventListener('click',e=>{
 if(!e.target.closest('[data-action=backend-refresh]'))return;
 e.preventDefault();e.stopImmediatePropagation();
 refresh().catch(x=>toast('Backend refresh: '+String(x),'warn'));
},true);
window.WolfNativeIntegration={refresh,get snapshot(){return cached},get ready(){return connected}};
back.status().then(async v=>{if(!v.available){toast('Native backend unavailable: '+v.error,'warn');return}connected=true;await refresh()})
 .catch(e=>console.warn('Wolf backend:',String(e)));
})();

const activityCSS=document.createElement('style');activityCSS.textContent='.backend-activity-entry{display:flex;align-items:center;width:100%;gap:12px;padding:12px 8px;background:transparent;border:0;border-bottom:1px solid #294158;text-align:left;color:#eff7ff;cursor:pointer;font-size:12px}.backend-activity-entry:hover{background:#102c46}.backend-activity-main{flex:1;min-width:0}.backend-activity-main b,.backend-activity-main small{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.backend-activity-main small{font-size:11px;color:#9bb6cb;margin-top:5px}';document.head.appendChild(activityCSS);
