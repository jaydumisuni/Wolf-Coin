'use strict';
const http=require('node:http');
const owner=String(process.env.WOLF_FIXTURE_OWNER||'Alex Example').replace(/[<>&"]/g,'').slice(0,60);
const quote=Number(process.env.WOLF_FIXTURE_ODDS||'2.1');
const port=Number(process.env.WOLF_FIXTURE_PORT||'0');
if(!Number.isFinite(quote)||quote<=1||quote>100)throw Error('Invalid fixture quote');

const server=http.createServer((req,res)=>{
 const cookies=req.headers.cookie||'';
 if(req.url==='/login'&&cookies.includes('wolf_fixture=ok')){res.writeHead(302,{location:'/dashboard'});res.end();return;}
 if(req.url==='/login'){
  res.writeHead(200,{'content-type':'text/html; charset=utf-8'});
  res.end(`<!doctype html><title>Fixture Login</title><h1>Sign in</h1><form method="POST" action="/signin"><label>User<input name="user" required></label><label>Password<input type="password" name="pass" required></label><button type="submit">Log in</button></form>`);return;
 }
 if(req.url==='/signin'&&req.method==='POST'){
  req.resume();req.on('end',()=>{res.writeHead(302,{'set-cookie':'wolf_fixture=ok; Max-Age=7200; HttpOnly; SameSite=Lax; Path=/','location':'/dashboard'});res.end()});return;
 }
 if(req.url==='/market'){
  res.writeHead(200,{'content-type':'text/html; charset=utf-8'});
  res.end('<!doctype html><title>Public Match Odds</title><h1>Public Markets</h1>'+
    '<div class="market" data-market="Fixture Match 2026-12-01" data-currency="ZMW"><h2 class="market-title">Fixture Match 2026-12-01</h2>'+
    '<button data-odds="2.10" data-selection="Home">Home 2.10</button>'+
    '<button data-odds="3.15" data-selection="Draw">Draw 3.15</button></div>');
  return;
 }
 if(req.url==='/control'){
  res.writeHead(200,{'content-type':'text/html; charset=utf-8'});
  res.end("<!doctype html><title>Controlled Browser Actions</title><h1>Test controls</h1><input id=\"test-password\" type=\"password\" autocomplete=\"off\"><input id=\"test-number\" type=\"number\"><button id=\"place-bet\" type=\"button\" onclick=\"this.dataset.activated=&#39;yes&#39;\">Place Bet</button><button id=\"withdraw\" type=\"button\" onclick=\"this.dataset.activated=&#39;yes&#39;\">Withdraw</button><form method=\"POST\" action=\"/ack\"><button id=\"confirm-payment\" type=\"submit\">Confirm Payment</button></form>");return;
 }
 if(req.url==='/ack'&&req.method==='POST'){
  req.resume();req.on('end',()=>{res.writeHead(200,{'content-type':'text/html; charset=utf-8'});res.end('<!doctype html><title>Controlled Acknowledgement</title><h1>Fixture submitted</h1>')});return;
 }
 if(req.url==='/compact-wallet'){
  if(!cookies.includes('wolf_fixture=ok')){res.writeHead(302,{location:'/login'});res.end();return;}
  res.writeHead(200,{'content-type':'text/html; charset=utf-8'});
  res.end('<!doctype html><title>Controlled Account Wallet</title><section><h2>My Account</h2><div>Sample Account</div><div>K 3.50</div><button>Deposit</button><button>Withdraw</button><button>Statement</button></section>');return;
 }
 if(req.url==='/dashboard'){
  if(!cookies.includes('wolf_fixture=ok')){res.writeHead(302,{location:'/login'});res.end();return;}
  res.writeHead(200,{'content-type':'text/html; charset=utf-8'});
  res.end(`<!doctype html><title>Fixture Sports Wallet</title><h1>My Account</h1><button onclick="location.href='/logout'">Log Out</button><section>Balance<br>K750.00</section><section>Pending Bets<br>K100.00</section><section>Net Profit/Loss<br>K60.00</section><section>Account Holder<br>${owner}</section><section data-wolf-opportunity data-wolf-market="Fixture Match 2026-12-01" data-wolf-selection="Home" data-wolf-kind="bet" data-wolf-side="back" data-wolf-quote="${quote}" data-wolf-currency="ZMW">Home odds: ${quote}</section>`);return;
 }
 if(req.url==='/logout'){res.writeHead(302,{'set-cookie':'wolf_fixture=; Max-Age=0; HttpOnly; SameSite=Lax; Path=/','location':'/login'});res.end();return;}
 res.writeHead(404);res.end('Not Found');
});
server.listen(port,'127.0.0.1',()=>{console.log('WOLF_FIXTURE_URL=http://127.0.0.1:'+server.address().port+'/login');});
