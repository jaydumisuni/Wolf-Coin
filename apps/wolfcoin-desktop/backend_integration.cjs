'use strict';
/* Browser evidence -> signed backend bridge, using the existing app backend contract. */
const crypto=require('node:crypto');
function uid(prefix){return prefix+'_'+crypto.randomUUID().replace(/-/g,'')}
function scope(a){
 if(!a||!a.id)throw Error('Account ID required');
 const domain=a.type==='Trading'?'trading':a.type==='Betting'?'sports':a.domain;
 if(domain!=='sports'&&domain!=='trading')throw Error('Backend domain missing for '+(a.type||'account'));
 return {domain,account_id:String(a.id)};
}
function platform(a){
 const url=new URL(a.url);
 return 'site_'+crypto.createHash('sha256').update(url.hostname).digest('hex').slice(0,20);
}
function currency(a,snapshot){
 const c=snapshot?.candidates?.balance?.currency||a.financialCurrency||a.currency;
 if(!/^[A-Z]{3}$/.test(String(c||'')))throw Error('Account currency must be supplied or observed');
 return c;
}
function numeric(value){
 if(typeof value!=='number'||!Number.isFinite(value))return null;
 return String(Number(value.toFixed(6)));
}
function normalizedFields(snapshot){
 const c=snapshot.candidates||{};
 const out={};
 for(const [from,to] of [['balance','cash_balance'],['pending','pending_bets'],['pnl','realized_pnl']]){
  if(c[from]?.currency!==c.balance?.currency)continue;
  const number=numeric(c[from]?.value);
  if(number!==null)out[to]=number;
 }
 return out;
}
class WolfAppIntegration{
 constructor(host){this.host=host;this.queues=new Map();}
 async serialize(a,fn){const key=scope(a).domain+':'+scope(a).account_id;const prev=this.queues.get(key)||Promise.resolve();const work=prev.then(fn,fn);this.queues.set(key,work.catch(()=>{}));return work;}
 request(operation,payload){return this.host.request(operation,payload)}
 async ensureAccount(a,snapshot){
  const {domain,account_id}=scope(a);
  const all=await this.request('accounts.list',{});
  const found=all.accounts.find(x=>x.domain===domain&&x.account_id===account_id);
  if(found)return found;
  await this.request('account.register',{domain,account_id,platform_id:platform(a),currency:currency(a,snapshot),display_name:String(a.name||a.id).slice(0,80)});
  return this.request('account.read',{domain,account_id});
 }
 async observe(a,snapshot){
  return this.serialize(a,async()=>{
  const origin=new URL(snapshot.url).hostname;
  const d=scope(a);
  if(a.id!==snapshot.accountId)throw Error('Browser account mismatch');
  const registered=await this.ensureAccount(a,snapshot);
  const observedAt=snapshot.observedAt;
  const prior=Date.parse(registered.session_changed_at||'');
  if(Number.isFinite(prior)&&Date.parse(observedAt)<prior){
   return {registered:registered.account_id,skippedStale:true,account:await this.request('account.read',d),overview:await this.request('financial.overview',{})};
  }
  const state=snapshot.auth==='probable_authenticated'?'ACTIVE':snapshot.auth==='login_required'?'LOGGED_OUT':'PAUSED';
  const ref='browser_'+crypto.createHash('sha256').update(d.account_id).digest('hex').slice(0,22);
  const ses={...d,state,observed_at:observedAt,device_id:'wolf_desktop'};
  if(state==='ACTIVE')ses.session_ref=ref;
  await this.request('session.record',ses);
  const fields=normalizedFields(snapshot);
  let receipt=null;
  if(state==='ACTIVE'&&Object.keys(fields).length){
   const evidence_sha256=crypto.createHash('sha256').update(JSON.stringify({
     id:snapshot.accountId,url:snapshot.url,observedAt,auth:snapshot.auth,fields,
     identity:snapshot.identity||null,opportunities:snapshot.opportunities||[]
   })).digest('hex');
   receipt=await this.request('observation.ingest',{...d,observation_id:uid('obs'),session_ref:ref,observed_at:observedAt,source:'DOM',origin,evidence_sha256,fields});
  }
  const account=await this.request('account.read',d);
  const overview=await this.request('financial.overview',{});
  return {registered:registered.account_id,account,receipt,overview,identity:snapshot.identity||null,
    opportunities:snapshot.opportunities||[]};
  });
 }
 async session(a,state){
  return this.serialize(a,async()=>{
  const d=scope(a);
  const prior=await this.ensureAccount(a);
  const latest=Date.parse(prior.session_changed_at||'');
  const when=new Date(Math.max(Date.now(),Number.isFinite(latest)?latest+1:0)).toISOString();
  return this.request('session.record',{...d,state,observed_at:when});
  });
 }
 async remove(a){
  return this.request('account.remove',scope(a));
 }
 async snapshot(){
  const [accounts,finance,activity]=await Promise.all([
    this.request('accounts.list',{}),this.request('financial.overview',{}),this.request('activity.list',{limit:100})
  ]);
  const history=[];
  for(const a of accounts.accounts){
   const d={domain:a.domain,account_id:a.account_id};
   const [transactions,observations]=await Promise.all([
    this.request('financial.history',{...d,kind:'TRANSACTIONS',limit:150}),
    this.request('financial.history',{...d,kind:'OBSERVATIONS',limit:150})
   ]);
   history.push({domain:a.domain,account_id:a.account_id,transactions:transactions.entries,observations:observations.entries});
  }
  return {schema:'wolf.host.snapshot.v1',accounts:accounts.accounts,finance,activity:activity.events,history};
 }
 async proposal(p){
  const available=await this.request('accounts.list',{});
  const found=available.accounts.find(x=>x.account_id===p.accountId);
  if(!found)throw Error('Account not registered in backend');
  const kind=p.candidate?.kind==='bet'?'PLACE_BET':p.candidate?.side==='sell'?'CLOSE_POSITION':'PLACE_TRADE';
  const human=[p.candidate?.market,p.candidate?.selection].filter(Boolean).join(' / ');
  const instrument='instrument_'+crypto.createHash('sha256').update(human).digest('hex').slice(0,32);
  const observations=await this.request('financial.history',{domain:found.domain,account_id:found.account_id,kind:'OBSERVATIONS',limit:1});
  const latest=observations.entries[0];
  if(!latest)throw Error('Backend has no matching account observation');
  const amount=p.proposed_amount;
  if(amount===undefined||amount===null||String(amount).trim()==='')
    return {status:'NEED_ACTION_AMOUNT',next_step:'SPECIFY_AMOUNT',candidate:p.candidate};
  const payload={
    domain:found.domain,account_id:found.account_id,
    decision_id:p.id?.replace(/[^A-Za-z0-9_.:-]/g,'_').slice(0,95)||uid('decision'),
    observation_id:latest.observation_id,
    instrument,action_kind:kind,
    proposed_amount:String(amount),
    ...(p.money_budget!==undefined?{money_budget:String(p.money_budget)}:{}),
    ...(p.browser_capabilities?{browser_capabilities:p.browser_capabilities}:{}),
    ...(p.platform_permissions?{platform_permissions:p.platform_permissions}:{})
  };
  return this.request('decision.propose',payload);
 }

}
module.exports={WolfAppIntegration,scope,normalizedFields,platform};
