import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {execFileSync} from 'node:child_process';
const src=await readFile(new URL('../dist/core.js',import.meta.url),'utf8');
const core=await import('data:text/javascript;base64,'+Buffer.from(src).toString('base64'));
const {isDate,days,shift,hasCycle,validateData,emptyData,demoData,impacts,health,projectsCSV,csvCell}=core;
const fresh=()=>JSON.parse(JSON.stringify(demoData()));

test('real calendar dates, leap years, supported bounds and strict format',()=>{
  for(const date of ['2024-02-29','1900-01-01','2200-12-31','2026-11-04']) assert.equal(isDate(date),true,date);
  for(const date of ['2025-02-29','2026-02-30','2026-13-01','2026-1-04','2026-11-04T00:00:00Z','1899-12-31','2201-01-01','',null,42]) assert.equal(isDate(date),false,String(date));
});
test('day arithmetic crosses month/year boundaries without drift',()=>{
  assert.equal(shift('2024-02-28',1),'2024-02-29');
  assert.equal(shift('2024-02-29',1),'2024-03-01');
  assert.equal(shift('2026-12-31',1),'2027-01-01');
  assert.equal(shift('2026-01-01',-1),'2025-12-31');
  assert.equal(days('2024-02-28','2024-03-01'),2);
  assert.equal(days('2024-03-01','2024-02-28'),-2);
});
test('calendar arithmetic remains stable across timezones and DST boundaries',()=>{
  const url='data:text/javascript;base64,'+Buffer.from(src).toString('base64');
  const script=`const c=await import(${JSON.stringify(url)}); console.log(JSON.stringify([c.shift('2026-03-07',2),c.shift('2026-10-31',2),c.days('2026-03-07','2026-03-09')]));`;
  for(const TZ of ['UTC','America/Sao_Paulo','America/New_York','Pacific/Auckland']){
    const result=execFileSync(process.execPath,['--input-type=module','-e',script],{env:{...process.env,TZ},encoding:'utf8'});
    assert.deepEqual(JSON.parse(result),['2026-03-09','2026-11-02',2],TZ);
  }
});
test('DAG handles isolated branches, self-cycle and transitive cycles',()=>{
  assert.equal(hasCycle([]),false);
  assert.equal(hasCycle([{from:'a',to:'b'},{from:'a',to:'c'},{from:'b',to:'d'},{from:'c',to:'d'}]),false);
  assert.equal(hasCycle([{from:'a',to:'a'}]),true);
  assert.equal(hasCycle([{from:'a',to:'b'},{from:'b',to:'a'}]),true);
  assert.equal(hasCycle([{from:'a',to:'b'},{from:'b',to:'c'},{from:'c',to:'a'}]),true);
});
test('empty and demo backup round-trip and normalization drop unknown fields',()=>{
  assert.deepEqual(validateData(emptyData()),emptyData());
  const data=fresh();data.projects[0].unknown='<script>alert(1)</script>';
  const validated=validateData(data);
  assert.equal('unknown' in validated.projects[0],false);
  assert.deepEqual(validateData(JSON.parse(JSON.stringify(validated))),validated);
});
test('reject malformed schema and duplicate identifiers without mutating input',()=>{
  for(const value of [null,[],{}, {...emptyData(),version:2},{...emptyData(),projects:{}},{...emptyData(),clusters:Array(1001).fill({id:'a',name:'A'})}]) assert.throws(()=>validateData(value));
  const data=fresh();data.squads[0].id=data.clusters[0].id;
  const before=JSON.stringify(data);assert.throws(()=>validateData(data),/duplicado/);assert.equal(JSON.stringify(data),before);
});
test('reject dangling references and cluster/squad mismatches',()=>{
  const changes=[d=>d.squads[0].clusterId='missing',d=>d.projects[0].squadId='missing',d=>d.projects[0].clusterId='c2',d=>d.milestones[0].projectId='missing',d=>d.dependencies[0].to='missing'];
  for(const change of changes){const data=fresh();change(data);assert.throws(()=>validateData(data));}
});
test('reject invalid dates, project range, status, priority and nonboolean completion',()=>{
  const changes=[d=>d.projects[0].start='2026-02-30',d=>d.projects[0].start='2200-01-01',d=>d.projects[0].status='whatever',d=>d.projects[0].priority='Critical',d=>d.milestones[0].done='false',d=>d.milestones[0].forecast='invalid'];
  for(const change of changes){const data=fresh();change(data);assert.throws(()=>validateData(data));}
});
test('reject duplicate edges, self-dependency and imported cycle',()=>{
  const changes=[d=>d.dependencies.push({...d.dependencies[0],id:'d99'}),d=>d.dependencies[0].to=d.dependencies[0].from,d=>d.dependencies.push({id:'d99',from:'m3',to:'m1'})];
  for(const change of changes){const data=fresh();change(data);assert.throws(()=>validateData(data));}
});
test('impacts find all downstream deliveries once and no unrelated nodes',()=>{
  const d=fresh();assert.deepEqual(new Set(impacts(d,'m1')),new Set(['m2','m3','m4']));assert.deepEqual(impacts(d,'m5'),[]);
});
test('risk propagation stops at completed deliveries while structural reach remains visible',()=>{
  const d=fresh(),p=d.projects.find(p=>p.id==='p3');
  const future=shift(core.today(),30);p.end=future;p.forecast=future;
  d.milestones.find(m=>m.id==='m4').forecast=future;d.milestones.find(m=>m.id==='m4').date=future;
  assert.equal(health(d,p).label,'Em atenção','Pending upstream delivery risk propagates');
  d.milestones.find(m=>m.id==='m3').done=true;
  assert.equal(health(d,p).label,'No prazo','Completed intermediate delivery breaks operational impact');
  assert.ok(impacts(d,'m1').includes('m4'),'Structural map retains original link');
  assert.ok(!impacts(d,'m1',{pendingOnly:true}).includes('m4'));
});
test('project forecast and milestone actual dates survive validated roundtrip',()=>{
  const d=fresh();d.projects[0].forecast=shift(d.projects[0].end,3);d.projects[0].reason='Ajuste de fornecedor';
  const done=d.milestones.find(m=>m.done);done.actual=shift(core.today(),-1);
  const v=validateData(d);assert.equal(v.projects[0].forecast,d.projects[0].forecast);assert.equal(v.projects[0].reason,d.projects[0].reason);assert.equal(v.milestones.find(m=>m.id===done.id).actual,done.actual);
  done.actual=shift(core.today(),1);assert.throws(()=>validateData(d),/Conclusão real/);
  done.actual='2026-02-30';assert.throws(()=>validateData(d),/Conclusão real/);
});
test('health prioritizes completed, overdue and direct dependency risks',()=>{
  const d=fresh(),p=d.projects[0],now='2026-11-04';
  d.milestones=[];d.dependencies=[];p.start='2026-11-01';p.end='2026-12-01';p.forecast=p.end;p.status='Em andamento';
  assert.notEqual(health(d,p,now).label,'No prazo','Ausência de marcos não comprova saúde');
  p.end='2026-11-03';p.forecast=p.end;assert.equal(health(d,p,now).label,'Atrasado');
  p.status='Concluído';assert.equal(health(d,p,now).label,'Concluído');
  p.status='Pausado';p.end='2026-12-01';p.forecast=p.end;assert.equal(health(d,p,now).label,'Em atenção');
  p.status='Em andamento';
  d.milestones=[{id:'a',projectId:'p2',date:'2026-11-09',forecast:'2026-11-09',done:false},{id:'b',projectId:p.id,date:'2026-11-08',forecast:'2026-11-08',done:false}];d.dependencies=[{id:'e',from:'a',to:'b'}];
  assert.equal(health(d,p,now).label,'Em atenção');
  d.milestones[0].done=true;assert.equal(health(d,p,now).label,'No prazo');
  d.milestones[1].forecast='2026-11-03';assert.equal(health(d,p,now).label,'Atrasado');
});
test('CSV guards formula prefixes and quotes, and excludes internal notes',()=>{
  for(const value of ['=HYPERLINK("x")','+1','-1','@SUM(1)','  =1','\t=1','\r=1']) assert.ok(csvCell(value).startsWith('"\''),JSON.stringify(value));
  assert.equal(csvCell('a"b'),'"a""b"');
  const data=fresh();data.projects[0].notes='SECRET_NOTE_987';data.projects[0].name='=1+1';
  const csv=projectsCSV(data,[data.projects[0]]);
  assert.ok(csv.startsWith('\uFEFF'));assert.ok(csv.includes('"\'=1+1"'));assert.ok(!csv.includes('SECRET_NOTE_987'));assert.equal(csv.split('\r\n').length,2);
});
