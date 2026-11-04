"""Trusted, read-only PR Tech Lead review following unprivileged PR CI.

Runs ONLY with the default-branch workflow_run payload. NEVER checks out PR code,
executes PR artifacts, approves a PR, merges, or deploys.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .tech_lead import github_json

BOT_MARKER = '<!-- ai-factory-tech-lead:'
SHA_PATTERN = re.compile(r'^[0-9a-f]{40}$')


def valid_target(event: dict, repo: str, token: str) -> tuple[dict, dict] | None:
    """Pair an actual CI workflow run with the CURRENT PR head; ignore stale runs."""
    run = event.get('workflow_run') or {}
    if run.get('event') != 'pull_request' or run.get('status') != 'completed':
        return None
    if (run.get('head_repository') or {}).get('full_name') != repo:
        return None  # don't permit privileged workflow to review forks
    sha = run.get('head_sha', '')
    if not SHA_PATTERN.fullmatch(sha):
        return None
    associated = run.get('pull_requests') or []
    if not associated:
        # Some GitHub events omit pull_requests. The server supplies PR associations.
        associated = github_json(f'/repos/{repo}/commits/{sha}/pulls?per_page=100', token)
    matches = []
    for summary in associated:
        number = summary.get('number')
        if not isinstance(number, int) or not (0 < number < 10000000):
            continue
        pr = github_json(f'/repos/{repo}/pulls/{number}', token)
        head = pr.get('head') or {}
        if (pr.get('state') != 'open' or (pr.get('base') or {}).get('ref') != 'main'
                or (head.get('repo') or {}).get('full_name') != repo):
            continue
        # Matching the event's PR head protects against a CI run for an older commit.
        event_head = (summary.get('head') or {}).get('sha')
        if not event_head and sha == head.get('sha'):
            event_head = sha
        if head.get('sha') != event_head:
            continue
        matches.append(pr)
    if len(matches) != 1:
        return None
    return run, matches[0]


def api_mutate(path: str, method: str, payload: dict, token: str) -> dict:
    if not path.startswith('/repos/') or method not in {'POST', 'PATCH'}:
        raise ValueError('Operação GitHub não permitida')
    req = Request('https://api.github.com' + path,
                  data=json.dumps(payload).encode('utf-8'), method=method,
                  headers={'Accept': 'application/vnd.github+json',
                           'Authorization': 'Bearer ' + token,
                           'X-GitHub-Api-Version': '2022-11-28',
                           'Content-Type': 'application/json',
                           'User-Agent': 'ai-software-factory-tech-lead'})
    with urlopen(req, timeout=15) as response:
        return json.load(response)


def upsert_comment(repo: str, pr: int, sha: str, body: str, token: str) -> None:
    marker = f'{BOT_MARKER}{sha} -->'
    text = marker + '\n' + body[:45000]
    # Avoid spam on reruns of the same commit. Do not update anyone else's comment.
    comments = github_json(f'/repos/{repo}/issues/{pr}/comments?per_page=100', token)
    for comment in reversed(comments):
        login = (comment.get('user') or {}).get('login', '')
        if (comment.get('body') or '').startswith(marker) and login == 'github-actions[bot]':
            api_mutate(f'/repos/{repo}/issues/comments/{comment["id"]}', 'PATCH', {'body': text}, token)
            return
    api_mutate(f'/repos/{repo}/issues/{pr}/comments', 'POST', {'body': text}, token)


def format_review(run: dict, verdict: str, details: str) -> str:
    title = '**Tech Lead automático — AI Software Factory**'
    return (f'{title}\n\n**VEREDITO: {verdict}**\n\n'
            f'- QA GitHub Actions: **{run.get("conclusion", "indisponível")}**.\n'
            f'- Commit testado: `{run["head_sha"]}`.\n'
            '- Revisão consultiva: **não aprova PR, não faz merge e não autoriza deploy**.\n\n'
            + details)


def classify_review_failure(exc: Exception) -> tuple[str, str]:
    """Return a safe diagnostic category; never expose raw exception messages.

    SDK/API exception text may contain request details or sensitive data.
    Only fixed messages and numeric HTTP statuses are used.
    """
    status = getattr(exc, 'status_code', None)
    if isinstance(exc, HTTPError):
        status = exc.code
    if isinstance(status, int):
        if status in (401, 403):
            return 'AUTH_OR_PERMISSION', 'Falha de autenticação ou permissão da API.'
        if status == 429:
            return 'RATE_OR_QUOTA', 'Limite de requisições ou cota da API atingido.'
        if status in (408, 504) or status >= 500:
            return 'API_UNAVAILABLE', 'API indisponível ou requisição expirada.'
        if status == 400:
            return 'INVALID_REQUEST', 'A API rejeitou os parâmetros da solicitação.'
    name = type(exc).__name__.lower()
    if isinstance(exc, (TimeoutError, ConnectionError, URLError)) or 'timeout' in name or 'connection' in name:
        return 'NETWORK_OR_TIMEOUT', 'Falha de rede ou tempo limite da API.'
    if isinstance(exc, (ValueError, RuntimeError)):
        return 'REVIEW_PROCESS', 'Falha de validação ou processamento da revisão.'
    return 'UNEXPECTED', 'Falha inesperada na revisão automática.'


def execute(event: dict, repo: str, token: str, ai_enabled: bool, model: str,
            output: Path) -> dict | None:
    selected = valid_target(event, repo, token)
    if not selected:
        return None
    run, pr = selected
    number = pr['number']
    status = run.get('conclusion')
    verdict = 'NAO_VERIFICADO'
    failure_category = None
    details = ('A revisão por IA está **desabilitada**; somente a execução do QA foi '
               'verificada automaticamente. Requer revisão humana do diff. Para ativar '
               'a análise semântica, configure o secret `OPENAI_API_KEY` e a variável '
               '`TECH_LEAD_AI_ENABLED=true` no repositório (pode gerar custos de API).')
    if status != 'success':
        verdict = 'AJUSTES_OBRIGATORIOS'
        details = 'O CI não passou. Corrija os testes antes da revisão técnica. Nenhum modelo de IA foi acionado.'
    elif ai_enabled and os.getenv('OPENAI_API_KEY'):
        try:
            from .tech_lead import review_pr
            output.mkdir(parents=True, exist_ok=True)
            report_path = review_pr(repo, number, token, model, output)
            report = json.loads(report_path.read_text(encoding='utf-8'))
            if report.get('head_sha') != pr['head']['sha']:
                raise RuntimeError('O HEAD do PR mudou durante a revisão')
            verdict = report['verdict']
            details = '### Revisão do diff pelo agente\n\n' + report['tech_lead'][:30000]
        except Exception as exc:
            verdict = 'NAO_VERIFICADO'
            failure_category, safe_message = classify_review_failure(exc)
            print(f'Tech Lead: falha classificada como {failure_category}')
            details = (f'A revisão automática não pôde ser concluída. **Categoria:** '
                       f'`{failure_category}`. {safe_message} '
                       'Não interprete este resultado como aprovação.')
    elif ai_enabled:
        details = ('O modo de IA foi solicitado, mas `OPENAI_API_KEY` não está disponível. '
                   'Nenhuma chamada cobrada foi realizada. **NAO_VERIFICADO**.')

    # Confirm the head has not moved while a potentially long model review ran.
    current = github_json(f'/repos/{repo}/pulls/{number}', token)
    if current.get('state') != 'open' or current.get('head', {}).get('sha') != pr['head']['sha']:
        return None
    body = format_review(run, verdict, details)
    upsert_comment(repo, number, pr['head']['sha'], body, token)
    result = {'pr': number, 'head_sha': pr['head']['sha'], 'ci_conclusion': status,
              'verdict': verdict, 'ai_enabled': bool(ai_enabled and os.getenv('OPENAI_API_KEY')),
              'failure_category': failure_category}
    output.mkdir(parents=True, exist_ok=True)
    (output / 'auto-tech-lead.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description='Automated PR Tech Lead report after GitHub CI')
    parser.add_argument('--event', type=Path, required=True)
    parser.add_argument('--repo', required=True)
    parser.add_argument('--model', default=os.getenv('OPENAI_MODEL', 'gpt-4.1-mini'))
    parser.add_argument('--output', type=Path, default=Path('workspace/reviews'))
    args = parser.parse_args()
    token = os.getenv('GITHUB_TOKEN', '')
    if not token or not args.event.is_file():
        parser.error('GITHUB_TOKEN e arquivo de evento são obrigatórios')
    with args.event.open(encoding='utf-8') as f:
        event = json.load(f)
    enabled = os.getenv('TECH_LEAD_AI_ENABLED', '').lower() == 'true'
    result = execute(event, args.repo, token, enabled, args.model, args.output)
    if result is None:
        print('Tech Lead: evento sem PR elegível ou commit obsoleto; sem alterações.')
    else:
        print(f'Tech Lead: PR #{result["pr"]} | VEREDITO: {result["verdict"]} | '
              f'CI: {result["ci_conclusion"]}')


if __name__ == '__main__':
    main()