"""Execute four specialized AI agents in a deterministic sequence.

Usage: python -m factory.runner --project meu-site --prompt "Crie um site..."
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from .workspace import Workspace, slugify


def execute(project: str, prompt: str, base_dir: Path, model: str) -> Path:
    # Import lazily so unit tests do not require API access or SDK installation.
    from agents import Agent, Runner, function_tool

    root = base_dir / slugify(project)
    workspace = Workspace(root)

    @function_tool
    def write_file(path: str, content: str) -> str:
        """Write a UTF-8 source file relative to the current project directory."""
        try:
            return workspace.write(path, content)
        except ValueError as exc:
            return f'ERRO: {exc}'

    @function_tool
    def read_file(path: str) -> str:
        """Read a UTF-8 source file relative to the current project directory."""
        try:
            return workspace.read(path)
        except (ValueError, UnicodeError) as exc:
            return f'ERRO: {exc}'

    @function_tool
    def list_files() -> str:
        """List the files created inside the current project directory."""
        return workspace.list_files()

    @function_tool
    def validate_site() -> str:
        """Perform basic static checks of the generated index.html file."""
        return workspace.validate_site()

    product = Agent(
        name='Product Owner', model=model,
        instructions='Você é Product Owner. Responda em português com escopo mínimo, histórias de usuário e critérios de aceite objetivos. Não acrescente requisitos não pedidos.',
    )
    architect = Agent(
        name='Arquiteto Web', model=model,
        instructions='Você é arquiteto. Proponha uma aplicação web estática HTML/CSS/JS para o MVP, com estrutura de arquivos, acessibilidade, responsividade e limites de segurança. Não proponha backend sem necessidade explícita.',
    )
    developer = Agent(
        name='Desenvolvedor Full Stack', model=model,
        tools=[write_file, read_file, list_files],
        instructions=(
            'Implemente de verdade a aplicação solicitada, escrevendo arquivos via write_file. '
            'Obrigatório: index.html na raiz, CSS e JS locais quando úteis, layout responsivo, '
            'acessibilidade básica, interface em português e comportamento funcional. '
            'Não apenas descreva código: chame write_file para salvar os arquivos. '
            'Não use serviços pagos, tokens ou segredos. Não crie arquivos fora do projeto. '
            'Finalize com resumo dos arquivos escritos.'
        ),
    )
    qa = Agent(
        name='QA', model=model,
        tools=[list_files, read_file, validate_site],
        instructions=(
            'Você é QA independente. Use list_files e validate_site e inspecione o código com read_file. '
            'Compare com os critérios de aceite. Liste PASSOU/FALHOU/NÃO VERIFICADO, '
            'riscos e próximos testes manuais. Não afirme ter executado navegador, testes E2E '
            'ou revisão de segurança completa. Não modifique arquivos.'
        ),
    )

    def run(agent, task):
        print(f'\n>>> {agent.name}...', flush=True)
        result = Runner.run_sync(agent, task)
        output = str(result.final_output)
        print(output[:600] + ('...' if len(output) > 600 else ''), flush=True)
        return output

    requirements = run(product, f'Solicitação do usuário:\n{prompt}')
    architecture = run(architect, f'Solicitação:\n{prompt}\n\nRequisitos:\n{requirements}')
    implementation = run(developer, f'Solicitação:\n{prompt}\n\nRequisitos:\n{requirements}\n\nArquitetura:\n{architecture}\n\nImplemente os arquivos agora.')
    review = run(qa, f'Solicitação:\n{prompt}\n\nCritérios de aceite:\n{requirements}\n\nArquivos relatados:\n{implementation}\n\nRevise o projeto existente.')

    # Reports live outside generated project: they cannot be overwritten by agents.
    report_dir = base_dir.parent / 'reports'
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f'{slugify(project)}.json'
    report_path.write_text(json.dumps({
        'project': slugify(project),
        'created_at': datetime.now(timezone.utc).isoformat(),
        'prompt': prompt,
        'model': model,
        'requirements': requirements,
        'architecture': architecture,
        'implementation': implementation,
        'qa': review,
        'static_validation': workspace.validate_site(),
        'status': 'AGUARDANDO_REVISAO_HUMANA',
        'files': workspace.list_files().splitlines(),
    }, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'\nProjeto: {root}\nRelatório: {report_path}\nStatus: aguardando revisão humana.')
    return report_path


def main():
    parser = argparse.ArgumentParser(description='Fábrica de software multiagente — MVP')
    parser.add_argument('--project', required=True, help='Nome do projeto, ex.: portal-clientes')
    parser.add_argument('--prompt', required=True, help='Descrição do sistema a construir')
    parser.add_argument('--model', default=os.getenv('OPENAI_MODEL', 'gpt-4.1-mini'))
    parser.add_argument('--output', type=Path, default=Path('workspace/projects'))
    args = parser.parse_args()
    if not os.getenv('OPENAI_API_KEY'):
        parser.error('Defina OPENAI_API_KEY antes de executar o orquestrador.')
    execute(args.project, args.prompt, args.output, args.model)


if __name__ == '__main__':
    main()
