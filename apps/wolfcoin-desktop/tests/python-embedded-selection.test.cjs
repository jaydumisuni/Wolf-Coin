'use strict';
const fs=require('node:fs');
const os=require('node:os');
const path=require('node:path');
const assert=require('node:assert/strict');
const {pythonForHost,backendModuleDirectory}=require('../backend_host.cjs');
const root=fs.mkdtempSync(path.join(os.tmpdir(),'wolf-host-select-'));
try{
 const moduleDir=path.join(root,'resources','app');
 const runtime=path.join(root,'resources','python','python.exe');
 fs.mkdirSync(moduleDir,{recursive:true});
 fs.mkdirSync(path.dirname(runtime),{recursive:true});
 assert.equal(pythonForHost('linux',moduleDir),'python3');
 assert.equal(pythonForHost('win32',moduleDir),'python');
 fs.writeFileSync(runtime,'official-python-executable-test-placeholder');
 assert.equal(pythonForHost('win32',moduleDir),runtime);
 const loose=path.join(moduleDir,'backend-runtime','wolf_app','bridge.py');
 fs.mkdirSync(path.dirname(loose),{recursive:true});
 fs.writeFileSync(loose,'example');
 assert.equal(backendModuleDirectory(path.join(root,'resources'),moduleDir),path.dirname(path.dirname(loose)));
 const unpacked=path.join(root,'resources','app.asar.unpacked','backend-runtime','wolf_app','bridge.py');
 fs.mkdirSync(path.dirname(unpacked),{recursive:true});
 fs.writeFileSync(unpacked,'example');
 assert.equal(backendModuleDirectory(path.join(root,'resources'),moduleDir),path.dirname(path.dirname(unpacked)));
 console.log('WOLF_EMBEDDED_PYTHON_HOST_SELECTION_PASS');
}finally{fs.rmSync(root,{force:true,recursive:true})}
