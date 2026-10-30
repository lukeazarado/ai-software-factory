(()=>{'use strict';
const $=id=>document.getElementById(id);
const DAYS=[{id:0,name:'Domingo'},{id:1,name:'Segunda'},{id:2,name:'Terça'},{id:3,name:'Quarta'},{id:4,name:'Quinta'},{id:5,name:'Sexta'},{id:6,name:'Sábado'}];
const TYPES={training:{label:'Treino',icon:'🏃',cls:'bg-indigo-50 border-indigo-200 text-indigo-800'},game:{label:'Jogo',icon:'⚽',cls:'bg-emerald-50 border-emerald-200 text-emerald-800'},other:{label:'Outro',icon:'📌',cls:'bg-amber-50 border-amber-200 text-amber-800'}};
let events=[],available=[],dragged=null,toastTimer;
let athletes=[],activeAthleteId=null,revisionByAthlete=new Map(),saveQueue=Promise.resolve(true);
let csrfToken=null;
function uid(){return 'item_'+Date.now()+'_'+Math.random().toString(36).slice(2,8)}
function esc(s=''){return String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function dayName(id){return DAYS.find(d=>d.id===Number(id))?.name||'Dia'}
function setSaveStatus(message,kind='ok'){
 const node=document.querySelector('.save-status');if(!node)return;
 node.classList.toggle('is-error',kind==='error');node.classList.toggle('is-saving',kind==='saving');
 const dot=document.createElement('span');node.replaceChildren(dot,document.createTextNode(' '+message));
}
async function api(path,options={}){
 const method=(options.method||'GET').toUpperCase();
 const writeHeaders=method==='GET'?{}:{'X-CSRF-Token':csrfToken||''};
 const response=await fetch(path,{credentials:'same-origin',...options,headers:{'Content-Type':'application/json',...writeHeaders,...(options.headers||{})},cache:'no-store'});
 if(response.status===401){window.location.assign('/login');throw Error('Sessão expirada. Entre novamente com Google.');}
 let data;try{data=await response.json()}catch(_){data={detail:'Resposta inesperada do servidor.'}}
 if(!response.ok)throw new Error(typeof data.detail==='string'?data.detail:`Erro HTTP ${response.status}`);
 return data;
}
// Snapshot serializado, sem gravar eventos no navegador. Falhas ficam visíveis, não silenciosas.
function save(){
 const athleteId=activeAthleteId;
 if(!athleteId){setSaveStatus('Atleta não carregado','error');return Promise.resolve(false)}
 const snapshot={events:events.map(x=>({...x})),available:available.map(x=>({...x}))};
 setSaveStatus('Salvando...','saving');
 saveQueue=saveQueue.then(async()=>{
  try{
   const response=await api(`/api/athletes/${encodeURIComponent(athleteId)}/state`,{
    method:'PUT',body:JSON.stringify({...snapshot,revision:revisionByAthlete.get(athleteId)||0})
   });
   revisionByAthlete.set(athleteId,response.revision);
   if(activeAthleteId===athleteId)setSaveStatus('Salvo no banco');
   return true;
  }catch(error){
   if(activeAthleteId===athleteId){setSaveStatus('Erro ao salvar','error');toast(error.message||'Falha ao salvar no banco.');}
   return false;
  }
 });
 return saveQueue;
}
function refreshAthleteSelector(){
 const select=$('athleteSelect');select.replaceChildren();
 for(const athlete of athletes){const option=document.createElement('option');option.value=athlete.id;option.textContent=athlete.name;select.append(option)}
 select.value=activeAthleteId||'';
}
async function switchAthlete(athleteId){
 if(!athleteId)return false;
 if(!(await saveQueue)){toast('Existem alterações não salvas. Verifique a conexão antes de trocar de atleta.');refreshAthleteSelector();return false}
 const state=await api(`/api/athletes/${encodeURIComponent(athleteId)}/state`);
 activeAthleteId=athleteId;revisionByAthlete.set(athleteId,state.revision);
 events=state.events;available=state.available;
 refreshAthleteSelector();render();setSaveStatus('Salvo no banco');return true;
}
async function initialize(){
 setSaveStatus('Carregando...','saving');
 const auth=await api('/api/auth/me'); csrfToken=auth.csrfToken;
 if(auth.isAdmin){
   const link=document.createElement('a');link.href='/admin';link.className='btn btn-outline';
   link.textContent='Administração';link.title='Parametrizações e obrigações do produto';
   const target=$('logoutBtn');target.parentNode.insertBefore(link,target);
 }
 athletes=await api('/api/athletes');
 if(!athletes.length)throw Error('Nenhum atleta disponível no banco de dados.');
 await switchAthlete(athletes[0].id);
}
$('logoutBtn').addEventListener('click',async()=>{
 try{if(!(await saveQueue))throw Error('Há alterações não salvas.');
  await api('/api/auth/logout',{method:'POST'});window.location.replace('/login');
 }catch(error){toast(error.message||'Erro ao sair');}
});
$('athleteSelect').addEventListener('change',async e=>{
 try{await switchAthlete(e.target.value)}catch(error){refreshAthleteSelector();setSaveStatus('Erro ao carregar','error');toast(error.message)}
});
$('addAthlete').addEventListener('click',async()=>{
 const name=prompt('Nome do novo atleta:');if(name===null)return;
 try{if(!(await saveQueue))throw Error('Salve as alterações pendentes antes de criar um atleta.');
  const athlete=await api('/api/athletes',{method:'POST',body:JSON.stringify({name:name.trim()})});
  athletes=await api('/api/athletes');await switchAthlete(athlete.id);toast('Atleta cadastrado.');
 }catch(error){toast(error.message)}
});
$('renameAthlete').addEventListener('click',async()=>{
 const athlete=athletes.find(x=>x.id===activeAthleteId);if(!athlete)return;
 const name=prompt('Nome do atleta:',athlete.name);if(name===null)return;
 try{await api(`/api/athletes/${encodeURIComponent(athlete.id)}`,{method:'PATCH',body:JSON.stringify({name:name.trim()})});
  athletes=await api('/api/athletes');refreshAthleteSelector();toast('Atleta atualizado.');
 }catch(error){toast(error.message)}
});
$('deleteAthlete').addEventListener('click',async()=>{
 const athlete=athletes.find(x=>x.id===activeAthleteId);if(!athlete)return;
 if(!confirm(`Excluir o atleta "${athlete.name}" e toda a sua agenda e biblioteca? Esta ação não poderá ser desfeita sem um backup.`))return;
 try{if(!(await saveQueue))throw Error('Há dados não salvos. Exporte um backup antes de excluir.');
  await api(`/api/athletes/${encodeURIComponent(athlete.id)}`,{method:'DELETE'});
  athletes=await api('/api/athletes');activeAthleteId=null;await switchAthlete(athletes[0].id);toast('Atleta excluído.');
 }catch(error){toast(error.message)}
});
function toast(msg){$('toast').textContent=msg;$('toast').classList.remove('hidden');clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('toast').classList.add('hidden'),2500)}
function sorted(list){return list.slice().sort((a,b)=>(a.start||'').localeCompare(b.start||''))}
function parseTime(value){
 if(typeof value!=='string')return null;
 const match=/^([01]\d|2[0-3]):([0-5]\d)$/.exec(value.trim());
 return match?Number(match[1])*60+Number(match[2]):null;
}
function minutes(e){
 const start=parseTime(e.start),end=parseTime(e.end);
 return start===null||end===null||end<=start?null:end-start;
}
function hours(n){const h=Math.floor(n/60),m=n%60;return m?`${h}h ${String(m).padStart(2,'0')}min`:`${h}h`}
function schoolKey(s){return (s||'').trim().replace(/\s+/g,' ').toLocaleLowerCase('pt-BR')||'__sem_escola__'}
function schoolGroups(){
 const groups=new Map();
 available.forEach(a=>{const key=schoolKey(a.school),name=(a.school||'').trim().replace(/\s+/g,' ')||'Sem escola / clube';if(!groups.has(key))groups.set(key,{name,items:[]});groups.get(key).items.push(a)});
 return [...groups.values()].sort((a,b)=>a.name.localeCompare(b.name,'pt-BR')).map((g,i)=>{
 const colorIndex=i%6;
 return `<section class="school-group"><header class="school-group-header school-color-${colorIndex}"><div class="flex justify-between items-center gap-2"><h4 class="font-extrabold text-sm break-words school-title-color-${colorIndex}">🏫 ${esc(g.name)}</h4><span class="text-[11px] text-slate-500 whitespace-nowrap">${g.items.length} ${g.items.length===1?'opção':'opções'}</span></div></header><div class="school-group-items">${sorted(g.items).map(a=>card(a,'available')).join('')}</div></section>`;
 }).join('')
}
function renderSummary(){
 const sums={training:0,game:0,other:0},dayMinutes=new Array(7).fill(0),dayCounts=new Array(7).fill(0);
 const schools=new Map(),validByDay=Array.from({length:7},()=>[]);
 let missing=0;
 events.forEach(e=>{
  const n=minutes(e),day=Number(e.day);
  if(n===null||!Number.isInteger(day)||day<0||day>6){missing++;return}
  sums[e.type in sums?e.type:'other']+=n;
  dayMinutes[day]+=n;dayCounts[day]++;
  validByDay[day].push({...e,startMinute:parseTime(e.start),endMinute:parseTime(e.end)});
  const key=schoolKey(e.school),label=(e.school||'').trim().replace(/\s+/g,' ')||'Sem escola / clube';
  if(!schools.has(key))schools.set(key,{label,total:0,count:0});
  const school=schools.get(key);school.total+=n;school.count++;
 });
 const total=Object.values(sums).reduce((a,b)=>a+b,0);
 $('sumTotalHours').textContent=hours(total);
 $('sumTrainingHours').textContent=hours(sums.training);
 $('sumGameHours').textContent=hours(sums.game);
 $('sumOtherHours').textContent=hours(sums.other);
 $('summaryDetails').textContent=`${events.length} atividades na semana · ${events.filter(e=>e.type==='training').length} treinos · ${events.filter(e=>e.type==='game').length} jogos · ${events.filter(e=>e.type!=='training'&&e.type!=='game').length} outras atividades`;
 $('summaryWarning').classList.toggle('hidden',!missing);
 $('summaryWarning').textContent=missing?`${missing} atividade(s) com dia ou horário de início/término ausente ou inválido não foram incluídas no cálculo de horas.`:'';
 const maxMinutes=Math.max(...dayMinutes);
 const peaks=maxMinutes>0?DAYS.filter(d=>dayMinutes[d.id]===maxMinutes):[];
 $('peakDay').textContent=peaks.length?peaks.map(d=>d.name).join(' e '):'—';
 $('peakDetail').textContent=peaks.length?`${hours(maxMinutes)} programadas · ${peaks.map(d=>dayCounts[d.id]).join(' e ')} atividade(s)`:'Nenhuma atividade com duração válida';
 const activeDays=dayMinutes.filter(n=>n>0).length;
 $('dailyAverage').textContent=activeDays?hours(Math.round(total/activeDays)):'0h';
 $('dailyAverageDetails').textContent=activeDays?`Média por ${activeDays} ${activeDays===1?'dia ativo':'dias ativos'} (dos 7 dias)`:'Nenhum dia com horas válidas';
 // CSS bars: relative height uses the highest daily duration as 100%.
 $('weeklyBars').innerHTML=DAYS.map(d=>{
  const value=dayMinutes[d.id],ratio=maxMinutes?value/maxMinutes:0;
  const pct=ratio*100;
  return `<div class="daily-bar-cell" title="${d.name}: ${hours(value)}"><span class="daily-bar-value">${hours(value)}</span><div class="daily-bar-track"><div class="daily-bar-fill ${value&&value===maxMinutes?'is-peak':''}" data-height-percent="${pct.toFixed(2)}"></div></div><span class="daily-bar-label">${d.name.slice(0,3)}</span></div>`;
 }).join('');
 $('weeklyBars').querySelectorAll('[data-height-percent]').forEach(el=>{el.style.height=Number(el.dataset.heightPercent)+'%'});
 $('weeklyBars').setAttribute('aria-label',DAYS.map(d=>`${d.name}: ${hours(dayMinutes[d.id])}`).join('; '));
 $('chartFootnote').textContent=total?`${activeDays} dia(s) com atividades válidas; ${7-activeDays} sem carga registrada. Os horários sobrepostos são somados individualmente.`:'Cadastre atividades na grade para visualizar o gráfico semanal.';
 const schoolRows=[...schools.values()].sort((a,b)=>b.total-a.total||a.label.localeCompare(b.label,'pt-BR'));
 $('schoolHours').innerHTML=schoolRows.length?schoolRows.map(g=>{
  const percentage=total?g.total/total*100:0;
  return `<div><div class="flex items-start justify-between gap-3 mb-2"><div class="min-w-0"><p class="text-sm font-bold text-slate-800 break-words">${esc(g.label)}</p><p class="text-xs text-slate-500">${g.count} ${g.count===1?'atividade':'atividades'} · ${percentage.toLocaleString('pt-BR',{maximumFractionDigits:1})}% do total</p></div><span class="font-extrabold text-sm text-slate-800 whitespace-nowrap">${hours(g.total)}</span></div><div class="school-hour-track"><div class="school-hour-fill" data-width-percent="${percentage.toFixed(2)}"></div></div></div>`;
 }).join(''):'<p class="text-sm text-slate-500 rounded-xl bg-slate-50 p-4">Sem escolas ou clubes com atividades válidas na grade.</p>';
 $('schoolHours').querySelectorAll('[data-width-percent]').forEach(el=>{el.style.width=Number(el.dataset.widthPercent)+'%'});
 const conflicts=[];
 DAYS.forEach(d=>{
  const list=validByDay[d.id].sort((a,b)=>a.startMinute-b.startMinute||a.endMinute-b.endMinute);
  for(let i=0;i<list.length;i++)for(let j=i+1;j<list.length;j++){
   const a=list[i],b=list[j];
   if(b.startMinute>=a.endMinute)break;
   const overlap=Math.min(a.endMinute,b.endMinute)-Math.max(a.startMinute,b.startMinute);
   if(overlap>0)conflicts.push({day:d.name,a,b,overlap});
  }
 });
 $('conflictsList').innerHTML=conflicts.length?`<div class="flex items-center gap-2 text-rose-700 font-bold text-sm">⚠️ ${conflicts.length} ${conflicts.length===1?'conflito encontrado':'conflitos encontrados'}</div>`+conflicts.map(c=>`<div class="conflict-item"><p class="font-bold text-sm text-rose-800">${esc(c.day)} · ${hours(c.overlap)} de sobreposição</p><p class="text-sm mt-1 text-slate-700 break-words"><strong>${esc(c.a.title)}</strong> (${esc(c.a.start)}–${esc(c.a.end)})</p><p class="text-sm text-slate-700 mt-1 break-words"><strong>${esc(c.b.title)}</strong> (${esc(c.b.start)}–${esc(c.b.end)})</p></div>`).join(''):'<div class="rounded-xl border border-emerald-100 bg-emerald-50 p-4"><p class="font-bold text-sm text-emerald-800">✓ Nenhum conflito identificado</p><p class="text-xs text-emerald-700 mt-1">Entre as atividades com horários válidos.</p></div>';
}

// Catálogo da escolinha: opções fixas, sem modificar os dados já salvos na biblioteca.
const ACADEMY_SLOTS=[
 ['baby-qui','Fut Baby','Fut Baby',0,'18:30','20:00'],
 ['t1-seg','Turma 1','Sub-6/7',1,'18:30','20:00'],
 ['t1-sex','Turma 1','Sub-6/7',5,'18:00','19:00'],
 ['t1-sab','Turma 1','Sub-6/7',6,'08:00','09:00'],
 ['t2-ter','Turma 2','Sub-8/9',2,'18:30','20:00'],
 ['t2-sex1','Turma 2','Sub-8/9',5,'19:00','20:00'],
 ['t2-sex2','Turma 2','Sub-8/9',5,'20:00','21:00'],
 ['t2-sab','Turma 2','Sub-8/9',6,'09:00','10:00'],
 ['t3-seg','Turma 3','Sub-10/11',1,'17:30','18:30'],
 ['t3-qui','Turma 3','Sub-10/11',4,'17:30','18:30'],
 ['t3-sab','Turma 3','Sub-10/11',6,'10:00','11:00'],
 ['t4-ter','Turma 4','Sub-12/13',2,'17:00','18:30'],
 ['t4-qua','Turma 4','Sub-12/13',3,'17:00','18:00'],
 ['t4-sex','Turma 4','Sub-12/13',5,'17:00','18:00']
];
// Ajuste: Fut Baby ocorre na quinta-feira (dia 4).
ACADEMY_SLOTS[0][3]=4;
const ACADEMY_COLORS={'Fut Baby':'#0b4a8c','Turma 1':'#076637','Turma 2':'#a31322','Turma 3':'#135a99','Turma 4':'#ad7800'};
function academySlot(id){const a=ACADEMY_SLOTS.find(x=>x[0]===id);return a?{id:'catalog_'+a[0],title:a[1]+' · '+a[2],type:'training',school:'Gol de Placa',day:a[3],start:a[4],end:a[5],location:'',notes:'Horário de referência do cartaz da escola · '+a[2],catalogId:a[0]}:null}
function addAcademy(id,day){const item=academySlot(id);if(!item)return;const targetDay=Number.isInteger(day)?day:item.day;
 if(events.some(e=>e.catalogId===id&&Number(e.day)===targetDay)){toast('Esse horário já está na grade desse dia.');return}
 events.push({...item,id:uid(),day:targetDay});save();render();toast(`${item.title} adicionado à ${dayName(targetDay)}.`)}
function renderAcademy(){const groups=['Fut Baby','Turma 1','Turma 2','Turma 3','Turma 4'];
 $('academyCatalog').innerHTML=groups.map(g=>{const slots=ACADEMY_SLOTS.filter(a=>a[1]===g),color=ACADEMY_COLORS[g];return `<section class="academy-card"><header class="academy-card-head academy-color-${groups.indexOf(g)}"><span>${esc(g)}</span><span class="text-xs font-semibold opacity-90">${esc(slots[0][2])}</span></header><div class="p-2.5 space-y-2">${slots.map(a=>{const added=events.some(e=>e.catalogId===a[0]&&Number(e.day)===a[3]);return `<div class="academy-slot ${added?'is-added':''}" draggable="true" tabindex="0" role="group" data-catalog-id="${a[0]}" title="Arraste para a grade semanal"><div class="min-w-0 flex-1"><p class="font-bold text-sm">${dayName(a[3])}</p><p class="text-sm font-semibold text-slate-600 whitespace-nowrap">${a[4]}–${a[5]}</p></div><button type="button" class="slot-add" data-add-catalog="${a[0]}" aria-label="Adicionar ${esc(g)} na ${dayName(a[3])}">${added?'✓ Na grade':'＋ Adicionar'}</button></div>`}).join('')}</div></section>`}).join('');
 $('academyCatalog').querySelectorAll('[data-add-catalog]').forEach(b=>b.addEventListener('click',()=>addAcademy(b.dataset.addCatalog)));
 $('academyCatalog').querySelectorAll('[data-catalog-id]').forEach(el=>{el.addEventListener('dragstart',e=>{dragged={kind:'catalog',id:el.dataset.catalogId};el.classList.add('dragging');e.dataTransfer.effectAllowed='copy';e.dataTransfer.setData('text/plain',JSON.stringify(dragged))});el.addEventListener('dragend',()=>{dragged=null;el.classList.remove('dragging');document.querySelectorAll('.day-col').forEach(x=>x.classList.remove('drag-over'))})});
}
$('toggleAcademyPhoto').addEventListener('click',()=>{const wrap=$('academyPhotoWrap');wrap.classList.toggle('hidden');const shown=!wrap.classList.contains('hidden');$('toggleAcademyPhoto').setAttribute('aria-expanded',String(shown));$('toggleAcademyPhoto').textContent=shown?'✕ Ocultar cartaz':'🖼️ Ver cartaz original'});

function render(){
 renderAcademy();renderSummary();const week=events; $('statTotal').textContent=week.length;$('statGames').textContent=week.filter(e=>e.type==='game').length;$('statTraining').textContent=week.filter(e=>e.type==='training').length;
 $('weekGrid').innerHTML=DAYS.map(d=>{const list=sorted(events.filter(e=>Number(e.day)===d.id));return `<section class="day-col" data-dropday="${d.id}">
 <header class="px-2 py-3 border-b border-slate-100 bg-slate-50/70"><div class="text-sm font-extrabold text-slate-700">${d.name}</div><div class="text-[11px] text-slate-400 mt-1">${list.length} ${list.length===1?'item':'itens'}</div></header>
 <div class="day-content duration-stack p-2" data-dropday="${d.id}">${list.length?list.map(e=>card(e,'event')).join(''):`<div class="empty-day text-center text-xs text-slate-400 py-5 border border-dashed border-slate-200 rounded-xl">Arraste para cá<br>ou adicione +</div>`}</div>
 <button class="add-day w-full border-t border-slate-100 text-xs font-bold text-indigo-600 py-2 hover:bg-indigo-50" data-day="${d.id}">＋ Adicionar</button></section>`}).join('');
 $('availableList').innerHTML=available.length?schoolGroups():`<div class="text-center py-8 px-4"><div class="text-3xl mb-2">🏫</div><p class="font-bold text-slate-700">Nenhum treino cadastrado</p><p class="text-sm text-slate-500 mt-1">Adicione as opções das escolas para começar.</p></div>`;
 document.querySelectorAll('[data-event-height]').forEach(el=>{el.style.setProperty('--event-height',Number(el.dataset.eventHeight)+'px')});
 document.querySelectorAll('.quick-remove').forEach(b=>b.addEventListener('click',e=>{e.stopPropagation();const id=b.dataset.remove,kind=b.dataset.kind,list=kind==='available'?available:events,item=list.find(x=>x.id===id);if(!item)return;if(confirm(`Remover "${item.title}" ${kind==='available'?'da biblioteca':'da grade'}?`)){if(kind==='available')available=available.filter(x=>x.id!==id);else events=events.filter(x=>x.id!==id);save();render();toast('Item removido.')}}));
 document.querySelectorAll('.add-day').forEach(b=>b.addEventListener('click',()=>openModal(null,'event',Number(b.dataset.day))));
 document.querySelectorAll('.event-card,.available-card').forEach(el=>{
  el.addEventListener('click',()=>{if(el.dataset.justDragged){delete el.dataset.justDragged;return}openModal(el.dataset.id,el.classList.contains('available-card')?'available':'event')});
  el.addEventListener('dragstart',e=>{dragged={id:el.dataset.id,kind:el.classList.contains('available-card')?'available':'event'};el.classList.add('dragging');e.dataTransfer.effectAllowed='copyMove';e.dataTransfer.setData('text/plain',JSON.stringify(dragged))});
  el.addEventListener('dragend',()=>{el.classList.remove('dragging');document.querySelectorAll('.day-col').forEach(x=>x.classList.remove('drag-over'));dragged=null});
 });
 document.querySelectorAll('.day-col').forEach(col=>{
  col.addEventListener('dragover',e=>{e.preventDefault();col.classList.add('drag-over');e.dataTransfer.dropEffect=dragged?.kind==='available'||dragged?.kind==='catalog'?'copy':'move'});
  col.addEventListener('dragleave',e=>{if(!col.contains(e.relatedTarget))col.classList.remove('drag-over')});
  col.addEventListener('drop',e=>{e.preventDefault();col.classList.remove('drag-over');let data;try{data=JSON.parse(e.dataTransfer.getData('text/plain'))}catch(_){data=dragged}if(!data)return;const day=Number(col.dataset.dropday);
   if(data.kind==='catalog'){addAcademy(data.id,day)}
   else if(data.kind==='available'){const a=available.find(x=>x.id===data.id);if(!a)return;events.push({...a,id:uid(),day,sourceId:a.id});save();render();toast(`${a.title} adicionado à ${dayName(day)}.`)}
   else{const ev=events.find(x=>x.id===data.id);if(ev&&Number(ev.day)!==day){ev.day=day;save();render();toast(`Movido para ${dayName(day)}.`)}}
  });
 });
}
function card(e,kind){
 const t=TYPES[e.type]||TYPES.other;
 if(kind==='event'){
  const duration=minutes(e),valid=duration!==null;
  const height=valid?Math.max(56,Math.round(duration*1.6)):100;
  const short=height<92;
  const tooltip=[e.title,`${e.start||'--:--'} – ${e.end||'--:--'}`,e.school||'',e.location||'',valid?hours(duration):'Duração não informada'].filter(Boolean).join(' · ');
  return `<article draggable="true" tabindex="0" role="button" aria-label="Editar ${esc(e.title)}" title="${esc(tooltip)}" class="event-card duration-card ${short?'is-short':''} ${valid?'':'is-invalid'} border rounded-xl ${t.cls}" data-event-height="${height}" data-id="${esc(e.id)}">
   <div class="duration-top"><span class="duration-time">${esc(e.start||'--:--')}${e.end?' – '+esc(e.end):''}</span><div class="flex items-center gap-1"><span class="text-xs">${t.icon}</span><button type="button" class="quick-remove" data-remove="${esc(e.id)}" data-kind="event" aria-label="Remover ${esc(e.title)}" title="Remover item">×</button></div></div>
   <p class="duration-title">${esc(e.title)}</p>
   ${!short&&e.school?`<p class="duration-extra">🏫 ${esc(e.school)}</p>`:''}
   ${!short&&height>=132&&e.location?`<p class="duration-extra">⌖ ${esc(e.location)}</p>`:''}
   ${!short?`<p class="duration-length">${valid?hours(duration):'Sem duração válida'}</p>`:''}
  </article>`;
 }
 return `<article draggable="true" tabindex="0" role="button" aria-label="Editar ${esc(e.title)}" class="available-card border rounded-xl p-2.5 ${t.cls}" data-id="${esc(e.id)}">
 <div class="flex items-center justify-between gap-1"><span class="text-[11px] font-extrabold">${esc(e.start||'--:--')}${e.end?' – '+esc(e.end):''}</span><div class="flex items-center gap-1"><span>${t.icon}</span><button type="button" class="quick-remove" data-remove="${esc(e.id)}" data-kind="available" aria-label="Remover ${esc(e.title)}" title="Remover item">×</button></div></div>
 <p class="font-bold text-sm leading-snug mt-1 break-words">${esc(e.title)}</p>
 ${e.school?`<p class="text-xs mt-1 opacity-80 break-words">🏫 ${esc(e.school)}</p>`:''}
 ${e.location?`<p class="text-xs mt-1 opacity-80 break-words">⌖ ${esc(e.location)}</p>`:''}
 <p class="text-[10px] font-bold uppercase tracking-wide mt-2 opacity-70">Disponível para adicionar</p>
 </article>`;
}
function openModal(id=null,kind='event',day=0){
 $('eventForm').reset();$('itemId').value='';$('itemKind').value=kind;$('formError').classList.add('hidden');$('deleteBtn').classList.toggle('hidden',!id);
 $('modalTitle').textContent=id?'Editar item':kind==='available'?'Novo treino disponível':'Novo compromisso';
 $('modalEyebrow').textContent=kind==='available'?'Biblioteca de treinos':'Grade semanal';
 $('day').disabled=kind==='available';
 let item=null;if(id)item=(kind==='available'?available:events).find(x=>x.id===id);
 if(item){$('itemId').value=item.id;$('title').value=item.title||'';$('type').value=item.type||'training';$('school').value=item.school||'';$('day').value=String(item.day??day);$('start').value=item.start||'16:00';$('end').value=item.end||'';$('location').value=item.location||'';$('notes').value=item.notes||''}
 else{$('day').value=String(day);$('start').value='16:00';$('end').value='17:00'}
 $('modal').classList.remove('hidden');$('modal').classList.add('flex');setTimeout(()=>$('title').focus(),30)
}
function closeModal(){$('modal').classList.add('hidden');$('modal').classList.remove('flex')}
$('eventForm').addEventListener('submit',e=>{e.preventDefault();const kind=$('itemKind').value,id=$('itemId').value,title=$('title').value.trim(),start=$('start').value,end=$('end').value,error=$('formError');if(!title||!start){error.textContent='Preencha o nome e o horário de início.';error.classList.remove('hidden');return}if(end&&end<=start){error.textContent='O término precisa ser posterior ao início.';error.classList.remove('hidden');return}
 const previous=id?(kind==='available'?available:events).find(x=>x.id===id):null;
 const item={id:id||uid(),title,type:$('type').value,school:$('school').value.trim(),day:Number($('day').value),start,end,location:$('location').value.trim(),notes:$('notes').value.trim(),
  ...(previous?.sourceId?{sourceId:previous.sourceId}:{}),...(previous?.catalogId?{catalogId:previous.catalogId}:{})};
 if(kind==='available'){if(id)available=available.map(x=>x.id===id?item:x);else available.push(item)}else{if(id)events=events.map(x=>x.id===id?item:x);else events.push(item)}
 save();closeModal();render();toast(id?'Item atualizado!':kind==='available'?'Treino disponível cadastrado!':'Compromisso adicionado à grade!')
});
$('deleteBtn').addEventListener('click',()=>{const id=$('itemId').value,kind=$('itemKind').value;if(!id)return;const list=kind==='available'?available:events;const item=list.find(x=>x.id===id);if(!item)return;if(confirm(`Excluir "${item.title}"?`)){if(kind==='available')available=available.filter(x=>x.id!==id);else events=events.filter(x=>x.id!==id);save();closeModal();render();toast('Item excluído.')}})
$('addBtn').addEventListener('click',()=>openModal(null,'event',0));$('addAvailableBtn').addEventListener('click',()=>openModal(null,'available',0));
$('closeModal').addEventListener('click',closeModal);$('cancelBtn').addEventListener('click',closeModal);$('modal').addEventListener('click',e=>{if(e.target===$('modal'))closeModal()});document.addEventListener('keydown',e=>{if(e.key==='Escape')closeModal()});
$('clearWeek').addEventListener('click',()=>{if(!events.length){toast('A grade já está vazia.');return}if(confirm('Remover todos os itens da grade? A biblioteca de treinos será mantida.')){events=[];save();render();toast('Grade limpa.')}})
$('exportBtn').addEventListener('click',()=>{const blob=new Blob([JSON.stringify({app:'Agenda do Atleta',version:'1.6.1',exportedAt:new Date().toISOString(),events,available},null,2)],{type:'application/json'});const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='agenda-atleta-v1.6.1.json';document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1500);toast('Backup JSON gerado com sucesso.')});
// Importação transacional: pré-validação completa, prévia e confirmação explícita.
let importCandidate=null;
const importModal=$('importModal');
function importMessage(message,error=false){const el=$('importFeedback');el.textContent=message;el.classList.toggle('is-error',error)}
function resetImport(){importCandidate=null;$('importFile').value='';$('importPreview').classList.add('hidden');$('confirmImport').disabled=true;importMessage('Nenhum arquivo selecionado.');document.querySelector('input[name="importMode"][value="replace"]').checked=true}
function openImport(){resetImport();importModal.classList.remove('hidden');document.body.classList.add('modal-open');$('closeImport').focus()}
function closeImport(){importModal.classList.add('hidden');document.body.classList.remove('modal-open')}
function normalizeImportedItem(item,kind,index){
 if(!item||typeof item!=='object'||Array.isArray(item))throw Error(`Item ${index+1} de ${kind} não é um objeto válido.`);
 const title=String(item.title??'').trim();
 if(!title||title.length>200)throw Error(`Item ${index+1} de ${kind} tem nome ausente ou inválido.`);
 const day=Number(item.day);
 if(!Number.isInteger(day)||day<0||day>6)throw Error(`Item ${index+1} de ${kind} possui dia da semana inválido.`);
 const start=String(item.start??'').trim(),end=String(item.end??'').trim();
 if(parseTime(start)===null)throw Error(`Item ${index+1} de ${kind} possui horário inicial inválido.`);
 if(end&&(parseTime(end)===null||parseTime(end)<=parseTime(start)))throw Error(`Item ${index+1} de ${kind} possui horário final inválido.`);
 const type=['training','game','other'].includes(item.type)?item.type:'other';
 const text=(v,max)=>String(v??'').slice(0,max);
 return {id:text(item.id,100)||uid(),title:title.slice(0,80),type,school:text(item.school,100),day,start,end,location:text(item.location,100),notes:text(item.notes,300),...(item.sourceId?{sourceId:text(item.sourceId,100)}:{}),...(item.catalogId?{catalogId:text(item.catalogId,100)}:{})};
}
function parseImportedJSON(raw){
 let data;
 try{data=JSON.parse(raw)}catch(_){throw Error('JSON inválido. Verifique se o arquivo é um backup em formato JSON.')}
 if(!data||typeof data!=='object'||Array.isArray(data))throw Error('O arquivo deve conter um objeto JSON com os campos events e available.');
 if(!Array.isArray(data.events)||!Array.isArray(data.available))throw Error('Estrutura incompatível. O arquivo precisa conter as listas "events" e "available".');
 if(data.events.length+data.available.length>20000)throw Error('Arquivo excede o limite de 20.000 itens.');
 const normalized={events:data.events.map((x,i)=>normalizeImportedItem(x,'events',i)),available:data.available.map((x,i)=>normalizeImportedItem(x,'available',i)),version:String(data.version||'não informada').slice(0,32),exportedAt:data.exportedAt};
 // IDs devem ser únicos por coleção para que edição e remoção continuem previsíveis.
 for(const collection of ['events','available']){
  const seen=new Set();for(const item of normalized[collection]){if(seen.has(item.id))item.id=uid();seen.add(item.id)}
 }
 return normalized;
}
$('importBtn').addEventListener('click',openImport);
$('closeImport').addEventListener('click',closeImport);
$('cancelImport').addEventListener('click',closeImport);
importModal.addEventListener('click',e=>{if(e.target===importModal)closeImport()});
$('importFile').addEventListener('change',async e=>{
 importCandidate=null;$('confirmImport').disabled=true;$('importPreview').classList.add('hidden');
 const file=e.target.files?.[0];if(!file){importMessage('Nenhum arquivo selecionado.');return}
 if(file.size>5*1024*1024){importMessage('Arquivo muito grande. O limite é de 5 MB.',true);return}
 if(!/\.json$/i.test(file.name)&&file.type!=='application/json'){importMessage('Selecione um arquivo com extensão .json.',true);return}
 try{
  importMessage('Lendo e validando o arquivo...');const data=parseImportedJSON(await file.text());importCandidate=data;
  $('previewEvents').textContent=data.events.length;$('previewAvailable').textContent=data.available.length;
  $('previewMeta').textContent=`Arquivo: ${file.name} · Versão de origem: ${data.version}`;
  $('importPreview').classList.remove('hidden');$('confirmImport').disabled=false;
  importMessage('Arquivo validado. Revise a prévia e escolha como importar.');
 }catch(error){importMessage(error.message||'Não foi possível ler o arquivo.',true)}
});
$('confirmImport').addEventListener('click',async()=>{
 if(!importCandidate)return;
 const mode=document.querySelector('input[name="importMode"]:checked')?.value||'replace';
 if(mode==='replace'&&!confirm('Substituir toda a agenda e a biblioteca atuais? Esta ação não poderá ser desfeita sem um backup.'))return;
 const oldEvents=events,oldAvailable=available;
 try{
  if(mode==='replace'){events=importCandidate.events.map(x=>({...x}));available=importCandidate.available.map(x=>({...x}))}
  else{
   const idsE=new Set(events.map(x=>x.id)),idsA=new Set(available.map(x=>x.id));
   const unique=(items,seen)=>items.map(x=>{let id=x.id;while(seen.has(id))id=uid();seen.add(id);return {...x,id}});
   events=[...events,...unique(importCandidate.events,idsE)];available=[...available,...unique(importCandidate.available,idsA)];
  }
  if(!(await save()))throw Error('Não foi possível gravar os dados no banco.');
  render();closeImport();toast(`Importação concluída: ${importCandidate.events.length} compromissos e ${importCandidate.available.length} treinos.`);
 }catch(error){events=oldEvents;available=oldAvailable;render();importMessage(error.message||'Falha ao importar os dados.',true)}
});
// Navegação adaptável: desktop expandida/compacta com memória; mobile em gaveta.
const sidebar=$('appSidebar'),scrim=$('mobileScrim');
const NAV_STATE_KEY='agendaAtleta.sidebar.compact.v1';
const mobileQuery=window.matchMedia('(max-width: 900px)');
let navCompact=false;
try{navCompact=localStorage.getItem(NAV_STATE_KEY)==='true'}catch(_){/* storage desabilitado */}
const collapseButton=$('collapseNav');
function updateSidebarUI(){
 document.body.classList.toggle('sidebar-collapsed',navCompact);
 const title=navCompact?'Expandir menu lateral':'Recolher menu lateral';
 collapseButton.setAttribute('aria-expanded',String(!navCompact));
 collapseButton.setAttribute('aria-label',title);
 collapseButton.setAttribute('title',title);
}
function toggleSidebar(){
 if(mobileQuery.matches)return; // no celular a navegação usa o menu sobreposto
 navCompact=!navCompact;
 try{localStorage.setItem(NAV_STATE_KEY,String(navCompact))}catch(_){/* mantém em memória */}
 updateSidebarUI();
}
collapseButton.addEventListener('click',toggleSidebar);
updateSidebarUI();
function setNav(open){
 const shouldOpen=Boolean(open)&&mobileQuery.matches;
 sidebar.classList.toggle('is-open',shouldOpen);
 scrim.classList.toggle('is-open',shouldOpen);
 $('openNav').setAttribute('aria-expanded',String(shouldOpen));
 document.body.classList.toggle('nav-open',shouldOpen);
}
$('openNav').addEventListener('click',()=>setNav(true));
$('closeNav').addEventListener('click',()=>setNav(false));
scrim.addEventListener('click',()=>setNav(false));
const onBreakpointChange=()=>{setNav(false);updateSidebarUI()};
if(mobileQuery.addEventListener)mobileQuery.addEventListener('change',onBreakpointChange);
else if(mobileQuery.addListener)mobileQuery.addListener(onBreakpointChange);
document.querySelectorAll('[data-nav]').forEach(a=>a.addEventListener('click',()=>{
 const fold=document.querySelector(`#section-${a.dataset.nav}`);
 if(fold)fold.open=true;
 document.querySelectorAll('[data-nav]').forEach(x=>x.classList.toggle('active',x===a));
 setNav(false);
}));
document.addEventListener('keydown',e=>{if(e.key==='Escape'){closeImport();setNav(false)}});
const FOLD_KEY='agendaAtleta.fold.v1';
let foldState={};
try{foldState=JSON.parse(localStorage.getItem(FOLD_KEY)||'{}')||{}}catch(_){}
document.querySelectorAll('details[data-fold]').forEach(panel=>{
 const id=panel.dataset.fold;
 if(typeof foldState[id]==='boolean')panel.open=foldState[id];
 panel.addEventListener('toggle',()=>{
  foldState[id]=panel.open;
  try{localStorage.setItem(FOLD_KEY,JSON.stringify(foldState))}catch(_){}
 });
});
initialize().catch(error=>{setSaveStatus('Erro ao carregar','error');toast(error.message||'Falha ao conectar ao banco de dados.');render()});
})();