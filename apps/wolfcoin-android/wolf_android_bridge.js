// Loaded before all Wolf-Coin app scripts at the trusted appassets origin.
(() => {
  if (!window.WolfHost || window.wolfNative) return;
  let next=0;
  const pending=new Map(), listeners=new Set();
  window.__wolfAndroidPageState = data => {
    for(const fn of listeners){try{fn(data)}catch(e){console.warn('Wolf listener',e)}}
  };
  window.WolfHost.onmessage=event=>{
    let msg;try{msg=JSON.parse(event.data);}catch{return;}
    if(msg.event==='pageState'){
      for(const fn of listeners){try{fn(msg.data)}catch(e){console.warn('Wolf listener',e)}}
      return;
    }
    const req=pending.get(msg.id);if(!req)return;pending.delete(msg.id);
    msg.ok?req.resolve(msg.result):req.reject(new Error(msg.error||'Android host failure'));
  };
  const invoke=(method,args={})=>new Promise((resolve,reject)=>{
    const id=String(++next);
    pending.set(id,{resolve,reject});
    try{window.WolfHost.postMessage(JSON.stringify({id,method,args}));}
    catch(error){pending.delete(id);reject(error)}
  });
  window.wolfNative=Object.freeze({
    version:'0.9.4-dev2',contract:'wolf.browser.v1',
    status:()=>invoke('status'),
    showBrowser:data=>invoke('showBrowser',data),
    hideBrowser:()=>invoke('hideBrowser'),
    browserBounds:data=>invoke('browserBounds',data),
    back:()=>invoke('back'),forward:()=>invoke('forward'),reload:()=>invoke('reload'),
    snapshot:data=>invoke('snapshot',data),
    inspectDOM:data=>invoke('inspectDOM',data),
    inspectNetwork:data=>invoke('inspectNetwork',data),
    action:data=>invoke('action',data),screenshot:data=>invoke('screenshot',data),
    clearSession:accountId=>invoke('clearSession',{accountId}),
    vaultStatus:()=>invoke('vaultStatus'),
    vaultList:()=>invoke('vaultList'),
    vaultSave:entry=>invoke('vaultSave',entry),
    vaultDelete:entry=>invoke('vaultDelete',entry),
    vaultFill:entry=>invoke('vaultFill',entry),
    downloads:()=>invoke('downloads'),
    openExternal:url=>invoke('openExternal',{url}),
    onPageState:callback=>{if(typeof callback!=='function')throw TypeError('callback');listeners.add(callback);return()=>listeners.delete(callback)}
  });
})();
