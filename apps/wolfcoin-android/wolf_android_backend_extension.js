  // Trusted appassets renderer -> signed owner-held backend embedded in Android.
  const nativeRequest=(operation,payload={})=>invoke('backendRequest',{operation,payload});
  const domainOf=account=>account.type==='Trading'?'trading':account.type==='Betting'?'sports':account.domain;
  const sessionRef=account=>'android_'+String(account.id).replace(/[^A-Za-z0-9_:-]/g,'_').slice(0,105);
  const idSafe=value=>String(value||'').replace(/[^A-Za-z0-9_.:-]/g,'_').slice(0,108);
  const sha256=async text=>{
    const digest=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(String(text)));
    return [...new Uint8Array(digest)].map(x=>x.toString(16).padStart(2,'0')).join('');
  };
  function validateAccount(account){
    if(!account?.id)throw Error('Account ID required');
    const domain=domainOf(account);
    if(domain!=='sports'&&domain!=='trading')throw Error('Unknown account domain');
    return {domain,account_id:String(account.id)};
  }
  async function registered(account,snapshot){
    const d=validateAccount(account);
    const existing=await nativeRequest('accounts.list',{});
    const found=existing.accounts.find(x=>x.domain===d.domain&&x.account_id===d.account_id);
    if(found)return found;
    const url=new URL(account.url||snapshot?.url);
    const currency=String(account.financialCurrency||account.currency||snapshot?.candidates?.balance?.currency||'ZMW').toUpperCase();
    if(!/^[A-Z]{3}$/.test(currency))throw Error('Account currency is missing');
    await nativeRequest('account.register',{
      ...d,platform_id:'website_'+url.hostname.toLowerCase().replace(/[^a-z0-9_]/g,'_').slice(0,58),
      currency,display_name:String(account.name||account.id).slice(0,80)
    });
    return nativeRequest('account.read',d);
  }
  async function observeAccount(account){
    const d=validateAccount(account);
    // Register before capturing evidence: backend session lineage cannot
    // accept an observation timestamp older than account creation.
    await registered(account);
    const snapshot=await window.wolfNative.snapshot({accountId:account.id});
    if(snapshot.accountId!==account.id)throw Error('Account/snapshot mismatch');
    const ref=sessionRef(account),ts=snapshot.observedAt;
    const state=snapshot.auth==='probable_authenticated'?'ACTIVE':
      snapshot.auth==='login_required'?'LOGGED_OUT':'PAUSED';
    await nativeRequest('session.record',{...d,state,observed_at:ts,device_id:'android',
      ...(state==='ACTIVE'?{session_ref:ref}:{})});
    const candidates=snapshot.candidates||{},currency=candidates.balance?.currency,fields={};
    for(const [src,dst] of [['balance','cash_balance'],['pending','pending_bets'],['pnl','realized_pnl']]){
      if(candidates[src]?.currency===currency&&Number.isFinite(candidates[src]?.value))
        fields[dst]=String(candidates[src].value);
    }
    let receipt=null;
    if(state==='ACTIVE'&&Object.keys(fields).length){
      const evidence_sha256=await sha256(JSON.stringify({
        id:account.id,url:snapshot.url,observedAt:ts,auth:snapshot.auth,
        fields,identity:snapshot.identity||null,opportunities:snapshot.opportunities||[]
      }));
      receipt=await nativeRequest('observation.ingest',{
        ...d,observation_id:'obs_'+crypto.randomUUID().replaceAll('-',''),
        session_ref:ref,observed_at:ts,source:'DOM',
        origin:new URL(snapshot.url).hostname,evidence_sha256,fields
      });
    }
    return {receipt,account:await nativeRequest('account.read',d),
      overview:await nativeRequest('financial.overview',{}),identity:snapshot.identity||null,
      opportunities:snapshot.opportunities||[]};
  }
  async function backendSnapshot(){
    const [accounts,finance,activity]=await Promise.all([
      nativeRequest('accounts.list',{}),
      nativeRequest('financial.overview',{}),
      nativeRequest('activity.list',{limit:100})
    ]);
    const history=[];
    for(const a of accounts.accounts){
      const d={domain:a.domain,account_id:a.account_id};
      const [transactions,observations]=await Promise.all([
        nativeRequest('financial.history',{...d,kind:'TRANSACTIONS',limit:150}),
        nativeRequest('financial.history',{...d,kind:'OBSERVATIONS',limit:150})
      ]);
      history.push({...d,transactions:transactions.entries,observations:observations.entries});
    }
    return {schema:'wolf.host.snapshot.v1',accounts:accounts.accounts,
      finance,activity:activity.events,history};
  }
  async function backendProposal(proposal){
    const all=await nativeRequest('accounts.list',{});
    const a=all.accounts.find(x=>x.account_id===proposal.accountId);
    if(!a)throw Error('Account not registered in backend');
    if(proposal.proposed_amount==null||String(proposal.proposed_amount).trim()==='')
      return {status:'NEED_ACTION_AMOUNT',next_step:'SPECIFY_AMOUNT'};
    const history=await nativeRequest('financial.history',{domain:a.domain,account_id:a.account_id,kind:'OBSERVATIONS',limit:1});
    const latest=history.entries[0];
    if(!latest)throw Error('No current account observation');
    const c=proposal.candidate||{};
    const kind=c.kind==='bet'?'PLACE_BET':c.side==='sell'?'CLOSE_POSITION':'PLACE_TRADE';
    return nativeRequest('decision.propose',{
      domain:a.domain,account_id:a.account_id,decision_id:idSafe(proposal.id)||'android_decision_'+crypto.randomUUID(),
      observation_id:latest.observation_id,
      instrument:'instrument_'+(await sha256(String(c.market||'')+'/'+String(c.selection||''))).slice(0,32),
      action_kind:kind,proposed_amount:String(proposal.proposed_amount),
      ...(proposal.money_budget!==undefined?{money_budget:String(proposal.money_budget)}:{}),
      ...(proposal.browser_capabilities?{browser_capabilities:proposal.browser_capabilities}:{}),
      ...(proposal.platform_permissions?{platform_permissions:proposal.platform_permissions}:{})
    });
  }
  window.wolfBackend=Object.freeze({
    contract:'wolf.app.bridge.v2',
    status:()=>invoke('backendStatus'),
    request:nativeRequest,
    registerAccount:account=>registered(account),
    observeAccount,
    recordSession:async(account,state)=>{
      const d=validateAccount(account);
      await registered(account);
      return nativeRequest('session.record',{...d,state,observed_at:new Date().toISOString(),
        ...(state==='ACTIVE'?{session_ref:sessionRef(account)}:{})});
    },
    removeAccount:account=>nativeRequest('account.remove',validateAccount(account)),
    snapshot:backendSnapshot,
    proposeAction:backendProposal,
    syncAll:async accounts=>{
      const results=[];
      for(const a of accounts.slice(0,100)){
        try{
          await window.wolfNative.showBrowser({accountId:a.id,url:a.url});
          await new Promise(r=>setTimeout(r,170));
          const d=await observeAccount(a);
          results.push({id:a.id,status:'OBSERVED',auth:d.account?.session_state,
            identity:d.identity,opportunities:d.opportunities,backend:d.account});
        }catch(e){results.push({id:a.id,status:'ERROR',message:String(e).slice(0,180)})}
      }
      return {schema:'wolf.host.sync.v1',results,backend:await backendSnapshot()};
    }
  });
