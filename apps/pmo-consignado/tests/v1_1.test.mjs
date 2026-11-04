import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {execFileSync} from 'node:child_process';
import vm from 'node:vm';
const source=await readFile(new URL('../dist/core.js',import.meta.url),'utf8');
const c=await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
const ids=rows=>rows.map(row=>row.id);
function fixture(){
  const d=c.emptyData();
  d.clusters=[{id:'c1',name:'Originação'},{id:'c2',name:'Plataforma'},{id:'c3',name:'Cluster sem squads'},{id:'c4',name:'Expansão sem projetos'}];
  d.squads=[{id:'s1',name:'Jornada digital',clusterId:'c1'},{id:'s2',name:'Integrações',clusterId:'c2'},{id:'s3',name:'Elegibilidade',clusterId:'c1'},{id:'s4',name:'Squad sem projetos',clusterId:'c4'}];
  d.projects=[{id:'p1',name:'Contratação',owner:'Ana',clusterId:'c1',squadId:'s1',start:'2024-01-01',end:'2024-04-01',updated:'2024-03-01',priority:'Alta',status:'Em andamento'},
    {id:'p2',name:'API central',owner:'Bruno',clusterId:'c2',squadId:'s2',start:'2024-01-01',end:'2024-04-01',updated:'2024-03-01',priority:'Média',status:'Pausado'},
    {id:'p3',name:'Motor de regras',owner:'João',clusterId:'c1',squadId:'s3',start:'2024-01-01',end:'2024-04-01',updated:'2024-03-01',priority:'Alta',status:'Planejado'}];
  const milestone=(id,projectId,name,actual,done=true)=>({id,projectId,name,date:'2024-02-28',forecast:'2024-02-28',actual,done});
  d.milestones=[milestone('m1','p1','Contrato aprovado','2024-02-26'),milestone('m2','p2','API disponível','2024-03-03'),milestone('m3','p1','Domingo anterior','2024-02-25'),milestone('m4','p1','Segunda seguinte','2024-03-04'),milestone('m5','p1','Legado sem data',''),milestone('m6','p1','Pendente nesta semana','',false),milestone('m7','p3','Integração de regras','2024-02-29')];
  d.dependencies=[{id:'d1',from:'m1',to:'m2'},{id:'d2',from:'m2',to:'m7'},{id:'d3',from:'m3',to:'m6'}];
  return c.validateData(d);
}
test('V1.1 organization respects cluster/squad/text together and ignores project status',()=>{
  const d=fixture();
  assert.deepEqual(ids(c.filterOrganization(d)),['c1','c2','c3','c4']);
  const rows=c.filterOrganization(d,{clusterId:'c1',squadId:'s3',search:'ELEGIBILIDADE',status:'Concluído'});
  assert.deepEqual(ids(rows),['c1']);assert.deepEqual(ids(rows[0].squads),['s3']);
  assert.equal(c.filterOrganization(d,{clusterId:'c1',squadId:'s2'}).length,0);
  assert.equal(c.filterOrganization(d,{search:'não existe'}).length,0);
});
test('V1.1 organization search includes entities without projects, empty clusters and accent variants',()=>{
  const d=fixture();
  assert.deepEqual(ids(c.filterOrganization(d,{search:'cluster sem squads'})),['c3']);
  assert.deepEqual(ids(c.filterOrganization(d,{squadId:'s4',status:'Em andamento'})),['c4']);
  assert.deepEqual(ids(c.filterOrganization(d,{search:'originacao'})),['c1']);
  assert.deepEqual(ids(c.filterOrganization(d,{search:'INTEGRACOES'})),['c2']);
});
test('V1.1 project filters combine status, organization and normalized query',()=>{
  const d=fixture();
  assert.deepEqual(ids(c.filterProjects(d,{search:'JOAO',clusterId:'c1',squadId:'s3',status:'Planejado'})),['p3']);
  assert.equal(c.filterProjects(d,{search:'JOAO',status:'Em andamento'}).length,0);
  assert.deepEqual(ids(c.filterProjects(d,{search:'  CONTRATACAO  '})),['p1']);
  assert.equal(c.filterProjects(d,{clusterId:'c1',squadId:'s2'}).length,0);
});
test('V1.1 dependency query matches either endpoint within the selected project scope',()=>{
  const d=fixture();
  assert.deepEqual(ids(c.filterDependencies(d,{projectIds:['p1'],milestoneQuery:'API DISPONIVEL'})),['d1']);
  assert.deepEqual(ids(c.filterDependencies(d,{projectIds:['p3'],milestoneQuery:'api'})),['d2']);
  assert.deepEqual(ids(c.filterDependencies(d,{projectIds:['p1'],milestoneQuery:'integracao'})),[]);
  assert.deepEqual(ids(c.filterDependencies(d,{projectIds:[],milestoneQuery:'api'})),[]);
  assert.equal(c.filterDependencies(d,{projectIds:['p1'],milestoneQuery:'inexistente'}).length,0);
});
test('V1.1 weeks are Monday through Sunday inclusive across leap and year boundaries',()=>{
  assert.deepEqual(c.weekBounds('2024-02-29'),{start:'2024-02-26',end:'2024-03-03'});
  assert.deepEqual(c.weekBounds('2024-03-03'),{start:'2024-02-26',end:'2024-03-03'});
  assert.deepEqual(c.weekBounds('2024-03-04'),{start:'2024-03-04',end:'2024-03-10'});
  assert.deepEqual(c.weekBounds('2025-01-01'),{start:'2024-12-30',end:'2025-01-05'});
  assert.deepEqual(c.weekBounds('1900-01-01'),{start:'1900-01-01',end:'1900-01-07'});
  assert.deepEqual(c.weekBounds('2200-12-31'),{start:'2200-12-29',end:'2201-01-04'});
  assert.throws(()=>c.weekBounds('2025-02-29'));
});
test('V1.1 completed highlights use only actual dates, include endpoints and group by squad/cluster',()=>{
  const d=fixture(),result=c.weeklyDeliveries(d,{reference:'2024-02-29'});
  assert.deepEqual(ids(result.deliveries),['m1','m7','m2']);assert.equal(result.missingActual,1);
  assert.deepEqual(result.groups.map(group=>group.id),['s1','s3','s2']);
  const filtered=c.weeklyDeliveries(d,{reference:'2024-02-29',projectIds:['p1'],groupBy:'cluster'});
  assert.deepEqual(ids(filtered.deliveries),['m1']);assert.deepEqual(filtered.groups.map(group=>group.id),['c1']);
  assert.equal(c.weeklyDeliveries(d,{reference:'2024-02-29',projectIds:[]}).deliveries.length,0);
  assert.equal(c.weeklyDeliveries(d,{reference:'2024-02-29',projectIds:['p2']}).missingActual,0);
});
test('V1.1 weekly boundaries remain local-calendar stable in four timezones around DST',()=>{
  const url='data:text/javascript;base64,'+Buffer.from(source).toString('base64');
  const script=`const c=await import(${JSON.stringify(url)});console.log(JSON.stringify([c.weekBounds('2026-03-08'),c.weekBounds('2026-11-01'),c.weekBounds('2025-01-01')]));`;
  for(const TZ of ['UTC','America/Sao_Paulo','America/New_York','Pacific/Auckland']){
    const out=execFileSync(process.execPath,['--input-type=module','-e',script],{env:{...process.env,TZ},encoding:'utf8'});
    assert.deepEqual(JSON.parse(out),[{start:'2026-03-02',end:'2026-03-08'},{start:'2026-10-26',end:'2026-11-01'},{start:'2024-12-30',end:'2025-01-05'}],TZ);
  }
});
test('V1.1 milestone sorts expose planned/forecast/actual without mutating source',()=>{
  const d=fixture(),before=JSON.stringify(d);
  assert.deepEqual(ids(c.filterMilestones(d,['p1'],'actual')),['m3','m1','m4','m5','m6']);
  assert.equal(c.filterMilestones(d,[],'date').length,0);assert.equal(JSON.stringify(d),before);
});
test('V1 backups retain schema version and legacy missing actual without fabricating highlights',()=>{
  const d=fixture();for(const p of d.projects){delete p.forecast;delete p.reason;}
  for(const m of d.milestones){delete m.actual;delete m.reason;}
  const restored=c.validateData(JSON.parse(JSON.stringify(d)));
  assert.equal(c.VERSION,1);assert.equal(restored.version,1);assert.equal(restored.milestones[0].actual,'');
  assert.equal(c.weeklyDeliveries(restored,{reference:'2024-02-29'}).deliveries.length,0);
  assert.equal(c.weeklyDeliveries(restored,{reference:'2024-02-29'}).missingActual,6);
});

const appSource=(await readFile(new URL('../dist/app.js',import.meta.url),'utf8')).replace(/^import[^\n]*\n/gm,'');
const executiveSource=(await readFile(new URL('../dist/executive.js',import.meta.url),'utf8')).replace(/^import[^\n]*\n/,'').replace(/^export /gm,'');
function boot(data=fixture()){
  const nodes=new Map(),events={},papers=[];
  function node(id){
    if(nodes.has(id))return nodes.get(id);
    let html='';
    const el={id,value:'',textContent:'',hidden:false,disabled:false,style:{},classList:{add(){},remove(){},toggle(){}},listeners:{},addEventListener(type,fn){this.listeners[type]=fn;},setAttribute(){},querySelector(){return node(id+'-child');},showModal(){this.open=true;},close(){this.open=false;},focus(){},setSelectionRange(){}};
    Object.defineProperty(el,'innerHTML',{get:()=>html,set:value=>{html=value;if(['cluster-filter','squad-filter'].includes(id)){const options=[...value.matchAll(/<option value="([^"]*)"([^>]*)>/g)];el.value=(options.find(match=>/selected/.test(match[2]))||options[0]||['',''])[1];}}});
    nodes.set(id,el);return el;
  }
  const context=vm.createContext({...c,structuredClone,console,Map,Set,Date,JSON,Error,Blob,URL,setTimeout:()=>1,clearTimeout(){},confirm:()=>true,window:{print(){}},document:{getElementById:node,querySelectorAll:()=>[],querySelector:()=>null,createElement:()=>({innerHTML:'',className:''}),body:{append:paper=>papers.push(paper)},addEventListener(type,fn){(events[type]||=[]).push(fn);}},localStorage:{getItem(key){assert.equal(key,'orbita-pmo-v1');return JSON.stringify(data);},setItem(){}}});
  vm.runInContext(executiveSource+'\n'+appSource+'\nglobalThis.QA={go,render,selected,week:()=>selectedWeek,timeline:()=>timelineView};',context);
  const change=(id,value)=>{node(id).value=value;for(const fn of events.change||[])fn({target:node(id)});};
  const click=(selector,dataset={})=>{const target={closest:s=>s===selector?{dataset}:null};for(const fn of events.click||[])fn({target});};
  return {context,nodes,papers,node,change,click};
}
test('V1.1 organization ignores and hides status, then restores project status and separate search',()=>{
  const app=boot();app.node('status-filter').value='Pausado';app.node('search').value='API';
  app.context.QA.go('organization');app.node('search').value='originação';app.context.QA.render();
  assert.equal(app.node('status-filter').hidden,true);assert.equal(app.node('status-filter').disabled,true);assert.equal(app.node('status-filter').value,'Pausado');
  assert.deepEqual(JSON.parse(JSON.stringify(app.context.QA.selected())).map(p=>p.id),['p1','p3']);
  app.context.QA.go('projects');assert.equal(app.node('search').value,'API');assert.equal(app.node('status-filter').disabled,false);
  assert.deepEqual(JSON.parse(JSON.stringify(app.context.QA.selected())).map(p=>p.id),['p2']);
  app.context.QA.go('organization');assert.equal(app.node('search').value,'originação');
});
test('V1.1 incompatible squad selection is cleared when the cluster options change',()=>{
  const app=boot();app.node('cluster-filter').value='c1';app.node('squad-filter').value='s2';app.context.QA.render();
  assert.equal(app.node('squad-filter').value,'');
});
test('V1.1 selected week survives navigation and executive report uses same week and filters',()=>{
  const app=boot();app.change('week-picker','2024-02-29');app.node('cluster-filter').value='c1';app.context.QA.go('timeline');app.click('[data-timeline-view]',{timelineView:'weekly'});
  assert.equal(app.context.QA.week(),'2024-02-26');assert.equal(app.context.QA.timeline(),'weekly');
  app.context.QA.go('projects');app.context.QA.go('dashboard');assert.equal(app.context.QA.week(),'2024-02-26');
  app.node('report').onclick();app.node('print-report').onclick();const html=app.papers.at(-1).innerHTML;
  const weekly=html.slice(html.indexOf('<h2>Conquistas da semana'));
  assert.ok(weekly.includes('26/02/2024 a 03/03/2024'));assert.ok(weekly.includes('2 entrega(s) concluída(s)'));
  assert.ok(weekly.includes('Contrato aprovado'));assert.ok(weekly.includes('Integração de regras'));assert.ok(!weekly.includes('API disponível'));assert.ok(!weekly.includes('Domingo anterior'));
});
test('V1.1 week navigation refuses out-of-range moves without corrupting state or render',()=>{
  const app=boot();app.change('week-picker','1900-01-01');assert.doesNotThrow(()=>app.click('[data-week-step]',{weekStep:'-7'}));assert.equal(app.context.QA.week(),'1900-01-01');
  app.change('week-picker','2200-12-31');assert.doesNotThrow(()=>app.click('[data-week-step]',{weekStep:'7'}));assert.equal(app.context.QA.week(),'2200-12-29');
});
