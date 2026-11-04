export const VERSION=1;
export const MAX_BACKUP_BYTES=32*1024*1024;
export function backupJSON(data){const text=JSON.stringify(validateData(data),null,2);if(new TextEncoder().encode(text).byteLength>MAX_BACKUP_BYTES)throw Error('O portfólio excede o limite de backup de 32 MiB.');return text;}
export function today(){const d=new Date();return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;}
export function shift(date,days){const d=new Date(date+'T12:00:00');d.setDate(d.getDate()+days);return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;}
export function days(a,b){return Math.round((new Date(b+'T12:00:00Z')-new Date(a+'T12:00:00Z'))/86400000);}
export function isDate(v){return typeof v==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(v)&&!isNaN(new Date(v+'T12:00:00Z'))&&new Date(v+'T12:00:00Z').toISOString().slice(0,10)===v&&v>='1900-01-01'&&v<='2200-12-31';}
export function uid(){return globalThis.crypto?.randomUUID?.()||Date.now().toString(36)+Math.random().toString(36).slice(2);}
export function emptyData(){return {version:VERSION,demo:false,clusters:[],squads:[],projects:[],milestones:[],dependencies:[],issues:[],decisions:[]};}
export function hasCycle(edges){const graph=new Map();for(const e of edges){if(!graph.has(e.from))graph.set(e.from,[]);graph.get(e.from).push(e.to);}const visiting=new Set(),done=new Set();function visit(id){if(visiting.has(id))return true;if(done.has(id))return false;visiting.add(id);for(const next of graph.get(id)||[])if(visit(next))return true;visiting.delete(id);done.add(id);return false;}return [...graph.keys()].some(visit);}
export function validateData(value){
if(!value||typeof value!=='object'||Array.isArray(value)||value.version!==VERSION)throw Error('Formato ou versão de backup incompatível.');
const out=emptyData();out.demo=value.demo===true;const ids=new Set();
for(const kind of ['clusters','squads','projects','milestones','dependencies']){if(!Array.isArray(value[kind])||value[kind].length>1000)throw Error('Lista inválida ou com mais de 1.000 registros: '+kind);out[kind]=value[kind].map(x=>{if(!x||typeof x!=='object'||Array.isArray(x))throw Error('Registro inválido.');const text=(key,max=200,optional=false)=>{const v=x[key];if(optional&&(v==null||v===''))return '';if(typeof v!=='string'||!v.trim()||v.length>max)throw Error('Campo inválido: '+key);return v.trim();};const id=text('id',100);if(ids.has(id))throw Error('Identificador duplicado.');ids.add(id);if(kind==='dependencies')return {id,from:text('from',100),to:text('to',100)};const r={id,name:text('name')};if(kind==='squads')r.clusterId=text('clusterId',100);if(kind==='projects'){Object.assign(r,{owner:text('owner'),clusterId:text('clusterId',100),squadId:text('squadId',100),objective:text('objective',1000,true),notes:text('notes',3000,true)});for(const key of ['start','end','updated']){if(!isDate(x[key]))throw Error('Data inválida: '+key);r[key]=x[key];}if(r.start>r.end)throw Error('O fim do projeto deve ser posterior ao início.');if(!['Alta','Média','Baixa'].includes(x.priority)||!['Planejado','Em andamento','Concluído','Pausado'].includes(x.status))throw Error('Situação ou prioridade inválida.');r.priority=x.priority;r.status=x.status;r.forecast=x.forecast||r.end;if(!isDate(r.forecast)||r.forecast<r.start)throw Error('Previsão final inválida.');r.reason=text('reason',1000,true);}
if(kind==='milestones'){r.projectId=text('projectId',100);for(const key of ['date','forecast']){if(!isDate(x[key]))throw Error('Data de marco inválida.');r[key]=x[key];}if(typeof x.done!=='boolean')throw Error('Conclusão de marco inválida.');r.done=x.done;r.actual=x.actual||'';if(r.actual&&(!isDate(r.actual)||r.actual>today()||!r.done))throw Error('Conclusão real inválida.');r.reason=text('reason',1000,true);}return r;});}
for (const kind of ['issues', 'decisions']) {
  const rows = value[kind] ?? [];
  if (!Array.isArray(rows) || rows.length > 1000) throw Error('Lista inválida ou com mais de 1.000 registros: ' + kind);
  out[kind] = rows.map(x => {
    if (!x || typeof x !== 'object' || Array.isArray(x)) throw Error('Registro inválido: ' + kind);
    const text = (key, max = 500, optional = false) => {
      const v = x[key];
      if (optional && (v == null || v === '')) return '';
      if (typeof v !== 'string' || !v.trim() || v.length > max) throw Error('Campo inválido: ' + key);
      return v.trim();
    };
    const id = text('id', 100);
    if (ids.has(id)) throw Error('Identificador duplicado.');
    ids.add(id);
    const projectId = text('projectId', 100, true);
    if (projectId && !value.projects.some(project => project.id === projectId)) throw Error('Registro executivo sem projeto válido.');
    if (kind === 'issues') {
      if (!['risk', 'blocker'].includes(x.kind)) throw Error('Tipo de risco ou impedimento inválido.');
      if (!['Baixo', 'Médio', 'Alto', 'Crítico'].includes(x.impact)) throw Error('Impacto inválido.');
      if (x.kind === 'risk' && !['Baixa', 'Média', 'Alta'].includes(x.probability)) throw Error('Probabilidade inválida.');
      if (!['Aberto', 'Resolvido'].includes(x.status)) throw Error('Situação inválida.');
      if (!isDate(x.due)) throw Error('Prazo de resposta inválido.');
      return { id, projectId, kind: x.kind, title: text('title'), impact: x.impact,
        probability: x.kind === 'risk' ? x.probability : '', owner: text('owner'), due: x.due,
        action: text('action', 2000), status: x.status };
    }
    if (!['Pendente', 'Decidida'].includes(x.status)) throw Error('Situação da decisão inválida.');
    if (!isDate(x.due)) throw Error('Data necessária da decisão inválida.');
    return { id, projectId, question: text('question'), options: text('options', 1000),
      recommendation: text('recommendation', 1000), owner: text('owner'), due: x.due,
      status: x.status, outcome: text('outcome', 1000, true) };
  });
}
const clusters=new Set(out.clusters.map(x=>x.id)),squads=new Map(out.squads.map(x=>[x.id,x])),projects=new Map(out.projects.map(x=>[x.id,x])),milestones=new Map(out.milestones.map(x=>[x.id,x]));
for(const s of out.squads)if(!clusters.has(s.clusterId))throw Error('Squad sem cluster válido.');
for(const p of out.projects)if(!clusters.has(p.clusterId)||!squads.has(p.squadId)||squads.get(p.squadId).clusterId!==p.clusterId)throw Error('Projeto com cluster/squad incompatível.');
for(const m of out.milestones)if(!projects.has(m.projectId))throw Error('Marco sem projeto válido.');
const pairs=new Set();for(const d of out.dependencies){if(!milestones.has(d.from)||!milestones.has(d.to)||d.from===d.to)throw Error('Dependência inválida.');const key=d.from+'>'+d.to;if(pairs.has(key))throw Error('Dependência duplicada.');pairs.add(key);}
if(hasCycle(out.dependencies))throw Error('Dependências circulares não são permitidas.');return out;
}
export function milestoneDate(m){return m.forecast||m.date;}
export function health(data,p,now=today()){
if(p.status==='Concluído')return {label:'Concluído',tone:'neutral'};
const ms=data.milestones.filter(m=>m.projectId===p.id&&!m.done);
if((p.forecast||p.end)<now||ms.some(m=>milestoneDate(m)<now))return {label:'Atrasado',tone:'danger'};
const impacted=data.dependencies.some(d=>{const target=data.milestones.find(m=>m.id===d.to),source=data.milestones.find(m=>m.id===d.from);if(!target||!source||target.done||source.done)return false;const risk=milestoneDate(source)>milestoneDate(target)||milestoneDate(source)<now;return risk&&(target.projectId===p.id||impacts(data,target.id,{pendingOnly:true}).some(id=>data.milestones.find(m=>m.id===id)?.projectId===p.id&&!data.milestones.find(m=>m.id===id)?.done));});
if(impacted||ms.some(m=>m.forecast>m.date)||(p.forecast||p.end)>p.end||p.status==='Pausado')return {label:'Em atenção',tone:'warning'};
if(!data.milestones.some(m=>m.projectId===p.id))return {label:'Sem marcos',tone:'neutral'};
return {label:'No prazo',tone:'success'};
}
export function impacts(data,sourceId,{pendingOnly=false}={}){const found=new Set(),queue=[sourceId];while(queue.length){const id=queue.shift();for(const e of data.dependencies.filter(e=>e.from===id))if(!found.has(e.to)&&(!pendingOnly||!data.milestones.find(m=>m.id===e.to)?.done)){ found.add(e.to);queue.push(e.to);}}return [...found];}
export function dependencyRisks(data,now=today()){
const risks=[];for(const edge of data.dependencies){const source=data.milestones.find(m=>m.id===edge.from),target=data.milestones.find(m=>m.id===edge.to);if(!source||!target||source.done||target.done)continue;if(milestoneDate(source)>milestoneDate(target)||milestoneDate(source)<now){const affected=[target.id,...impacts(data,target.id,{pendingOnly:true})];risks.push({source:source.id,target:target.id,affected});}}return risks;
}
export function csvCell(v){let s=String(v??'');if(/^[\s]*[=+@-]/.test(s))s="'"+s;return '"'+s.replaceAll('"','""')+'"';}
export function projectsCSV(data,projects=data.projects){const rows=[['Projeto','Cluster','Squad','Responsável','Prioridade','Situação','Início','Fim planejado','Previsão final','Atualização','Objetivo','Origem dos dados'],...projects.map(p=>[p.name,data.clusters.find(c=>c.id===p.clusterId)?.name,data.squads.find(s=>s.id===p.squadId)?.name,p.owner,p.priority,p.status,p.start,p.end,p.forecast||p.end,p.updated,p.objective,data.demo?'DADOS FICTÍCIOS DE DEMONSTRAÇÃO':'Portfólio pessoal'])];return '\uFEFF'+rows.map(r=>r.map(csvCell).join(';')).join('\r\n');}
export function demoData(){const d=today(),data={version:1,demo:true,clusters:[{id:'c1',name:'Originação'},{id:'c2',name:'Plataforma'},{id:'c3',name:'Gestão de carteira'}],squads:[{id:'s1',name:'Jornada digital',clusterId:'c1'},{id:'s2',name:'Integrações',clusterId:'c2'},{id:'s3',name:'Pós-venda',clusterId:'c3'}],projects:[{id:'p1',name:'Nova jornada de contratação',owner:'Ana · exemplo',clusterId:'c1',squadId:'s1',start:shift(d,-14),end:shift(d,35),updated:d,priority:'Alta',status:'Em andamento',objective:'Reduzir o atrito na contratação de consignado.',notes:'Exemplo de anotação interna.'},{id:'p2',name:'Motor de elegibilidade',owner:'Bruno · exemplo',clusterId:'c2',squadId:'s2',start:shift(d,-25),end:shift(d,21),updated:shift(d,-10),priority:'Alta',status:'Em andamento',objective:'Disponibilizar regras unificadas para as jornadas.',notes:''},{id:'p3',name:'Portal de acompanhamento',owner:'Carla · exemplo',clusterId:'c3',squadId:'s3',start:shift(d,4),end:shift(d,49),updated:d,priority:'Média',status:'Planejado',objective:'Dar visibilidade ao andamento dos contratos.',notes:''}],milestones:[{id:'m1',projectId:'p2',name:'API de elegibilidade disponível',date:shift(d,-2),forecast:shift(d,12),done:false},{id:'m2',projectId:'p1',name:'Integração da jornada',date:shift(d,7),forecast:shift(d,7),done:false},{id:'m3',projectId:'p1',name:'Piloto com clientes',date:shift(d,28),forecast:shift(d,28),done:false},{id:'m4',projectId:'p3',name:'Consulta de propostas integrada',date:shift(d,25),forecast:shift(d,25),done:false},{id:'m5',projectId:'p2',name:'Contrato de API aprovado',date:shift(d,-10),forecast:shift(d,-10),actual:weekBounds(d).start,done:true}],dependencies:[{id:'d1',from:'m1',to:'m2'},{id:'d2',from:'m2',to:'m3'},{id:'d3',from:'m3',to:'m4'}]};return validateData(data);}

export function normalizeSearch(value) {
  return String(value ?? '').trim().normalize('NFD').replace(/\p{M}/gu, '').toLocaleLowerCase('pt-BR');
}

// V1.1: filtros puros para manter os mesmos recortes na tela e no relatório.
export function filterProjects(data, filters = {}) {
  const query = normalizeSearch(filters.search);
  return data.projects.filter(project =>
    (!query || normalizeSearch(`${project.name} ${project.owner}`).includes(query)) &&
    (!filters.clusterId || project.clusterId === filters.clusterId) &&
    (!filters.squadId || project.squadId === filters.squadId) &&
    (!filters.status || project.status === filters.status)
  );
}

export function filterOrganization(data, filters = {}) {
  const query = normalizeSearch(filters.search);
  return data.clusters.flatMap(cluster => {
    if (filters.clusterId && cluster.id !== filters.clusterId) return [];
    const clusterMatches = !query || normalizeSearch(cluster.name).includes(query);
    const squads = data.squads.filter(squad => squad.clusterId === cluster.id &&
      (!filters.squadId || squad.id === filters.squadId) &&
      (clusterMatches || normalizeSearch(squad.name).includes(query)));
    if (filters.squadId && !squads.length) return [];
    if (!clusterMatches && !squads.length) return [];
    return [{ ...cluster, squads }];
  });
}

export function filterDependencies(data, { projectIds, milestoneQuery = '' } = {}) {
  const allowed = new Set(projectIds || data.projects.map(project => project.id));
  const query = normalizeSearch(milestoneQuery);
  const milestones = new Map(data.milestones.map(milestone => [milestone.id, milestone]));
  return data.dependencies.filter(edge => {
    const source = milestones.get(edge.from), target = milestones.get(edge.to);
    return source && target && (allowed.has(source.projectId) || allowed.has(target.projectId)) &&
      (!query || normalizeSearch(source.name).includes(query) ||
        normalizeSearch(target.name).includes(query));
  });
}

export function weekBounds(reference = today()) {
  if (!isDate(reference)) throw Error('Selecione uma data válida para a semana.');
  const weekday = new Date(`${reference}T12:00:00Z`).getUTCDay();
  const start = shift(reference, -((weekday + 6) % 7));
  return { start, end: shift(start, 6) };
}

export function weeklyDeliveries(data, { projectIds, reference = today(), groupBy = 'squad' } = {}) {
  const { start, end } = weekBounds(reference);
  const allowed = new Set(projectIds || data.projects.map(project => project.id));
  const projects = new Map(data.projects.map(project => [project.id, project]));
  const completed = data.milestones.filter(milestone => milestone.done && allowed.has(milestone.projectId));
  const deliveries = completed.filter(milestone => isDate(milestone.actual) &&
    milestone.actual >= start && milestone.actual <= end)
    .sort((a, b) => a.actual.localeCompare(b.actual) || a.name.localeCompare(b.name, 'pt-BR'));
  const groups = new Map();
  for (const milestone of deliveries) {
    const project = projects.get(milestone.projectId);
    const key = groupBy === 'cluster' ? project.clusterId : project.squadId;
    const rows = groups.get(key) || [];
    rows.push(milestone);
    groups.set(key, rows);
  }
  return { start, end, deliveries, groups: [...groups].map(([id, milestones]) => ({ id, milestones })),
    missingActual: completed.filter(milestone => !isDate(milestone.actual)).length };
}

export function filterMilestones(data, projectIds, sortBy = 'forecast') {
  const allowed = new Set(projectIds);
  const key = ['date', 'forecast', 'actual'].includes(sortBy) ? sortBy : 'forecast';
  return data.milestones.filter(milestone => allowed.has(milestone.projectId)).sort((a, b) =>
    (a[key] || '9999-12-31').localeCompare(b[key] || '9999-12-31') || a.name.localeCompare(b.name, 'pt-BR'));
}

// V1.2: sinais de agenda baseados apenas nas datas e atribuições cadastradas.
export function squadSignals(data, { projectIds, reference = today(), horizonDays = 30 } = {}) {
  if (!isDate(reference) || !Number.isInteger(horizonDays) || horizonDays < 1 || horizonDays > 365)
    throw Error('Período de análise inválido.');
  const allowed = new Set(projectIds || data.projects.map(project => project.id));
  const horizonEnd = shift(reference, horizonDays);
  return data.squads.map(squad => {
    const projects = data.projects.filter(project => allowed.has(project.id) && project.squadId === squad.id &&
      project.status !== 'Concluído' && project.start <= horizonEnd && (project.forecast || project.end) >= reference);
    const overlaps = [];
    for (let i = 0; i < projects.length; i++) for (let j = i + 1; j < projects.length; j++) {
      if (projects[i].start <= (projects[j].forecast || projects[j].end) &&
          projects[j].start <= (projects[i].forecast || projects[i].end)) overlaps.push([projects[i].id, projects[j].id]);
    }
    const milestones = data.milestones.filter(milestone => allowed.has(milestone.projectId) &&
      projects.some(project => project.id === milestone.projectId) && !milestone.done &&
      milestoneDate(milestone) >= reference && milestoneDate(milestone) <= horizonEnd);
    return { squadId: squad.id, clusterId: squad.clusterId, projects, overlaps, milestones,
      signal: overlaps.length ? 'Sobreposição de períodos' : projects.length > 1 ? 'Janelas distintas' : 'Sem conflito de datas observado' };
  }).filter(item => item.projects.length || item.milestones.length);
}

// Simulação local e descartável: nunca grava nem altera o horizonte oficial.
export function simulateDelay(data, sourceId, scenarioDate, { projectIds } = {}) {
  const source = data.milestones.find(item => item.id === sourceId);
  if (!source || source.done || !isDate(scenarioDate) || scenarioDate < milestoneDate(source))
    throw Error('Selecione um marco pendente e uma data simulada igual ou posterior à previsão atual.');
  const allowed = new Set(projectIds || data.projects.map(project => project.id));
  if (!allowed.has(source.projectId)) throw Error('O marco está fora do recorte atual.');
  const milestones = new Map(data.milestones.map(item => [item.id, item]));
  const projected = new Map([[source.id, scenarioDate]]), queue = [source.id];
  while (queue.length) {
    const from = queue.shift();
    for (const edge of data.dependencies.filter(item => item.from === from)) {
      const target = milestones.get(edge.to);
      if (!target || target.done) continue;
      const date = projected.get(from) > milestoneDate(target) ? projected.get(from) : milestoneDate(target);
      const previous = projected.get(target.id);
      if (previous && previous >= date) continue;
      projected.set(target.id, date); queue.push(target.id);
    }
  }
  const rows = [...projected].filter(([id]) => id !== source.id).flatMap(([id, date]) => {
    const milestone = milestones.get(id), project = data.projects.find(item => item.id === milestone.projectId);
    return allowed.has(milestone.projectId) ? [{ milestone, project, original: milestoneDate(milestone), scenario: date,
      direct: data.dependencies.some(edge => edge.from === source.id && edge.to === id) }] : [];
  }).sort((a, b) => a.scenario.localeCompare(b.scenario));
  return { source, original: milestoneDate(source), scenario: scenarioDate, affected: rows };
}
