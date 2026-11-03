"""Exercise orchestration with a fake SDK; never contact a provider."""
import asyncio
import json
import sys
import types

import pytest
from factory.runner import execute, parse_qa_result
from factory.tech_lead import gate_status


def install_sdk(monkeypatch, outcomes=('PASSOU',), valid=True, error=None):
    calls, tasks, agents = [], [], []
    qa = iter(outcomes)

    class Agent:
        def __init__(self, name, model, instructions, tools=None):
            self.name, self.tools = name, tools or []
            agents.append(self)

    class Runner:
        @staticmethod
        async def run(agent, task, max_turns):
            calls.append(agent.name)
            tasks.append(task)
            assert max_turns == 12
            assert agent.model_settings.max_tokens == 4000
            if error == 'timeout':
                await asyncio.sleep(1)
            if error == 'exception':
                raise RuntimeError('sensitive provider details')
            output = 'implementado'
            if agent.name == 'Desenvolvedor Full Stack' and valid:
                next(t for t in agent.tools if t.__name__ == 'write_file')(
                    'index.html', '<html><title>MVP</title><meta name="viewport"></html>')
            if agent.name == 'QA':
                output = 'Achado objetivo: botão.\nRESULTADO_QA: ' + next(qa)
            if agent.name == 'Tech Lead':
                output = 'VEREDITO: APROVADO'
            return types.SimpleNamespace(final_output=output,
                context_wrapper=types.SimpleNamespace(usage=types.SimpleNamespace(total_tokens=10)))

    monkeypatch.setitem(sys.modules, 'agents', types.SimpleNamespace(
        Agent=Agent, Runner=Runner, ModelSettings=types.SimpleNamespace, function_tool=lambda f: f))
    return calls, tasks, agents


def run(tmp_path, **kwargs):
    return json.loads(execute('Portal', 'MVP', tmp_path / 'projects', 'fake', **kwargs).read_text())


def test_success_and_independent_lead(tmp_path, monkeypatch):
    calls, _, agents = install_sdk(monkeypatch)
    report = run(tmp_path, allow_correction=True)
    assert calls == ['Product Owner', 'Arquiteto Web', 'Desenvolvedor Full Stack', 'QA', 'Tech Lead']
    assert report['status'] == 'AGUARDANDO_REVISAO_HUMANA'
    assert report['attempt_count'] == 1
    assert 'write_file' not in [t.__name__ for t in agents[-1].tools]


@pytest.mark.parametrize('outcomes,status', [
    (('FALHOU', 'PASSOU'), 'AGUARDANDO_REVISAO_HUMANA'),
    (('FALHOU', 'FALHOU'), 'AJUSTES_OBRIGATORIOS')])
def test_correction_is_bounded_and_keeps_history(tmp_path, monkeypatch, outcomes, status):
    calls, tasks, _ = install_sdk(monkeypatch, outcomes)
    report = run(tmp_path, allow_correction=True)
    assert calls == ['Product Owner', 'Arquiteto Web', 'Desenvolvedor Full Stack', 'QA',
                     'Desenvolvedor Full Stack', 'QA', 'Tech Lead']
    assert report['status'] == status
    assert report['attempt_count'] == 2
    assert report['attempts'][0]['qa_result'] == 'FALHOU'
    assert 'Achado objetivo' in tasks[4] and 'Critérios' in tasks[-1]
    assert 'Histórico' in tasks[-1]


def test_default_does_not_correct(tmp_path, monkeypatch):
    calls, _, _ = install_sdk(monkeypatch, ('FALHOU',))
    report = run(tmp_path)
    assert calls.count('Desenvolvedor Full Stack') == 1
    assert report['status'] == 'AJUSTES_OBRIGATORIOS'
    assert report['stop_reason'] == 'CORRECAO_DESABILITADA'


def test_unknown_qa_does_not_speculate(tmp_path, monkeypatch):
    calls, _, _ = install_sdk(monkeypatch, ('garbage',))
    report = run(tmp_path, allow_correction=True)
    assert calls.count('QA') == 1
    assert report['status'] == 'NAO_VERIFICADO'


def test_static_failure_overrides_qa_and_lead(tmp_path, monkeypatch):
    calls, _, _ = install_sdk(monkeypatch, ('PASSOU', 'PASSOU'), valid=False)
    report = run(tmp_path, allow_correction=True)
    assert calls.count('QA') == 2
    assert report['status'] == 'AJUSTES_OBRIGATORIOS'


@pytest.mark.parametrize('error', ['timeout', 'exception'])
def test_interruption_writes_partial_report(tmp_path, monkeypatch, error):
    calls, _, _ = install_sdk(monkeypatch, error=error)
    report = run(tmp_path, timeout_seconds=0.01)
    assert len(calls) == 1
    assert report['status'] == 'NAO_VERIFICADO'
    assert not report['tech_lead_executed']
    assert 'sensitive' not in json.dumps(report)


def test_budget_stops_before_next_agent(tmp_path, monkeypatch):
    calls, _, _ = install_sdk(monkeypatch)
    report = run(tmp_path, token_budget=10)
    assert len(calls) == 1
    assert report['stop_reason'] == 'ORCAMENTO_ATINGIDO'
    assert report['status'] == 'NAO_VERIFICADO'


@pytest.mark.parametrize('text,expected', [
    ('RESULTADO_QA: PASSOU', 'PASSOU'), ('RESULTADO_QA: FALHOU', 'FALHOU'),
    ('PASSOU', 'NAO_VERIFICADO'),
    ('RESULTADO_QA: PASSOU\nRESULTADO_QA: INVALIDO', 'NAO_VERIFICADO'), ('RESULTADO_QA: INVALIDO', 'NAO_VERIFICADO'),
    ('RESULTADO_QA: PASSOU\nRESULTADO_QA: FALHOU', 'NAO_VERIFICADO')])
def test_qa_parser(text, expected):
    assert parse_qa_result(text) == expected


@pytest.mark.parametrize('qa,expected', [('FALHOU', 'AJUSTES_OBRIGATORIOS'),
                                        ('NAO_VERIFICADO', 'NAO_VERIFICADO')])
def test_lead_cannot_override_qa(qa, expected):
    assert gate_status('APROVADO', 'PASSOU: básico', qa) == expected


@pytest.mark.parametrize('limits', [{'max_turns': 0}, {'timeout_seconds': float('inf')},
                                     {'token_budget': -1}, {'max_output_tokens': 0}])
def test_invalid_limits_make_no_calls(tmp_path, monkeypatch, limits):
    calls, _, _ = install_sdk(monkeypatch)
    with pytest.raises(ValueError):
        run(tmp_path, **limits)
    assert not calls


@pytest.mark.parametrize('budget,agent,field,count', [
    (25, 'Desenvolvedor Full Stack', 'implementation', 3),
    (35, 'QA', 'qa', 4),
    (45, 'Tech Lead', 'tech_lead', 5),
    (50, 'Tech Lead', 'tech_lead', 5),
])
def test_completed_outputs_survive_budget(tmp_path, monkeypatch, budget, agent, field, count):
    calls, _, _ = install_sdk(monkeypatch)
    report = run(tmp_path, token_budget=budget, allow_correction=True)
    assert len(calls) == count and calls[-1] == agent
    assert report[field]
    assert sum(item['total_tokens'] for item in report['usage']) == count * 10
    assert report['stages'][-1] == dict(agent=agent, executed=True, completed=True,
        result_available=True, output=report[field], total_tokens=10)
    assert report['interrupted'] and report['status'] == 'NAO_VERIFICADO'
    if agent == 'Desenvolvedor Full Stack':
        assert report['attempts'][-1]['implementation'] == report[field]
    if agent == 'QA':
        assert report['attempts'][-1]['qa'] == report[field]
    if agent == 'Tech Lead':
        assert report['tech_lead_executed'] and report['tech_lead_result_available']
        assert report['tech_lead_verdict'] == 'APROVADO'


@pytest.mark.parametrize('failure', ['unicode', 'oserror'])
def test_html_read_failure_preserves_report(tmp_path, monkeypatch, capsys, failure):
    install_sdk(monkeypatch)
    original = __import__('pathlib').Path.read_text

    def read(path, *args, **kwargs):
        if path.name == 'index.html':
            if failure == 'unicode':
                raise UnicodeDecodeError('utf-8', b'\xff', 0, 1, 'sensitive bytes')
            raise OSError('sensitive path')
        return original(path, *args, **kwargs)

    monkeypatch.setattr('pathlib.Path.read_text', read)
    report = run(tmp_path)
    assert report['interrupted'] and report['status'] == 'NAO_VERIFICADO'
    assert report['static_validation'].startswith('NAO_VERIFICADO:')
    assert report['attempts'][0]['qa']
    assert 'sensitive' not in json.dumps(report) + capsys.readouterr().out


@pytest.mark.parametrize('error,extra,expected', [
    (None, [], 0), ('timeout', ['--timeout-seconds', '0.01'], 1),
    ('exception', [], 1), (None, ['--token-budget', '25'], 1),
    ('html', [], 1),
])
def test_cli_exit_and_partial_report(tmp_path, monkeypatch, capsys, error, extra, expected):
    import runpy
    install_sdk(monkeypatch, error=error)
    if error == 'html':
        from factory.workspace import Workspace

        def unreadable(workspace):
            raise OSError('sensitive HTML path')

        monkeypatch.setattr(Workspace, 'validate_site', unreadable)
    monkeypatch.setenv('OPENAI_API_KEY', 'fake-never-sent')
    monkeypatch.setattr(sys, 'argv', ['factory.runner', '--project', 'Portal', '--prompt', 'MVP',
                                    '--output', str(tmp_path / 'projects'), *extra])
    monkeypatch.delitem(sys.modules, 'factory.runner', raising=False)
    with pytest.raises(SystemExit) as exited:
        runpy.run_module('factory.runner', run_name='__main__')
    assert exited.value.code == expected
    report = json.loads((tmp_path / 'reports' / 'portal.json').read_text())
    assert report['interrupted'] == bool(expected)
    assert 'sensitive' not in json.dumps(report) + capsys.readouterr().out


def test_tl_started_without_result_is_recorded(tmp_path, monkeypatch):
    install_sdk(monkeypatch)
    runner = sys.modules['agents'].Runner
    original = runner.run

    async def fail_tl(agent, task, max_turns):
        if agent.name == 'Tech Lead':
            raise RuntimeError('sensitive')
        return await original(agent, task, max_turns)

    monkeypatch.setattr(runner, 'run', fail_tl)
    report = run(tmp_path)
    assert report['tech_lead_executed']
    assert not report['tech_lead_result_available']
    assert not report['stages'][-1]['completed']
    assert report['stages'][-1]['total_tokens'] is None
    assert report['status'] == 'NAO_VERIFICADO'


@pytest.mark.parametrize('failure', ['unicode', 'oserror'])
def test_only_final_validation_fails(tmp_path, monkeypatch, capsys, failure):
    install_sdk(monkeypatch)
    from factory.workspace import Workspace
    original = Workspace.validate_site
    validations = []

    def validate(workspace):
        validations.append(True)
        if len(validations) == 2:
            if failure == 'unicode':
                raise UnicodeDecodeError('utf-8', b'\xff', 0, 1, 'sensitive')
            raise OSError('sensitive')
        return original(workspace)

    monkeypatch.setattr(Workspace, 'validate_site', validate)
    report = run(tmp_path)
    assert report['tech_lead_result_available']
    assert report['tech_lead_verdict'] == 'APROVADO'
    assert report['status'] == 'NAO_VERIFICADO'
    assert report['interrupted']
    assert report['error_category'] == 'HTML_READ_ERROR'
    assert report['stop_reason'] == 'VALIDACAO_INDISPONIVEL'
    assert 'sensitive' not in json.dumps(report) + capsys.readouterr().out
