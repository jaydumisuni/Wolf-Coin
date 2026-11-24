'use strict';
const {contextBridge,ipcRenderer}=require('electron');
const invoke=(channel,payload)=>ipcRenderer.invoke(channel,payload);
const api={
 version:'0.7.2-dev',contract:'wolf.browser.v1',
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
 openExternal:url=>invoke('wolf:open-external',{url}),
 onPageState:callback=>{
  if(typeof callback!=='function')throw new TypeError('Callback required');
  const listener=(_event,detail)=>callback(detail);
  ipcRenderer.on('wolf:page-state',listener);
  return ()=>ipcRenderer.removeListener('wolf:page-state',listener);
 }
};
contextBridge.exposeInMainWorld('wolfNative',Object.freeze(api));
