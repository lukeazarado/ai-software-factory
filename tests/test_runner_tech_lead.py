"""Verify real five-agent orchestration without OpenAI API calls."""
import json
from pathlib import Path
import sys
import types

from factory.runner import execute


def test_pipeline_invokes_five_agents_and_records_tech_lead(tmp_path, monkeypatch):
    calls = []

    class FakeAgent:
        def __init__(self, name, model, instructions, tools=None):
            self.name = name
            self.tools = tools or []

    class FakeRunner:
        @staticmethod
        def run_sync(agent, task):
            calls.append(agent.name)
            if agent.name == 'Desenvolvedor Full Stack':
                for tool in agent.tools:
                    if tool.__name__ == 'write_file':
                        tool('index.html', '<html><head><title>MVP</title><meta name="viewport" content="width=device-width"></head></html>')
            output = 'VEREDITO: APROVADO' if agent.name == 'Tech Lead' else f'Feito por {agent.name}'
            return types.SimpleNamespace(final_output=output)

    fake = types.SimpleNamespace(Agent=FakeAgent, Runner=FakeRunner, function_tool=lambda f: f)
    monkeypatch.setitem(sys.modules, 'agents', fake)
    result = execute('Meu Portal', 'Criar MVP', tmp_path / 'projects', 'modelo-teste')
    report = json.loads(result.read_text(encoding='utf-8'))
    assert calls == ['Product Owner', 'Arquiteto Web', 'Desenvolvedor Full Stack', 'QA', 'Tech Lead']
    assert report['tech_lead_verdict'] == 'APROVADO'
    assert report['status'] == 'AGUARDANDO_REVISAO_HUMANA'
    assert (tmp_path / 'projects' / 'meu-portal' / 'index.html').exists()


def test_failed_validation_blocks_approval(tmp_path, monkeypatch):
    class FakeAgent:
        def __init__(self, name, model, instructions, tools=None):
            self.name = name
    class FakeRunner:
        @staticmethod
        def run_sync(agent, task):
            return types.SimpleNamespace(final_output='VEREDITO: APROVADO')
    monkeypatch.setitem(sys.modules, 'agents', types.SimpleNamespace(Agent=FakeAgent, Runner=FakeRunner, function_tool=lambda f: f))
    report = json.loads(execute('Sem Site', 'MVP', tmp_path / 'projects', 'modelo-teste').read_text())
    assert report['status'] == 'AJUSTES_OBRIGATORIOS'