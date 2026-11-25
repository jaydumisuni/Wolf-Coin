(()=>{
 const redact=s=>String(s||'').replace(/(?:password|passcode|api[_ -]?key|access[_ -]?token|secret|session[_ -]?id)\s*[:=]\s*\S+/ig,'[redacted]');
 const all=redact(document.body?.innerText||'').slice(0,50000);
 const sections=all.split(/\n+/).map(x=>x.trim()).filter(Boolean).slice(0,1100);
 const loginForm=[...document.querySelectorAll('input[type=password]')].some(e=>e.getClientRects().length>0);
 const signout=[...document.querySelectorAll('a,button')].some(e=>e.getClientRects().length>0&&/^(?:log\s*out|sign\s*out)$/i.test((e.innerText||e.getAttribute('aria-label')||'').trim()));
 // A public "Create a portfolio" link is NOT evidence of a logged-in account.
 const signin=[...document.querySelectorAll('a,button')].some(e=>e.getClientRects().length>0&&/^(?:sign\s*in|log\s*in|login)$/i.test((e.innerText||e.getAttribute('aria-label')||'').trim()));
 const accountHeader=/(?:\bmy account\b|account overview|my wallet|account balance|account details)/i.test(sections.slice(0,140).join(' '));
 const auth=loginForm&&!signout?'login_required':signout?'probable_authenticated':signin?'unverified':accountHeader?'probable_authenticated':'unverified';
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
 // Public market price observations are not actionable broker trade controls.
 // Cross-check an instrument identifier in the URL, a visible title price,
 // and the currency displayed near that instrument before emitting evidence.
 function publicMarketQuotes(){
   const quotes=[];
   const title=document.title.trim();
   const m=title.match(/^([A-Z][A-Z0-9.-]{0,15})\s+((?:USD|CAD|AUD|EUR|GBP|ZMW)\s+|[$€£])\s*([0-9][0-9,]*(?:\.[0-9]{1,4})?)/i);
   if(!m)return quotes;
   let pathname;
   try{pathname=decodeURIComponent(location.pathname)}catch{return quotes}
   const pathMatch=pathname.match(/\/(?:finance\/quote|quote)\/([A-Za-z0-9._:-]{1,36})/i);
   if(!pathMatch)return quotes;
   const instrument=pathMatch[1].toUpperCase(),symbol=m[1].toUpperCase();
   if(instrument!==symbol&&!instrument.startsWith(symbol+':')&&!instrument.startsWith(symbol+'.'))return quotes;
   const value=Number(m[3].replaceAll(',',''));
   if(!Number.isFinite(value)||value<=0||value>1e12)return quotes;
   const instrumentAt=all.toUpperCase().indexOf(instrument);
   const context=instrumentAt>=0?all.slice(instrumentAt,instrumentAt+650):all.slice(0,3500);
   const currency=context.match(/\b(?:USD|CAD|AUD|EUR|GBP|ZMW|JPY)\b/i)?.[0]?.toUpperCase()||
     (/^(?:USD|CAD|AUD|EUR|GBP|ZMW)\s/i.test(m[2])?m[2].trim().toUpperCase():null);
   const visible=(m[2].trim()+m[3]).replace(/\s+/g,'');
   if(!currency||!context.replace(/\s+/g,'').includes(visible)&&!context.includes(m[3]))return quotes;
   quotes.push({instrument,symbol,quote:value,currency,kind:'public_market_price',
     source:'visible_title_url_and_currency',verification:'candidate_only'});
   return quotes;
 }
 function platformDiscovery(opportunities,marketQuotes){
  const links=[...document.querySelectorAll('a[href]')].slice(0,300);
  const affordances={
   navigation:links.length,
   login:loginForm,
   account:accountHeader||signout,
   odds:opportunities.some(x=>x.kind==='bet'),
   prices:opportunities.some(x=>x.kind==='trade'),
   publicMarketPrices:marketQuotes.length,
   editableFields:document.querySelectorAll('input:not([type=hidden]),textarea,select').length,
   interactiveControls:document.querySelectorAll('button,[role=button]').length
  };
  const publicText=(document.title+' '+[...document.querySelectorAll('h1,h2,h3')].slice(0,12).map(el=>el.innerText).join(' ')).slice(0,1200);
  const labelBet=/\b(?:sports\s*betting|online\s*betting|sportsbook|betting\s*odds|sport\s*betting)\b/i.test(publicText);
  const labelTrade=/\b(?:online\s*trading|forex\s*trading|stock\s*broker|share\s*trading|trade\s*stocks)\b/i.test(publicText);
  const category=affordances.odds?'betting':affordances.prices?'trading':
    marketQuotes.length?'market_data':labelBet&&!labelTrade?'betting':
    labelTrade&&!labelBet?'trading':'unclassified';
  const basis=(affordances.odds||affordances.prices)?'visible_market_controls':
    marketQuotes.length?'public_price_evidence':
    category==='unclassified'?'unclassified':'visible_site_heading';
  return {hostname:location.hostname,title:document.title.slice(0,160),
   category,classificationBasis:basis,affordances,identifiedBy:'visible_dom',
   verification:'candidate_only'};
 }
 const opportunities=opportunityCandidates();
 const marketQuotes=publicMarketQuotes();
 return {url:location.href,title:document.title,visibleText:all.slice(0,12000),elementCount:document.querySelectorAll('*').length,
  auth,authEvidence:{loginFormVisible:loginForm,logoutControlVisible:signout,signInControlVisible:signin,accountHeaderVisible:accountHeader},
  candidates:{balance:candidate('balance'),pending:candidate('pending'),pnl:candidate('pnl')},identity:identityCandidate(),opportunities,marketQuotes,platformDiscovery:platformDiscovery(opportunities,marketQuotes),observedAt:new Date().toISOString(),
  provenance:'browser visible DOM; heuristic candidates not independently verified'};
})()
