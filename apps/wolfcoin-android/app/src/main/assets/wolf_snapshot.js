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
  const result=[];
  for(const el of document.querySelectorAll('[data-wolf-opportunity]')){
    if(result.length>=30)break;
    if(!el.getClientRects().length)continue;
    const market=String(el.dataset.wolfMarket||'').trim().slice(0,120);
    const selection=String(el.dataset.wolfSelection||'').trim().slice(0,120);
    const quote=Number(el.dataset.wolfQuote);
    const kind=el.dataset.wolfKind,side=el.dataset.wolfSide,currency=String(el.dataset.wolfCurrency||'').toUpperCase();
    if(!market||!selection||!Number.isFinite(quote)||quote<=0||!['bet','trade'].includes(kind)||
      !['back','buy','sell'].includes(side)||!(/^[A-Z]{3}$/).test(currency))continue;
    result.push({market,selection,kind,side,quote,currency,verification:'candidate_only',source:'visible_dom'});
  }
  return result;
 }
 return {url:location.href,title:document.title,visibleText:all.slice(0,12000),elementCount:document.querySelectorAll('*').length,
  auth,authEvidence:{loginFormVisible:loginForm,logoutControlVisible:signout,accountHeaderVisible:accountHeader},
  candidates:{balance:candidate('balance'),pending:candidate('pending'),pnl:candidate('pnl')},identity:identityCandidate(),opportunities:opportunityCandidates(),observedAt:new Date().toISOString(),
  provenance:'browser visible DOM; heuristic candidates not independently verified'};
})()
