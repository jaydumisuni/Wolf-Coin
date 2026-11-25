'use strict';
const {contextBridge,ipcRenderer}=require('electron');
const invoke=(channel,payload)=>ipcRenderer.invoke(channel,payload);
const api={
 version:'0.9.4-dev',contract:'wolf.browser.v1',
 status:()=>invoke('wolf:status'),
 showBrowser:request=>invoke('wolf:show-browser',request),
 hideBrowser:()=>invoke('wolf:hide-browser'),
 browserBounds:rect=>invoke('wolf:bounds',rect),
 back:()=>invoke('wolf:back'),forward:()=>invoke('wolf:forward'),reload:()=>invoke('wolf:reload'),
 snapshot:request=>invoke('wolf:snapshot',request),
 inspectDOM:request=>invoke('wolf:dom',request),
 inspectNetwork:request=>invoke('wolf:network',request),
 screenshot:request=>invoke('wolf:screenshot',request),
 action:request=>invoke('wolf:action',request),
 events:request=>invoke('wolf:events',request),
 clearSession:accountId=>invoke('wolf:clear-session',{accountId}),
 vaultStatus:()=>invoke('wolf:vault-status'),
 vaultList:()=>invoke('wolf:vault-list'),
 vaultSave:entry=>invoke('wolf:vault-save',entry),
 vaultDelete:entry=>invoke('wolf:vault-delete',entry),
 vaultFill:entry=>invoke('wolf:vault-fill',entry),
 downloads:()=>invoke('wolf:downloads'),
 openExternal:url=>invoke('wolf:open-external',{url}),
 onPageState:callback=>{
  if(typeof callback!=='function')throw new TypeError('Callback required');
  const listener=(_event,detail)=>callback(detail);
  ipcRenderer.on('wolf:page-state',listener);
  return ()=>ipcRenderer.removeListener('wolf:page-state',listener);
 }
};
contextBridge.exposeInMainWorld('wolfNative',Object.freeze(api));
contextBridge.exposeInMainWorld('wolfBackend',Object.freeze({
 contract:'wolf.app.bridge.v2',
 status:()=>invoke('wolf:backend-status'),
 request:(operation,payload={})=>invoke('wolf:backend-request',{operation,payload}),
 registerAccount:account=>invoke('wolf:backend-register',account),
 observeAccount:account=>invoke('wolf:backend-observe',account),
 recordSession:(account,state)=>invoke('wolf:backend-session',{account,state}),
 removeAccount:account=>invoke('wolf:backend-remove',account),
 snapshot:()=>invoke('wolf:backend-snapshot'),
 syncAll:accounts=>invoke('wolf:backend-sync-all',{accounts}),
 proposeAction:request=>invoke('wolf:backend-propose',request)
}));
