/* Account grouping and comparisons in the nine-screen UI. Loaded after app script. */
(function(){
'use strict';
const core=window.WOLF_PORTFOLIO_CORE;
if(!core)throw Error('Wolf portfolio core unavailable');
const html=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const f=n=>Number(n).toLocaleString('en-US',{maximumFractionDigits:2,minimumFractionDigits:2});
function paint(){
 const main=document.querySelector('#main');
 if(!main||!['overview','accounts','platforms','finance'].includes(state.tab))return;
 const p=core.initState(state);
 // Dropped accounts are not retained in group membership.
 for(const g of p.groups)g.accountIds=g.accountIds.filter(id=>state.accounts.some(a=>a.id===id));
 p.groups=p.groups.filter(g=>g.accountIds.length>=2);
 const suggestions=core.matchCandidates(state.accounts);
 const summary=core.summaries(state);
 const compare=core.comparisons(state);
 const cards=[];
 cards.push('<section class="panel" data-pf-panel style="margin:15px 0;padding:16px"><header style="display:flex;justify-content:space-between;gap:14px;align-items:center;flex-wrap:wrap"><h3 style="margin:0;color:#edf7ff">Cross-platform owner & portfolio</h3><small style="color:#93afc9">Browser evidence · owner-confirmed links</small></header>');
 if(suggestions.length)cards.push('<div style="margin-top:10px"><b>Suggested same-owner matches</b>'+suggestions.map(m=>{
  const a=state.accounts.find(x=>x.id===m.first),b=state.accounts.find(x=>x.id===m.second);
  return '<div class="mini-stat" style="margin:8px 0"><span>'+html(a?.name)+' ↔ '+html(b?.name)+' · '+html(m.displayName)+'<small> · matching observed account-holder labels, not proof of legal ownership</small></span> <button type="button" class="btn primary" data-pf="link" data-a="'+html(m.first)+'" data-b="'+html(m.second)+'">Confirm Pair</button></div>';
 }).join('')+'</div>');
 if(!summary.length && !suggestions.length)cards.push('<div class="notice" style="margin-top:10px">No linked owners yet. Connect two accounts, inspect their authenticated account-holder labels, then confirm a suggested match. Credentials and sessions remain separate.</div>');
 for(const g of summary){
  cards.push('<div style="margin:12px 0 8px"><strong>'+html(g.displayName)+'</strong> · '+g.accounts.length+' linked accounts <span class="muted">('+html(g.verification)+')</span></div>');
  cards.push('<div class="inline-row" style="gap:8px;flex-wrap:wrap">'+g.accounts.map(a=>'<span class="chip">'+html(a.name)+' '+html(a.status)+' <button type="button" data-pf="unlink" data-id="'+html(a.id)+'" title="Unlink account" aria-label="Unlink '+html(a.name)+'" style="background:none;border:0;color:inherit;cursor:pointer">×</button></span>').join('')+'</div>');
  const totals=Object.entries(g.totals);
  cards.push(totals.length?totals.map(([curr,v])=>'<div class="mini-stat" style="margin:8px 0">'+html(curr)+' balance <strong>'+f(v.balance)+'</strong> · pending '+f(v.pending)+' · P/L '+f(v.pnl)+' · '+v.accounts+' candidates'+(v.stale?' · '+v.stale+' stale':'')+'</div>').join(''):'<div class="muted">No observed financial balances.</div>');
 }
 if(compare.length){
   cards.push('<div style="margin-top:12px"><strong>Cross-platform quote comparison</strong><div class="muted" style="font-size:12px">Same market, selection, side and currency · most recent DOM observations; not forecast profitability</div></div>');
   for(const c of compare.slice(0,12)){
     const a=state.accounts.find(x=>x.id===c.best.accountId);
     cards.push('<div class="mini-stat" style="margin:9px 0;gap:12px;flex-wrap:wrap"><span>'+html(c.market)+' / '+html(c.selection)+' · '+html(c.kind)+' '+html(c.side)+'<br><b>'+html(a?.name)+' '+f(c.best.quote)+'</b> '+html(c.currency)+' · spread '+f(c.spread)+' against '+c.alternatives.length+' alternative(s)</span><button type="button" class="btn" data-pf="propose" data-key="'+html(c.key)+'">Send Candidate to Backend Queue</button></div>');
   }
 }
 const pending=p.proposals.filter(x=>x.status==='pending_backend');
 if(pending.length)cards.push('<div class="notice" style="margin-top:12px">'+pending.length+' evidence-linked candidate request(s) queued for backend integration. No financial transaction has been executed.</div>');
 cards.push('</section>');
 main.insertAdjacentHTML('beforeend',cards.join(''));
}
const base=render;
render=function(...args){const x=base.apply(this,args);paint();return x;};
window.WolfPortfolio={
 ingest(account,snapshot){return core.ingest(state,account,snapshot)},
 snapshot(){return {state:core.initState(state),matches:core.matchCandidates(state.accounts),comparisons:core.comparisons(state)}},
 render:paint
};
document.addEventListener('click',async event=>{
 const el=event.target.closest('[data-pf]');
 if(!el)return;
 event.preventDefault();event.stopImmediatePropagation();
 try{
  const action=el.dataset.pf;
  if(action==='link'){
    const group=core.groupPair(state,el.dataset.a,el.dataset.b);
    logEvent('Owner link confirmed',group.displayName+' · '+group.accountIds.length+' linked platform accounts');
    save();render();toast('Accounts paired under '+group.displayName+'; sessions remain independent');
  } else if(action==='unlink'){
    const ok=core.unlinkAccount(state,el.dataset.id);
    if(ok){save();render();toast('Account unlinked; login session unaffected');}
  } else if(action==='propose'){
    const req=core.requestAction(state,el.dataset.key);
    save();render();
    const backend=window.wolfBackend;
    if(backend&&typeof backend.proposeAction==='function'){
      try{
       const receipt=await backend.proposeAction(req);
       req.status=receipt?.status||'submitted_backend';
       req.backendReceipt=receipt?.id||null;
       save();render();toast('Candidate sent to backend; no action executed by UI');
      }catch(e){req.status='pending_backend';save();render();toast('Backend unavailable; candidate remains queued','warn');}
    }else{
      window.dispatchEvent(new CustomEvent('wolf:action-request',{detail:req}));
      toast('Evidence-linked candidate queued; awaits your backend adapter');
    }
  }
 }catch(e){toast('Portfolio: '+String(e.message||e),'warn');}
},true);
paint();
})();
