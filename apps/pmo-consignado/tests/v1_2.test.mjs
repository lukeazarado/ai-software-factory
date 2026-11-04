import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const source = await readFile(new URL('../dist/core.js', import.meta.url), 'utf8');
const core = await import('data:text/javascript;base64,' + Buffer.from(source).toString('base64'));

function fixture() {
  const data = core.emptyData();
  data.clusters = [{ id: 'c1', name: 'Plataforma' }, { id: 'c2', name: 'Originação' }];
  data.squads = [{ id: 's1', name: 'Integrações', clusterId: 'c1' }, { id: 's2', name: 'Jornada', clusterId: 'c2' }];
  data.projects = [
    { id: 'p1', name: 'Fornecedor', owner: 'Ana', clusterId: 'c1', squadId: 's1', start: '2026-11-01', end: '2026-11-30', forecast: '2026-11-30', updated: '2026-11-04', priority: 'Alta', status: 'Em andamento' },
    { id: 'p2', name: 'Consumidor A', owner: 'Bia', clusterId: 'c2', squadId: 's2', start: '2026-11-05', end: '2026-12-05', forecast: '2026-12-05', updated: '2026-11-04', priority: 'Média', status: 'Planejado' },
    { id: 'p3', name: 'Consumidor B', owner: 'Caio', clusterId: 'c2', squadId: 's2', start: '2026-11-10', end: '2026-12-10', forecast: '2026-12-10', updated: '2026-11-04', priority: 'Baixa', status: 'Em andamento' },
  ];
  data.milestones = [
    { id: 'm1', projectId: 'p1', name: 'API base', date: '2026-11-10', forecast: '2026-11-10', done: false, actual: '' },
    { id: 'm2', projectId: 'p2', name: 'Integração A', date: '2026-11-18', forecast: '2026-11-18', done: false, actual: '' },
    { id: 'm3', projectId: 'p3', name: 'Integração B', date: '2026-11-20', forecast: '2026-11-20', done: false, actual: '' },
    { id: 'm4', projectId: 'p3', name: 'Teste integrado', date: '2026-11-21', forecast: '2026-11-21', done: false, actual: '' },
    { id: 'm5', projectId: 'p2', name: 'Entrega já concluída', date: '2026-11-17', forecast: '2026-11-17', done: true, actual: '2026-11-03' },
  ];
  data.dependencies = [
    { id: 'd1', from: 'm1', to: 'm2' }, { id: 'd2', from: 'm1', to: 'm3' },
    { id: 'd3', from: 'm2', to: 'm4' }, { id: 'd4', from: 'm3', to: 'm4' },
    { id: 'd5', from: 'm1', to: 'm5' },
  ];
  return core.validateData(data);
}

test('V1.2 accepts legacy version-1 backups and defaults executive records to empty arrays', () => {
  const legacy = core.emptyData();
  delete legacy.issues;
  delete legacy.decisions;
  const restored = core.validateData(legacy);
  assert.deepEqual(restored.issues, []);
  assert.deepEqual(restored.decisions, []);
  assert.equal(restored.version, 1);
});

test('V1.2 validates risks, blockers and decisions and rejects invalid references', () => {
  const data = fixture();
  data.issues = [{ id: 'i1', projectId: 'p1', kind: 'risk', title: 'Fornecedor pode atrasar', impact: 'Alto', probability: 'Média', owner: 'Ana', due: '2026-11-12', action: 'Revisar contrato', status: 'Aberto' },
    { id: 'i2', projectId: '', kind: 'blocker', title: 'Acesso indisponível', impact: 'Crítico', probability: '', owner: 'Bia', due: '2026-11-08', action: 'Escalar liberação', status: 'Aberto' }];
  data.decisions = [{ id: 'dsc1', projectId: 'p2', question: 'Qual integração priorizar?', options: 'A ou B', recommendation: 'A', owner: 'Diretoria', due: '2026-11-09', status: 'Pendente', outcome: '' }];
  assert.equal(core.validateData(data).issues.length, 2);
  assert.throws(() => core.validateData({ ...data, issues: [{ ...data.issues[0], projectId: 'unknown' }] }), /projeto válido/);
  assert.throws(() => core.validateData({ ...data, issues: [{ ...data.issues[0], probability: 'Certeza' }] }), /Probabilidade inválida/);
  assert.throws(() => core.validateData({ ...data, decisions: [{ ...data.decisions[0], due: '2026-02-30' }] }), /Data necessária/);
  assert.throws(() => core.validateData({ ...data, decisions: [{ ...data.decisions[0], id: 'i1' }] }), /Identificador duplicado/);
});

test('V1.2 squad signals describe overlapping planned windows, not a utilization percentage', () => {
  const data = fixture();
  const signals = core.squadSignals(data, { reference: '2026-11-04', horizonDays: 30 });
  const signal = signals.find(item => item.squadId === 's2');
  assert.equal(signal.projects.length, 2);
  assert.deepEqual(signal.overlaps, [['p2', 'p3']]);
  assert.equal(signal.milestones.length, 3);
  assert.equal(signal.signal, 'Sobreposição de períodos');
  assert.throws(() => core.squadSignals(data, { reference: '2026-11-04', horizonDays: 0 }), /Período/);
});

test('V1.2 delay simulation propagates the latest reachable date without mutating official forecasts', () => {
  const data = fixture();
  const before = JSON.stringify(data);
  const result = core.simulateDelay(data, 'm1', '2026-11-15');
  assert.equal(result.source.name, 'API base');
  assert.equal(result.affected.find(item => item.milestone.id === 'm2').scenario, '2026-11-18');
  assert.equal(result.affected.find(item => item.milestone.id === 'm3').scenario, '2026-11-20');
  assert.equal(result.affected.find(item => item.milestone.id === 'm4').scenario, '2026-11-21');
  assert.equal(result.affected.some(item => item.milestone.id === 'm5'), false);
  assert.equal(JSON.stringify(data), before);
  assert.throws(() => core.simulateDelay(data, 'm1', '2026-11-09'), /igual ou posterior/);
  assert.throws(() => core.simulateDelay(data, 'missing', '2026-11-15'), /marco pendente/);
});

test('V1.2 simulation respects the project recorte while still traversing cross-squad dependencies', () => {
  const data = fixture();
  const result = core.simulateDelay(data, 'm1', '2026-11-15', { projectIds: ['p1'] });
  assert.deepEqual(result.affected, []);
  assert.throws(() => core.simulateDelay(data, 'm2', '2026-11-20', { projectIds: ['p1'] }), /fora do recorte/);
});
