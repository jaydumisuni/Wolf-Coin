'use strict';
/* Pure DOM-evidence regression for public quote, sign-in and authenticated wallet. */
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'..','wolf_snapshot.js'),'utf8');
function element({text='',label='',dataset={},href='',parent=null}={}){
 return {
  innerText:text,
  textContent:text,
  dataset,parentElement:parent,
  getClientRects:()=>[{}],
  getAttribute:n=>n==='aria-label'?label:n==='href'?href:null,
  closest:()=>null
 };
}
function inspect({url,title,body,buttons=[],inputs=[],headings=[],opportunities=[],accountHeadings=[]}){
 const nodes={
  'input[type=password]':inputs,
  'a,button':buttons,
  'h1,h2,h3':headings.map(text=>element({text})),
  'h1,h2,h3,h4,[role=heading]':accountHeadings,
  'a[href]':buttons.filter(x=>x.href),
  'input:not([type=hidden]),textarea,select':inputs,
  'button,[role=button]':buttons,
  '[data-wolf-opportunity]':opportunities,
  '[data-odds],[data-price],[data-quote],button,[role=button],.odds':buttons,
  '*':buttons.concat(inputs)
 };
 const document={
  title,
  body:{innerText:body},
  querySelectorAll:selector=>nodes[selector]||[]
 };
 const u=new URL(url);
 const location={href:u.href,hostname:u.hostname,pathname:u.pathname};
 return vm.runInNewContext(source,{document,location},{timeout:500});
}
const finance=inspect({
 url:'https://www.google.com/finance/quote/GOOGL:NASDAQ',
 title:'GOOGL $264.91 (▼ 5.07%) Alphabet Inc Class A | Google Finance',
 body:'Finance\nStocks\nSign in\nCreate a portfolio\nGOOGL:NASDAQ\nAlphabet Inc Class A\n$264.91\n-5.07% Today\nNov 25, 11:44 AM · USD',
 buttons:[element({text:'Sign in'}),element({text:'Create a portfolio'})],
 headings:['Alphabet Inc Class A']
});
assert.equal(finance.auth,'unverified');
assert.equal(finance.authEvidence.signInControlVisible,true);
assert.equal(finance.platformDiscovery.category,'market_data');
assert.equal(finance.platformDiscovery.classificationBasis,'public_price_evidence');
assert.equal(finance.opportunities.length,0,'Public quote is not a broker action');
assert.equal(finance.marketQuotes.length,1);
assert.equal(finance.marketQuotes[0].instrument,'GOOGL:NASDAQ');
assert.equal(finance.marketQuotes[0].quote,264.91);
assert.equal(finance.marketQuotes[0].currency,'USD');
const betting=inspect({
 url:'https://www.betpawa.co.zm/',
 title:'Bet Small, Win BIG | Online Sports Betting | betPawa Zambia',
 body:'LOGIN\nJOIN NOW\nSPORTS\nLIVE\nCASINO\nJoin Africa Betting Giant',
 buttons:[element({text:'LOGIN'}),element({text:'JOIN NOW'})],
 headings:['Online Sports Betting']
});
assert.equal(betting.auth,'unverified');
assert.equal(betting.platformDiscovery.category,'betting');
assert.equal(betting.marketQuotes.length,0);
const wallet=inspect({
 url:'http://127.0.0.1:44567/dashboard',
 title:'Fixture Sports Wallet',
 body:'My Account\nLog Out\nBalance\nK750.00\nPending Bets\nK100.00\nNet Profit/Loss\nK60.00\nAccount Holder\nAlex Example',
 buttons:[element({text:'Log Out'})],
 headings:['My Account']
});
assert.equal(wallet.auth,'probable_authenticated');
assert.equal(wallet.candidates.balance.value,750);
assert.equal(wallet.candidates.pending.value,100);
assert.equal(wallet.candidates.pnl.value,60);
assert.equal(wallet.identity.displayName,'Alex Example');
console.log('WOLF_PUBLIC_MARKET_DOM_EVIDENCE_REGRESSION_PASS',JSON.stringify({
 financeAuth:finance.auth,financeQuote:finance.marketQuotes[0].quote,
 bettingCategory:betting.platformDiscovery.category,walletAuth:wallet.auth,
 balance:wallet.candidates.balance.value
}));

const compact=inspect({
 url:'https://wallet.example.invalid/account',title:'Account',
 body:'Sports\nMy Account\nSample Account\nK 3.50\nDeposit\nWithdraw\nMy activity\nStatement\nHelp',
 buttons:[element({text:'Deposit'}),element({text:'Withdraw'}),element({text:'Statement'})]
});
assert.equal(compact.auth,'probable_authenticated');
assert.equal(compact.authEvidence.accountPanelAuthenticated,true);
assert.equal(compact.candidates.balance.value,3.5);
assert.equal(compact.candidates.balance.currency,'ZMW');
const ambiguous=inspect({url:'https://wallet.example.invalid/account',title:'Account',
 body:'My Account\nK3.50\nK7.00\nDeposit\nWithdraw\nStatement'});
assert.equal(ambiguous.candidates.balance,null);
const unauth=inspect({url:'https://wallet.example.invalid/',title:'Public',
 body:'My Account\nK3.50\nDeposit\nWithdraw\nStatement',
 buttons:[element({text:'Sign in'})]});
assert.equal(unauth.auth,'unverified');
assert.equal(unauth.candidates.balance,null);
const arbitrary=inspect({url:'https://wallet.example.invalid/',title:'Public',
 body:'K3.50\nDeposit\nWithdraw\nStatement'});
assert.equal(arbitrary.candidates.balance,null);
const android=fs.readFileSync(path.join(__dirname,'..','..','wolfcoin-android','app','src','main','assets','wolf_snapshot.js'),'utf8');
assert.equal(android,source,'Android and desktop observer source diverged');
console.log('WOLF_COMPACT_WALLET_AND_ANDROID_PARITY_PASS');

const latePanel=element({text:'My Account\nSample Account\nK3.50\nDeposit\nWithdraw\nStatement'});
const late=inspect({url:'https://wallet.example.invalid/',title:'Account',
 body:'Other page text\n'.repeat(5000),
 accountHeadings:[element({text:'My Account',parent:latePanel})]});
assert.equal(late.authEvidence.accountPanelAuthenticated,true);
assert.equal(late.candidates.balance.value,3.5);
console.log('WOLF_LATE_VISIBLE_ACCOUNT_PANEL_PASS');
