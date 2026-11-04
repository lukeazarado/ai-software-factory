import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import {readFile} from 'node:fs/promises';
const coreSource=await readFile(new URL('../dist/core.js',import.meta.url),'utf8');
const core=await import('data:text/javascript;base64,'+Buffer.from(coreSource).toString('base64'));
const appSource=(await readFile(new URL('../dist/app.js',import.meta.url),'utf8')).replace(/^import[^\n]*\n/,'');

// Only persistence/handlers run here. Browser layout, native dialogs and DOM behavior
// are intentionally outside this fixture; the owner checks them in a real browser.
function boot(raw,options={}){
  const nodes=new Map(),writes=[],papers=[];
  const node=id=>{if(!nodes.has(id))nodes.set(id,{value:'',textContent:'',innerHTML:'',hidden:false,style:{},classList:{add(){},remove(){},toggle(){}},listeners:{},addEventListener(type,fn){this.listeners[type]=fn;},setAttribute(){},querySelector(){return node(id+'-child');},showModal(){this.open=true;},close(){this.open=false;}});return nodes.get(id);};
  const context=vm.createContext({...core,structuredClone,console,Map,Set,Date,JSON,Error,Blob,URL,setTimeout:()=>1,clearTimeout(){},confirm:()=>options.confirm!==false,window:{print(){}},document:{getElementById:node,querySelectorAll:()=>[],querySelector:()=>null,createElement:()=>({innerHTML:'',className:''}),body:{append:paper=>papers.push(paper)},addEventListener(){}},localStorage:{getItem(){if(options.readError)throw Error('blocked');return raw;},setItem(key,value){if(options.writeError)throw Error('quota');writes.push({key,value});raw=value;}}});
  vm.runInContext(appSource+'\nglobalThis.QA={snapshot:()=>JSON.stringify(data),save,blocked:()=>storageBlocked};',context);
  return {context,nodes,writes,papers,snapshot:()=>JSON.parse(context.QA.snapshot()),save:value=>context.QA.save(value),blocked:()=>context.QA.blocked(),raw:()=>raw};
}
test('valid stored data loads without overwriting it on startup',()=>{
  const original=JSON.stringify(core.demoData()),app=boot(original);
  assert.deepEqual(app.snapshot(),JSON.parse(original));assert.equal(app.writes.length,0);
});
test('corrupt and unavailable storage are never overwritten during startup',()=>{
  for(const options of [{},{readError:true}]){
    const app=boot('{invalid-json',options);assert.equal(app.blocked(),true);assert.equal(app.writes.length,0);assert.equal(app.raw(),'{invalid-json');assert.equal(app.snapshot().projects.length,0);
    assert.throws(()=>app.save(core.demoData()),/recuperado/);assert.equal(app.writes.length,0);
  }
});
test('failed storage write preserves existing in-memory and persisted data',()=>{
  const original=JSON.stringify(core.demoData()),app=boot(original,{writeError:true}),before=app.snapshot();
  assert.throws(()=>app.save(core.emptyData()),/Não foi possível salvar/);
  assert.deepEqual(app.snapshot(),before);assert.equal(app.raw(),original);assert.equal(app.writes.length,0);
});
test('invalid import is rejected before confirmation/write and keeps existing state',async()=>{
  const original=JSON.stringify(core.demoData()),app=boot(original),before=app.snapshot();
  const input={files:[{size:10,text:async()=>'{bad'}],value:'file.json'};
  await app.nodes.get('import-file').listeners.change({target:input});
  assert.deepEqual(app.snapshot(),before);assert.equal(app.raw(),original);assert.equal(app.writes.length,0);assert.equal(input.value,'');
  assert.match(app.nodes.get('toast').textContent,/Importação não realizada/);
});
test('valid import requires confirmation and preserves data on cancellation',async()=>{
  const original=JSON.stringify(core.demoData()),app=boot(original,{confirm:false});
  await app.nodes.get('import-file').listeners.change({target:{files:[{size:100,text:async()=>JSON.stringify(core.emptyData())}],value:'backup.json'}});
  assert.equal(app.raw(),original);assert.equal(app.writes.length,0);assert.equal(app.snapshot().projects.length,3);
});
test('valid confirmed import atomically persists the normalized replacement',async()=>{
  const app=boot(JSON.stringify(core.demoData()));
  await app.nodes.get('import-file').listeners.change({target:{files:[{size:100,text:async()=>JSON.stringify(core.emptyData())}],value:'backup.json'}});
  assert.equal(app.writes.length,1);assert.deepEqual(app.snapshot(),core.emptyData());assert.deepEqual(JSON.parse(app.raw()),core.emptyData());
});
test('oversized import is rejected without reading or changing current data',async()=>{
  const original=JSON.stringify(core.demoData()),app=boot(original);let read=false;
  await app.nodes.get('import-file').listeners.change({target:{files:[{size:core.MAX_BACKUP_BYTES+1,text:async()=>{read=true;return '{}';}}],value:'huge.json'}});
  assert.equal(read,false);assert.equal(app.raw(),original);assert.equal(app.writes.length,0);
});
test('a valid exported backup larger than the former 2 MiB limit can be restored',async()=>{
  const data=core.demoData();
  for(let i=3;i<500;i++)data.projects.push({...data.projects[0],id:'project-'+i,notes:'a'.repeat(3000),objective:'b'.repeat(1000)});
  const exported=core.backupJSON(data),size=Buffer.byteLength(exported);
  assert.ok(size>2*1024*1024);assert.ok(size<=core.MAX_BACKUP_BYTES);
  const app=boot(JSON.stringify(core.emptyData()));
  await app.nodes.get('import-file').listeners.change({target:{files:[{size,text:async()=>exported}],value:'large-backup.json'}});
  assert.equal(app.writes.length,1);assert.equal(app.snapshot().projects.length,500);assert.deepEqual(app.snapshot(),core.validateData(data));
});
test('report generation excludes internal notes by default, marks demo and escapes user text',()=>{
  const data=core.demoData();data.projects[0].notes='SECRET_NOTE_456';data.projects[0].name='<img src=x onerror=alert(1)>';
  const app=boot(JSON.stringify(data));app.nodes.get('report').onclick();app.nodes.get('print-report').onclick();
  const html=app.papers.at(-1).innerHTML;
  assert.ok(!html.includes('SECRET_NOTE_456'));assert.ok(html.includes('DADOS FICTÍCIOS DE DEMONSTRAÇÃO'));assert.ok(html.includes('&lt;img src=x onerror=alert(1)&gt;'));assert.ok(!html.includes('<img src=x'));
});
test('explicit include-notes option and project filters are applied to generated report',()=>{
  const data=core.demoData();data.projects[0].notes='INTERNAL_NOTE_OPT_IN';
  const app=boot(JSON.stringify(data));app.nodes.get('search').value=data.projects[0].name;app.nodes.get('report').onclick();app.context.document.getElementById('include-notes').checked=true;app.nodes.get('print-report').onclick();
  const html=app.papers.at(-1).innerHTML;
  assert.ok(html.includes('INTERNAL_NOTE_OPT_IN'));assert.ok(html.includes('<b>1</b>projetos'));assert.ok(!html.includes(data.projects[2].objective));
});
