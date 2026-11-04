import { squadSignals, simulateDelay, milestoneDate, isDate, today } from './core.js';

const list = (rows, render, emptyMessage) => rows.length
  ? `<div class="exec-list">${rows.map(render).join('')}</div>`
  : `<p class="empty-note">${emptyMessage}</p>`;

function scoped(row, allowed) { return !row.projectId || allowed.has(row.projectId); }

export function executiveAgenda(data, projects, { esc, fmt, name }) {
  const allowed = new Set(projects.map(project => project.id));
  const issues = data.issues.filter(item => scoped(item, allowed));
  const decisions = data.decisions.filter(item => scoped(item, allowed));
  const openIssues = issues.filter(item => item.status === 'Aberto')
    .sort((a, b) => a.due.localeCompare(b.due));
  const pending = decisions.filter(item => item.status === 'Pendente')
    .sort((a, b) => a.due.localeCompare(b.due));
  const issueCard = item => `<article class="exec-item ${item.kind === 'blocker' ? 'blocker' : 'risk'}">
    <div class="exec-item-top"><span class="badge ${item.kind === 'blocker' ? 'danger' : 'warning'}">${item.kind === 'blocker' ? 'Impedimento ativo' : 'Risco potencial'}</span><span class="subtext">Resposta até ${fmt(item.due)}</span></div>
    <h3>${esc(item.title)}</h3><p>${esc(item.projectId ? name('projects', item.projectId) : 'Portfólio')} · Impacto ${esc(item.impact)}${item.kind === 'risk' ? ` · Probabilidade ${esc(item.probability)}` : ''}</p>
    <p>Responsável: <strong>${esc(item.owner)}</strong></p><p class="exec-action">Ação: ${esc(item.action)}</p>
    <button class="quiet" data-edit="issues" data-id="${esc(item.id)}">Editar registro</button></article>`;
  const decisionCard = item => `<article class="exec-item decision">
    <div class="exec-item-top"><span class="badge warning">Decisão necessária</span><span class="subtext">Até ${fmt(item.due)}</span></div>
    <h3>${esc(item.question)}</h3><p>${esc(item.projectId ? name('projects', item.projectId) : 'Portfólio')} · Decisor: <strong>${esc(item.owner)}</strong></p>
    <p><b>Opções:</b> ${esc(item.options)}</p><p class="exec-action"><b>Recomendação:</b> ${esc(item.recommendation)}</p>
    <button class="quiet" data-edit="decisions" data-id="${esc(item.id)}">Editar registro</button></article>`;
  return `<div class="section-intro"><div><h2>Pauta de gestão</h2><p>Riscos ainda podem acontecer; impedimentos já bloqueiam uma entrega. Decisões têm uma data e um responsável.</p></div>
    <div class="card-tools"><button class="secondary" data-add="decisions">＋ Decisão</button><button class="primary" data-add="issues">＋ Risco ou impedimento</button></div></div>
    <section class="exec-columns"><article class="card"><div class="card-head"><div><h2>Riscos e impedimentos <small>${openIssues.length} abertos</small></h2><p>Priorize a resposta antes de afetar a entrega.</p></div></div><div class="card-body">${list(openIssues, issueCard, 'Nenhum risco ou impedimento aberto neste recorte.')}</div></article>
    <article class="card"><div class="card-head"><div><h2>Decisões pendentes <small>${pending.length}</small></h2><p>Pergunta, opções, recomendação e prazo em uma pauta.</p></div></div><div class="card-body">${list(pending, decisionCard, 'Nenhuma decisão pendente neste recorte.')}</div></article></section>
    <section class="card"><div class="card-head"><div><h2>Histórico resolvido</h2><p>Registros encerrados permanecem disponíveis para consulta.</p></div></div><div class="card-body">${list(issues.filter(item => item.status === 'Resolvido'), issueCard, 'Ainda não há registros resolvidos.')}${list(decisions.filter(item => item.status === 'Decidida'), decisionCard, 'Ainda não há decisões concluídas.')}</div></section>`;
}

export function capacityView(data, projects, { esc, fmt, name }) {
  const projectIds = projects.map(project => project.id);
  const signals = squadSignals(data, { projectIds });
  return `<section class="card"><div class="card-head"><div><h2>Conflitos de agenda por squad</h2><p>Próximos 30 dias · ${fmt(today())} como referência.</p></div><span class="badge">${signals.length} squads com atividade</span></div>
    <p class="inline-note">Só há sinal de simultaneidade quando as janelas planejadas se sobrepõem. Projetos em períodos distintos continuam visíveis, mas não contam como conflito. O quadro não representa percentual de ocupação, capacidade disponível ou confirmação de conflito pela squad.</p>
    <div class="table-wrap"><table><thead><tr><th>Cluster / squad</th><th>Projetos ativos</th><th>Janelas sobrepostas</th><th>Marcos em 30 dias</th><th>Sinal</th></tr></thead><tbody>${signals.map(item => `<tr><td><strong>${esc(name('clusters', item.clusterId))} / ${esc(name('squads', item.squadId))}</strong></td>
      <td>${item.projects.length}<span class="subtext">${item.projects.map(project => esc(project.name)).join(' · ')}</span></td><td>${item.overlaps.length}</td><td>${item.milestones.length}<span class="subtext">${item.milestones.map(milestone => `${esc(milestone.name)} · ${fmt(milestoneDate(milestone))}`).join('<br>')}</span></td>
      <td><span class="badge ${item.overlaps.length ? 'warning' : 'neutral'}">${esc(item.signal)}</span></td></tr>`).join('')}</tbody></table></div>
    ${signals.length ? '' : '<div class="empty">Nenhum compromisso ativo no recorte atual.</div>'}</section>`;
}

export function simulationView(data, projects, sourceId, scenarioDate, { esc, fmt, name }) {
  const allowed = new Set(projects.map(project => project.id));
  const candidates = data.milestones.filter(item => !item.done && allowed.has(item.projectId));
  if (!candidates.length) return `<section class="card"><div class="card-head"><div><h2>Simular atraso</h2><p>Selecione um marco pendente no recorte atual.</p></div></div><div class="card-body"><p class="empty">Não há marcos pendentes para simular.</p></div></section>`;
  const source = candidates.find(item => item.id === sourceId) || candidates[0];
  const date = isDate(scenarioDate) && scenarioDate >= milestoneDate(source) ? scenarioDate : milestoneDate(source);
  const result = simulateDelay(data, source.id, date, { projectIds: [...allowed] });
  const project = data.projects.find(item => item.id === source.projectId);
  return `<section class="card"><div class="card-head"><div><h2>Cenário hipotético</h2><p>Teste uma nova previsão para o fornecedor e veja a cadeia de entregas que pode ser afetada.</p></div><span class="badge warning">Não altera o plano oficial</span></div>
    <div class="card-body"><div class="simulation-controls"><label class="field"><span>Marco fornecedor</span><select id="simulation-source">${candidates.map(item => `<option value="${esc(item.id)}" ${item.id === source.id ? 'selected' : ''}>${esc(item.name)} · ${esc(name('projects', item.projectId))}</option>`).join('')}</select></label>
    <label class="field"><span>Nova data prevista no cenário</span><input type="date" id="simulation-date" min="${milestoneDate(source)}" max="2200-12-31" value="${date}"></label></div>
    <p class="scenario-summary"><strong>${esc(source.name)}</strong> · ${esc(name('clusters', project.clusterId))} / ${esc(name('squads', project.squadId))}<br>Previsão atual: ${fmt(milestoneDate(source))} → Cenário: ${fmt(result.scenario)}.</p>
    <p class="inline-note">Para cada entrega dependente, o cenário considera a data mais tarde entre sua previsão atual e a data simulada do fornecedor. É uma leitura simplificada de alcance; não calcula caminho crítico, duração de trabalho ou nova data oficial.</p>
    ${result.affected.length ? `<h3>Entregas potencialmente afetadas</h3><div class="table-wrap"><table><thead><tr><th>Entrega</th><th>Cluster / squad</th><th>Previsão atual</th><th>Neste cenário</th><th>Relação</th></tr></thead><tbody>${result.affected.map(row => `<tr><td><strong>${esc(row.milestone.name)}</strong><span class="subtext">${esc(row.project.name)}</span></td><td>${esc(name('clusters', row.project.clusterId))} / ${esc(name('squads', row.project.squadId))}</td><td>${fmt(row.original)}</td><td><strong>${fmt(row.scenario)}</strong></td><td>${row.direct ? 'Direta' : 'Transitivamente alcançada'}</td></tr>`).join('')}</tbody></table></div>` : '<div class="empty">Nenhuma entrega pendente ligada a este marco no recorte.</div>'}
    </div></section>`;
}

export function executiveReportHTML(data, projects, { esc, fmt, name }) {
  const allowed = new Set(projects.map(project => project.id));
  const issues = data.issues.filter(item => item.status === 'Aberto' && scoped(item, allowed));
  const decisions = data.decisions.filter(item => item.status === 'Pendente' && scoped(item, allowed));
  const rows = [...issues.map(item => `<tr><td>${item.kind === 'blocker' ? 'Impedimento' : 'Risco'}</td><td>${esc(item.title)}</td><td>${esc(item.projectId ? name('projects', item.projectId) : 'Portfólio')}</td><td>${esc(item.owner)}</td><td>${fmt(item.due)}</td><td>${esc(item.action)}</td></tr>`),
    ...decisions.map(item => `<tr><td>Decisão necessária</td><td>${esc(item.question)}<br><small>Opções: ${esc(item.options)}<br>Recomendação: ${esc(item.recommendation)}</small></td><td>${esc(item.projectId ? name('projects', item.projectId) : 'Portfólio')}</td><td>${esc(item.owner)}</td><td>${fmt(item.due)}</td><td>Definir encaminhamento</td></tr>`)];
  return `<h2>Riscos, impedimentos e decisões</h2>${rows.length ? `<table><thead><tr><th>Tipo</th><th>Assunto / recomendação</th><th>Escopo</th><th>Responsável</th><th>Data necessária</th><th>Próxima ação</th></tr></thead><tbody>${rows.join('')}</tbody></table>` : '<p>Nenhum risco, impedimento ou decisão pendente neste recorte.</p>'}`;
}
