/* Real UI + real Chromium fixture tests for cross-platform portfolio and request continuity. */
import assert from 'node:assert/strict';
const port=Number(process.env.WOLF_TEST_CDP_PORT||13886);
const origin='http://127.0.0.1:'+port;
const sleep=n=>new Promise(r=>setTimeout(r,n));
async function targets(){return(await(await fetch(origin+'/json')).json()).filter(x=>x.type==='page')}
async function connect(t){
 let id=0;const pending=new Map(),ws=new WebSocket(t.webSocketDebuggerUrl);
 await new Promise((resolve,reject)=>{ws.onopen=resolve;ws.onerror=reject});
 ws.onmessage=e=>{const m=JSON.parse(e.data);if(m.id&&pending.has(m.id)){
   const x=pending.get(m.id);pending.delete(m.id);m.error?x.reject(new Error(m.error.message)):x.resolve(m.result);
 }};
 return {eval:async expression=>{const r=await new Promise((resolve,reject)=>{
   const n=++id;pending.set(n,{resolve,reject});
   ws.send(JSON.stringify({id:n,method:'Runtime.evaluate',params:{expression,returnByValue:true,awaitPromise:true}}));
 });if(r.exceptionDetails)throw new Error(JSON.stringify(r.exceptionDetails));return r.result?.value;},close:()=>ws.close()};
}
async function until(f,attempts=35){
 for(let i=0;i<attempts;i++){const result=await f();if(result)return result;await sleep(150)}
 throw new Error('Timeout waiting for browser/UI state');
}
const ui=await connect((await until(async()=>((await targets()).find(t=>t.url.startsWith('file:'))))) );
const result={};
async function addAndSync(url,name){
 await ui.eval("(()=>{document.querySelector('[data-tab=platforms]').click();document.querySelector('[data-action=add-account]').click();const f=document.querySelector('#account-form');if(!f)throw Error('Add form not present');f.querySelector('[name=name]').value="+JSON.stringify(name)+";f.querySelector('[name=url]').value="+JSON.stringify(url)+";f.querySelector('[name=type]').value='Betting';f.requestSubmit();return true})()");
 const now=JSON.parse(await ui.eval("JSON.stringify({tab:state.tab,accounts:state.accounts.map(a=>({id:a.id,name:a.name}))})"));
 assert.equal(now.tab,'browser');
 const account=now.accounts.find(a=>a.name===name);assert(account);
 const site=await until(async()=>(await targets()).find(t=>t.url===url));
 const page=await connect(site);
 await until(async()=>{try{return await page.eval("!!document.querySelector('[name=user]')")}catch{return false}});
 try{await page.eval("(()=>{document.querySelector('[name=user]').value='fixture';document.querySelector('[name=pass]').value='fixture';document.querySelector('form').requestSubmit();return true})()");}
 finally{page.close()}
 await sleep(350);
 await ui.eval("document.querySelector('[data-action=sync-current]').click()");
 const proof=await until(async()=>{
   const data=JSON.parse(await ui.eval("JSON.stringify(state.accounts)"));
   const a=data.find(x=>x.id===account.id);
   return a?.status==='connected'&&a.ownerEvidence?.displayName==='Alex Example'?a:null;
 });
 assert.equal(proof.balance,750);
 assert.equal(proof.ownerEvidence.label.toLowerCase(),'account holder');
 return {id:account.id,name,opportunities:JSON.parse(await ui.eval("JSON.stringify(state.portfolio?.observations||[])")).length};
}
try{
 await until(async()=>await ui.eval("window.WOLF_DXQT?.status==='ready'&&!!window.WolfPortfolio"));
 const initial=JSON.parse(await ui.eval("JSON.stringify({accounts:state.accounts.length,demo:state.demoMode})"));
 assert.equal(initial.accounts,0);assert.equal(initial.demo,false);
 result.first=await addAndSync('http://127.0.0.1:44567/login','Fixture Sports A');
 result.second=await addAndSync('http://127.0.0.1:44568/login','Fixture Sports B');
 await ui.eval("document.querySelector('[data-tab=accounts]').click()");
 const before=JSON.parse(await ui.eval("JSON.stringify({matches:window.WolfPortfolio.snapshot().matches,groups:state.portfolio.groups})"));
 assert.equal(before.matches.length,1,'Auto match should discover common owner');
 assert.equal(before.groups.length,0,'Auto match must not silently assert legal ownership');
 await ui.eval("document.querySelector('[data-pf=link]').click()");
 const grouped=JSON.parse(await ui.eval("JSON.stringify({groups:state.portfolio.groups,matches:window.WolfPortfolio.snapshot().matches})"));
 assert.equal(grouped.groups.length,1);
 assert.equal(grouped.groups[0].accountIds.length,2);
 assert.equal(grouped.matches.length,0);
 result.pair={autoMatches:before.matches.length,ownerConfirmed:true,linkedAccounts:grouped.groups[0].accountIds.length};
 await ui.eval("document.querySelector('[data-tab=finance]').click()");
 const comparisons=JSON.parse(await ui.eval("JSON.stringify(window.WolfPortfolio.snapshot().comparisons)"));
 assert.equal(comparisons.length,1,'Pair should compare both quotes');
 assert.equal(comparisons[0].best.quote,2.3);
 await ui.eval("document.querySelector('[data-pf=propose]').click()");
 const proposals=JSON.parse(await ui.eval("JSON.stringify(state.portfolio.proposals)"));
 assert.equal(proposals.length,1);
 assert.equal(proposals[0].status,'pending_backend');
 assert.equal(proposals[0].source.verification,'candidate_only');
 assert(proposals[0].idempotencyKey);
 result.compare={bestQuote:comparisons[0].best.quote,alternatives:comparisons[0].alternatives.length,queuedRequests:proposals.length};
 // Reload the actual app UI from the same isolated profile. Owner pairing and requests must persist.
 await ui.eval("location.reload()");
 await sleep(700);
 const persisted=await until(async()=>{
   try{return JSON.parse(await ui.eval("JSON.stringify({accounts:state.accounts.length,groups:state.portfolio?.groups?.length,requests:state.portfolio?.proposals?.length,ready:window.WOLF_DXQT?.status})"))}
   catch{return null}
 });
 assert.equal(persisted.accounts,2);
 assert.equal(persisted.groups,1);
 assert.equal(persisted.requests,1);
 assert.equal(persisted.ready,'ready');
 result.persistence=persisted;
 console.log('WOLF_NATIVE_PORTFOLIO_E2E_PASS '+JSON.stringify(result));
}finally{ui.close()}
