/* Wolf-Coin portfolio integration v1. Self-contained, no external imports. */
(function(root){
'use strict';
const CONTRACT='wolf.portfolio.v1';
const MATCH_SCHEMA='wolf.owner.match.v1';
const ACTION_SCHEMA='wolf.action.request.v1';
const badIdentity=/^(?:user|guest|my account|profile|customer|unknown|anonymous|not set|not available)$/i;
const key=x=>String(x??'').normalize('NFKC').trim().replace(/\s+/g,' ').toLocaleLowerCase('en');
const clean=x=>String(x??'').trim().replace(/\s+/g,' ').slice(0,120);
const validIdentity=x=>clean(x).length>=4&&!badIdentity.test(clean(x))&&!/[<>\n\r]/.test(String(x??''));
function initState(state){
 if(!state.portfolio||state.portfolio.version!==1)
   state.portfolio={version:1,groups:[],proposals:[],observations:[]};
 for(const field of ['groups','proposals','observations'])if(!Array.isArray(state.portfolio[field]))state.portfolio[field]=[];
 return state.portfolio;
}
function matchCandidates(accounts){
 const matches=[];
 for(let i=0;i<accounts.length;i++)for(let j=i+1;j<accounts.length;j++){
   const a=accounts[i],b=accounts[j];
   const ia=a.ownerEvidence,ib=b.ownerEvidence;
   if(!ia||!ib||ia.auth!=='probable_authenticated'||ib.auth!=='probable_authenticated')continue;
   if(!ia.observedAt||!ib.observedAt||!validIdentity(ia.displayName)||!validIdentity(ib.displayName))continue;
   if(key(ia.displayName)!==key(ib.displayName))continue;
   const ca=a.ownerGroupId,cb=b.ownerGroupId;
   if(ca&&ca===cb)continue;
   matches.push({schema:MATCH_SCHEMA,first:a.id,second:b.id,displayName:clean(ia.displayName),
     confidence:'suggested_match',verification:'browser_observation_only',
     evidence:[{accountId:a.id,url:ia.url,at:ia.observedAt,label:ia.label},
               {accountId:b.id,url:ib.url,at:ib.observedAt,label:ib.label}]});
 }
 return matches;
}
function groupPair(state,idA,idB){
 const portfolio=initState(state);
 const a=state.accounts.find(x=>x.id===idA),b=state.accounts.find(x=>x.id===idB);
 if(!a||!b||a.id===b.id)throw Error('Two distinct registered accounts required');
 const m=matchCandidates([a,b])[0];
 if(!m)throw Error('Two matching authenticated owner observations required');
 const left=portfolio.groups.find(g=>g.id===a.ownerGroupId);
 const right=portfolio.groups.find(g=>g.id===b.ownerGroupId);
 const name=m?.displayName||left?.displayName||right?.displayName;
 if(!name||!validIdentity(name))throw Error('No eligible observed owner');
 if(left&&right&&left.id!==right.id&&key(left.displayName)!==key(right.displayName))throw Error('Conflicting owner groups');
 const group=left||right||{id:'owner-'+cryptoRandom(),displayName:name,accountIds:[],createdAt:new Date().toISOString(),verification:'owner_confirmed_link'};
 for(const acct of [a,b]){if(!group.accountIds.includes(acct.id))group.accountIds.push(acct.id);acct.ownerGroupId=group.id;}
 if(right&&right!==group){
   for(const id of right.accountIds){const other=state.accounts.find(x=>x.id===id);if(other){other.ownerGroupId=group.id;if(!group.accountIds.includes(id))group.accountIds.push(id);}}
   portfolio.groups=portfolio.groups.filter(g=>g!==right);
 }
 if(!portfolio.groups.includes(group))portfolio.groups.push(group);
 return group;
}
function cryptoRandom(){
 return typeof crypto!=='undefined'&&typeof crypto.randomUUID==='function'
   ?crypto.randomUUID()
   :'local-'+Date.now().toString(36)+'-'+Math.random().toString(36).slice(2,13);
}
function unlinkAccount(state,id){
 const p=initState(state),a=state.accounts.find(x=>x.id===id);
 if(!a||!a.ownerGroupId)return false;
 const group=p.groups.find(g=>g.id===a.ownerGroupId);
 if(group){group.accountIds=group.accountIds.filter(x=>x!==id);if(group.accountIds.length<2){
  for(const x of group.accountIds){const member=state.accounts.find(y=>y.id===x);if(member)member.ownerGroupId=null;}
  p.groups=p.groups.filter(g=>g!==group);
 }}
 a.ownerGroupId=null;
 return true;
}
function ingest(state,account,snapshot){
 const p=initState(state);
 if(!account||!snapshot||snapshot.accountId!==account.id)throw Error('Observation/account identity mismatch');
 const at=snapshot.observedAt;
 if(!at||!Number.isFinite(Date.parse(at)))throw Error('Observation timestamp missing');
 if(snapshot.auth==='probable_authenticated'&&validIdentity(snapshot.identity?.displayName)){
   account.ownerEvidence={
     displayName:clean(snapshot.identity.displayName),label:clean(snapshot.identity.label),
     observedAt:at,url:clean(snapshot.url).slice(0,120),auth:snapshot.auth,
     verification:'browser_observation_only'
   };
 }
 const currency=snapshot.candidates?.balance?.currency;
 if(currency&&/^[A-Z]{3}$/.test(currency))account.financialCurrency=currency;
 const observations=Array.isArray(snapshot.opportunities)?snapshot.opportunities:[];
 for(const obs of observations.slice(0,30)){
   const market=clean(obs.market),selection=clean(obs.selection);
   const kind=obs.kind==='trade'?'trade':obs.kind==='bet'?'bet':null;
   const side=obs.side==='sell'?'sell':obs.side==='buy'?'buy':kind==='bet'?'back':null;
   const quote=Number(obs.quote),currency=String(obs.currency||'').toUpperCase();
   if(!market||!selection||!kind||!side||!Number.isFinite(quote)||quote<=0||quote>1e12||!/^[A-Z]{3}$/.test(currency))continue;
   const evidenceId='obs-'+account.id+'-'+key(market)+'-'+key(selection)+'-'+side+'-'+at;
   if(p.observations.some(x=>x.id===evidenceId))continue;
   p.observations.unshift({id:evidenceId,accountId:account.id,market,selection,kind,side,quote,currency,
     capturedAt:at,sourceUrl:String(snapshot.url||'').slice(0,200),verification:'candidate_only',
     confidence:'website_dom_observation',status:'unverified'});
 }
 p.observations=p.observations.slice(0,250);
 return {identity:account.ownerEvidence||null,matched:matchCandidates(state.accounts),observations:observations.length};
}
function comparisons(state){
 const p=initState(state),accounts=new Map(state.accounts.map(a=>[a.id,a])),groups=new Map(p.groups.map(g=>[g.id,g]));
 const bins=new Map();
 for(const obs of p.observations){
   const a=accounts.get(obs.accountId);
   if(!a?.ownerGroupId||!groups.has(a.ownerGroupId))continue;
   if(a.status!=='connected'||!obs.capturedAt||Date.now()-Date.parse(obs.capturedAt)>24*60*60*1000)continue;
   const groupKey=[a.ownerGroupId,key(obs.market),key(obs.selection),obs.kind,obs.side,obs.currency].join('|');
   if(!bins.has(groupKey))bins.set(groupKey,[]);
   bins.get(groupKey).push(obs);
 }
 const out=[];
 for(const [groupKey,entries] of bins){
   const latest=new Map();
   for(const item of entries){
     const prior=latest.get(item.accountId);
     if(!prior||Date.parse(item.capturedAt)>Date.parse(prior.capturedAt))latest.set(item.accountId,item);
   }
   const unique=[...latest.values()];
   if(unique.length<2)continue;
   const higher=unique[0].kind==='bet'||unique[0].side==='sell';
   unique.sort((a,b)=>higher?b.quote-a.quote:a.quote-b.quote);
   const best=unique[0],worst=unique.at(-1);
   out.push({key:groupKey,market:best.market,selection:best.selection,kind:best.kind,side:best.side,
     currency:best.currency,best,alternatives:unique.slice(1),spread:Math.abs(best.quote-worst.quote),
     ownerGroupId:accounts.get(best.accountId).ownerGroupId,status:'comparative_observation_only',
     explanation:higher?'Highest observed quote':'Lowest observed buy price'});
 }
 return out;
}
function requestAction(state,comparisonKey){
 const p=initState(state),comparison=comparisons(state).find(c=>c.key===comparisonKey);
 if(!comparison)throw Error('No current cross-platform comparison for this group');
 const a=state.accounts.find(x=>x.id===comparison.best.accountId);
 if(!a?.ownerGroupId||a.ownerGroupId!==comparison.ownerGroupId)throw Error('Account/owner group mismatch');
 const dedupe='candidate:'+comparison.best.id;
 const prior=p.proposals.find(x=>x.idempotencyKey===dedupe);
 if(prior)return prior;
 const request={schema:ACTION_SCHEMA,id:'req-'+cryptoRandom(),idempotencyKey:dedupe,
   ownerGroupId:a.ownerGroupId,accountId:a.id,platform:a.name,
   candidate:{market:comparison.market,selection:comparison.selection,kind:comparison.kind,side:comparison.side,
     quote:comparison.best.quote,currency:comparison.currency},
   source:{evidenceId:comparison.best.id,capturedAt:comparison.best.capturedAt,url:comparison.best.sourceUrl,
     verification:'candidate_only'},status:'pending_backend',createdAt:new Date().toISOString()};
 p.proposals.unshift(request);p.proposals=p.proposals.slice(0,80);
 return request;
}
function summaries(state){
 const p=initState(state);
 return p.groups.map(g=>{
  const accounts=state.accounts.filter(a=>g.accountIds.includes(a.id));
  const totals={};
  for(const a of accounts){
   if(!a.known||!Number.isFinite(a.balance))continue;
   const currency=a.financialCurrency||'ZMW';
   if(!totals[currency])totals[currency]={balance:0,pending:0,pnl:0,accounts:0,stale:0};
   totals[currency].balance+=a.balance;totals[currency].pending+=Number(a.pending)||0;
   totals[currency].pnl+=Number(a.pnl)||0;totals[currency].accounts++;
   if(a.status!=='connected')totals[currency].stale++;
  }
  return {...g,accounts,totals};
 });
}
const Core={CONTRACT,MATCH_SCHEMA,ACTION_SCHEMA,initState,matchCandidates,groupPair,unlinkAccount,ingest,comparisons,requestAction,summaries,key};
if(typeof module!=='undefined'&&module.exports)module.exports=Core;
root.WOLF_PORTFOLIO_CORE=Core;
})(typeof window!=='undefined'?window:globalThis);
