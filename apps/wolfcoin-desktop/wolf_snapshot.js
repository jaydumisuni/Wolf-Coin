(()=>{
 const redact=s=>String(s||'').replace(/(?:password|passcode|api[_ -]?key|access[_ -]?token|secret|session[_ -]?id)\s*[:=]\s*\S+/ig,'[redacted]');
 const all=redact(document.body?.innerText||'').slice(0,50000);
 const sections=all.split(/\n+/).map(x=>x.trim()).filter(Boolean).slice(0,1100);
 const loginForm=[...document.querySelectorAll('input[type=password]')].some(e=>e.getClientRects().length>0);
 const signout=[...document.querySelectorAll('a,button')].some(e=>e.getClientRects().length>0&&/^(?:log\s*out|sign\s*out)$/i.test((e.innerText||e.getAttribute('aria-label')||'').trim()));
 const accountHeader=/(?:my account|account overview|my wallet|portfolio|account balance|account details)/i.test(sections.slice(0,140).join(' '));
 const auth=loginForm&&!signout?'login_required':signout||accountHeader?'probable_authenticated':'unverified';
 function candidate(type){
  const regex=type==='balance'?/^(?:available\s+)?(?:account\s+)?balance\b|^wallet(?: balance)?\b/i:type==='pending'?/^pending(?: bets| amount| exposure| stakes)?\b|^open(?: positions| bets| exposure)\b/i:/^(?:net\s+)?profit\s*(?:\/|&|and)\s*loss\b|^net\s*p\s*\/?\s*l\b|^realized\s+p\s*\/?\s*l\b/i;
  const found=[];
  for(let i=0;i<sections.length;i++){
   const s=sections[i];if(!regex.test(s))continue;
   const combined=(s+' '+(sections[i+1]||'')).slice(0,150);
   const m=combined.match(/(?:ZMW|K|ZK|USD|\$)\s*([+-]?[0-9][0-9,]*(?:\.[0-9]{1,2})?)/i);
   if(!m)continue;const n=Number(m[1].replaceAll(',',''));if(!Number.isFinite(n)||Math.abs(n)>1e12)continue;
   found.push({value:n,currency:/USD|\$/i.test(combined)?'USD':'ZMW',source:s.slice(0,100),label:type,verification:'candidate_only',confidence:'heuristic'});
  }
  return found.length===1?found[0]:null;
 }
 function identityCandidate(){
   if(auth!=='probable_authenticated')return null;
   const names=[];
   for(let i=0;i<sections.length;i++){
     const line=sections[i];
     const match=line.match(/^(account\s+holder|full\s+name|account\s+name|profile\s+name)\s*(?::|-)\s*(.*)$/i)
       ||line.match(/^(account\s+holder|full\s+name|account\s+name|profile\s+name)$/i);
     if(!match)continue;
     const value=(match[2]||sections[i+1]||'').trim().replace(/\s+/g,' ').slice(0,120);
     if(value.length<4 || /^(my account|user|guest|unknown)$/i.test(value))continue;
     names.push({displayName:value,label:match[1],verification:'browser_observation_only',confidence:'heuristic'});
   }
   return names.length===1?names[0]:null;
 }
 function opportunityCandidates(){
  const candidates=[],used=new Set();
  const balanceCurrency=candidate('balance')?.currency;
  function pick(raw,source){
   const market=String(raw.market||'').trim().slice(0,120),
    selection=String(raw.selection||'').trim().slice(0,120);
   const quote=Number(raw.quote),currency=String(raw.currency||balanceCurrency||'').toUpperCase();
   const kind=raw.kind==='trade'?'trade':'bet',side=raw.side==='buy'?'buy':raw.side==='sell'?'sell':'back';
   if(!market||!selection||market===selection||!Number.isFinite(quote)||quote<=0||
      kind==='bet'&&(quote<1.01||quote>1000)||!/^[A-Z]{3}$/.test(currency))return;
   const key=[market.toLowerCase(),selection.toLowerCase(),kind,side,currency].join('|');
   if(used.has(key))return;
   used.add(key);
   candidates.push({market,selection,kind,side,quote,currency,verification:'candidate_only',
     source,confidence:source==='explicit_dom'?'declared':'inferred_visible_control'});
  }
  for(const el of document.querySelectorAll('[data-wolf-opportunity]')){
   if(candidates.length>=40)break;
   if(!el.getClientRects().length)continue;
   pick({market:el.dataset.wolfMarket,selection:el.dataset.wolfSelection,
    quote:el.dataset.wolfQuote,kind:el.dataset.wolfKind,side:el.dataset.wolfSide,
    currency:el.dataset.wolfCurrency},'explicit_dom');
  }
  // Provider-independent DOM cues: market group + selection + visible price/odds control.
  const controls=document.querySelectorAll('[data-odds],[data-price],[data-quote],button,[role=button],.odds');
  let scanned=0;
  for(const el of controls){
   if(++scanned>1800||candidates.length>=40)break;
   if(!el.getClientRects().length)continue;
   const label=(el.getAttribute('aria-label')||el.innerText||'').trim().slice(0,140);
   const raw=el.getAttribute('data-odds')||el.getAttribute('data-quote')||
    el.getAttribute('data-price')||label.match(/(?:odds\s*[:=]\s*|price\s*[:=]\s*)(\d+(?:\.\d+)?)/i)?.[1];
   if(!raw||!/^(?:\d{1,9}(?:\.\d{1,6})?)$/.test(String(raw).trim()))continue;
   const group=el.closest('[data-market],.market,[role=group],[data-event],.event');
   const market=group?.getAttribute('data-market')||group?.getAttribute('data-event')||
     group?.querySelector('[data-market-name],.market-name,.market-title,h2,h3,h4')?.textContent||
     group?.getAttribute('aria-label')||'';
   const selection=el.getAttribute('data-selection')||el.closest('[data-selection]')?.getAttribute('data-selection')||
     el.getAttribute('aria-label')?.replace(/\b(?:odds|price)\b\s*[:=]?\s*\d+(?:\.\d+)?/ig,'').trim()||
     label.replace(/\b(?:odds|price)\b\s*[:=]?\s*\d+(?:\.\d+)?/ig,'').trim();
   const type=el.getAttribute('data-instrument-type')||group?.getAttribute('data-instrument-type')||
     (/(?:\b(?:buy|sell|bid|ask|shares?|stock|forex)\b)/i.test(label)?'trade':'bet');
   const side=el.getAttribute('data-side')||(/\bsell\b/i.test(label)?'sell':/\bbuy\b/i.test(label)?'buy':'back');
   pick({market,selection,quote:raw,kind:type,side,
     currency:el.getAttribute('data-currency')||group?.getAttribute('data-currency')||balanceCurrency},
    'inferred_visible_control');
  }
  return candidates;
 }
 function platformDiscovery(opportunities){
  const links=[...document.querySelectorAll('a[href]')].slice(0,300);
  const affordances={
   navigation:links.length,
   login:loginForm,
   account:accountHeader||signout,
   odds:opportunities.some(x=>x.kind==='bet'),
   prices:opportunities.some(x=>x.kind==='trade'),
   editableFields:document.querySelectorAll('input:not([type=hidden]),textarea,select').length,
   interactiveControls:document.querySelectorAll('button,[role=button]').length
  };
  return {hostname:location.hostname,title:document.title.slice(0,160),
   category:affordances.odds?'betting':affordances.prices?'trading':'unclassified',
   affordances,identifiedBy:'visible_dom',verification:'candidate_only'};
 }
 const opportunities=opportunityCandidates();
 return {url:location.href,title:document.title,visibleText:all.slice(0,12000),elementCount:document.querySelectorAll('*').length,
  auth,authEvidence:{loginFormVisible:loginForm,logoutControlVisible:signout,accountHeaderVisible:accountHeader},
  candidates:{balance:candidate('balance'),pending:candidate('pending'),pnl:candidate('pnl')},identity:identityCandidate(),opportunities,platformDiscovery:platformDiscovery(opportunities),observedAt:new Date().toISOString(),
  provenance:'browser visible DOM; heuristic candidates not independently verified'};
})()
