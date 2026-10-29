(() => {
  'use strict';
  const KEY = 'ai-software-factory-tasks-v1';
  const form = document.getElementById('task-form');
  const input = document.getElementById('task-input');
  const list = document.getElementById('task-list');
  const empty = document.getElementById('empty-state');
  const count = document.getElementById('task-count');
  const summary = document.getElementById('task-summary');
  const pending = document.getElementById('pending-count');
  const filters = [...document.querySelectorAll('.filter')];
  let tasks = [];
  let filter = 'all';
  try {
    const saved = JSON.parse(localStorage.getItem(KEY) || '[]');
    if (Array.isArray(saved)) tasks = saved.filter(t => t && typeof t.text === 'string' && typeof t.id === 'string' && typeof t.done === 'boolean').slice(0, 500);
  } catch { tasks = []; }
  function save() { try { localStorage.setItem(KEY, JSON.stringify(tasks)); } catch { /* private mode or quota */ } }
  function render() {
    const open = tasks.filter(t => !t.done).length;
    count.textContent = String(tasks.length);
    summary.textContent = tasks.length ? `${tasks.length - open} concluídas` : 'Tudo pronto para começar';
    pending.textContent = `${open} pendente${open === 1 ? '' : 's'}`;
    const visible = tasks.filter(t => filter === 'all' || (filter === 'done' ? t.done : !t.done));
    list.replaceChildren();
    for (const task of visible) {
      const li = document.createElement('li'); li.className = `task-item${task.done ? ' done' : ''}`;
      const check = document.createElement('input'); check.type = 'checkbox'; check.checked = task.done;
      check.setAttribute('aria-label', `Marcar ${task.text} como ${task.done ? 'pendente' : 'concluída'}`);
      check.addEventListener('change', () => { task.done = check.checked; save(); render(); });
      const label = document.createElement('span'); label.className = 'task-text'; label.textContent = task.text;
      const remove = document.createElement('button'); remove.className = 'delete'; remove.textContent = 'Excluir';
      remove.setAttribute('aria-label', `Excluir tarefa ${task.text}`);
      remove.addEventListener('click', () => { tasks = tasks.filter(t => t.id !== task.id); save(); render(); });
      li.append(check, label, remove); list.append(li);
    }
    empty.hidden = visible.length > 0;
    if (!visible.length && tasks.length) {
      empty.querySelector('h3').textContent = 'Nada neste filtro';
      empty.querySelector('p').textContent = 'Experimente outro filtro para ver suas tarefas.';
    } else {
      empty.querySelector('h3').textContent = 'Nenhuma tarefa por aqui';
      empty.querySelector('p').textContent = 'Adicione sua primeira tarefa e comece a avançar.';
    }
  }
  form.addEventListener('submit', e => {
    e.preventDefault();
    const text = input.value.trim();
    if (!text) return;
    tasks.unshift({ id: crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`, text, done: false });
    save(); input.value = ''; render(); input.focus();
  });
  for (const button of filters) button.addEventListener('click', () => {
    filter = button.dataset.filter;
    for (const item of filters) { const selected = item === button; item.classList.toggle('active', selected); item.setAttribute('aria-pressed', String(selected)); }
    render();
  });
  render();
})();
