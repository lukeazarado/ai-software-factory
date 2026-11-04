import json
import pytest

from factory import auto_pr_review as review

SHA = 'a' * 40
REPO = 'lukeazarado/ai-software-factory'


def sample():
    pr = {'number': 6, 'state': 'open', 'base': {'ref': 'main'},
          'head': {'sha': SHA, 'repo': {'full_name': REPO}}}
    event = {'workflow_run': {
        'event': 'pull_request', 'status': 'completed', 'conclusion': 'success',
        'head_repository': {'full_name': REPO}, 'head_sha': SHA,
        'pull_requests': [{'number': 6, 'head': {'sha': SHA}}],
    }}
    return event, pr


def test_select_live_pr(monkeypatch):
    event, pr = sample()
    calls = []
    def get(path, token):
        calls.append(path)
        return pr
    monkeypatch.setattr(review, 'github_json', get)
    run, got = review.valid_target(event, REPO, 'token')
    assert run['conclusion'] == 'success' and got == pr
    assert len(calls) == 1


def test_skip_stale_pr_and_fork_before_any_api(monkeypatch):
    event, pr = sample()
    monkeypatch.setattr(review, 'github_json', lambda *a: pr)
    pr['head']['sha'] = 'b' * 40
    assert review.valid_target(event, REPO, 'token') is None
    event['workflow_run']['head_repository']['full_name'] = 'other/repo'
    monkeypatch.setattr(review, 'github_json', lambda *a: (_ for _ in ()).throw(AssertionError('API should not be called')))
    assert review.valid_target(event, REPO, 'token') is None


def test_do_not_run_for_manual_workflow(monkeypatch):
    event, _ = sample()
    event['workflow_run']['event'] = 'workflow_dispatch'
    monkeypatch.setattr(review, 'github_json', lambda *a: (_ for _ in ()).throw(AssertionError('API should not be called')))
    assert review.valid_target(event, REPO, 'token') is None


def test_fallback_lookup_when_event_omits_pr_list(monkeypatch):
    event, pr = sample()
    event['workflow_run']['pull_requests'] = []
    found = []
    def api(path, token):
        found.append(path)
        return [{'number': 6}] if '/commits/' in path else pr
    monkeypatch.setattr(review, 'github_json', api)
    assert review.valid_target(event, REPO, 'token') is not None
    assert '/commits/' in found[0]


def test_review_disabled_produces_no_paid_calls(tmp_path, monkeypatch):
    event, pr = sample()
    calls = []
    monkeypatch.setattr(review, 'github_json', lambda *a: pr)
    monkeypatch.setattr(review, 'upsert_comment', lambda repo, n, sha, body, token: calls.append(body))
    result = review.execute(event, REPO, 'testtoken', False, 'test-model', tmp_path)
    assert result['verdict'] == 'NAO_VERIFICADO'
    assert result['ai_enabled'] is False
    assert 'não está' not in calls[0] or 'desabilitada' in calls[0]
    assert (tmp_path / 'auto-tech-lead.json').is_file()


def test_failed_ci_requires_adjustments_without_ai(tmp_path, monkeypatch):
    event, pr = sample()
    event['workflow_run']['conclusion'] = 'failure'
    monkeypatch.setattr(review, 'github_json', lambda *a: pr)
    comments = []
    monkeypatch.setattr(review, 'upsert_comment', lambda *args: comments.append(args[3]))
    result = review.execute(event, REPO, 'testtoken', True, 'test-model', tmp_path)
    assert result['verdict'] == 'AJUSTES_OBRIGATORIOS'
    assert 'O CI não passou' in comments[0]


def test_ai_report_only_when_explicitly_enabled_and_key_present(tmp_path, monkeypatch):
    event, pr = sample()
    monkeypatch.setattr(review, 'github_json', lambda *a: pr)
    monkeypatch.setenv('OPENAI_API_KEY', 'only-in-test')
    report = tmp_path / 'report.json'
    report.write_text(json.dumps({'head_sha': SHA, 'verdict': 'APROVADO', 'tech_lead': 'Revisão independente'}))
    calls = []
    comment = []
    monkeypatch.setattr(review, 'upsert_comment', lambda *args: comment.append(args[3]))
    # review_pr is imported lazily from factory.tech_lead.
    import factory.tech_lead as agent
    monkeypatch.setattr(agent, 'review_pr', lambda *a: calls.append(a) or report)
    result = review.execute(event, REPO, 'token', True, 'test-model', tmp_path)
    assert result['verdict'] == 'APROVADO' and len(calls) == 1
    assert 'Revisão independente' in comment[0]


def test_comment_update_only_bot_identity(monkeypatch):
    existing = {'id': 55, 'body': f'{review.BOT_MARKER}{SHA} -->\ntext',
                'user': {'login': 'github-actions[bot]'}}
    monkeypatch.setattr(review, 'github_json', lambda *a: [existing])
    calls = []
    monkeypatch.setattr(review, 'api_mutate', lambda *a: calls.append(a))
    review.upsert_comment(REPO, 6, SHA, 'updated', 'token')
    assert calls[0][1] == 'PATCH'
    existing['user']['login'] = 'another-user'
    review.upsert_comment(REPO, 6, SHA, 'updated', 'token')
    assert calls[1][1] == 'POST'


def test_missing_head_repository_fails_closed(monkeypatch):
    event, _ = sample()
    event['workflow_run']['head_repository'] = None
    monkeypatch.setattr(review, 'github_json', lambda *a: (_ for _ in ()).throw(AssertionError('API must not be called')))
    assert review.valid_target(event, REPO, 'token') is None

def test_safe_error_categories_do_not_leak_details():
    class APIError(Exception):
        status_code = 429
    category, message = review.classify_review_failure(APIError('secret-key-do-not-log'))
    assert category == 'RATE_OR_QUOTA'
    assert 'secret-key-do-not-log' not in message
    assert review.classify_review_failure(TimeoutError('sensitive-url'))[0] == 'NETWORK_OR_TIMEOUT'
    assert review.classify_review_failure(ValueError('sensitive-payload'))[0] == 'REVIEW_PROCESS'
    assert review.classify_review_failure(Exception('sensitive-header'))[0] == 'UNEXPECTED'


def test_ai_failure_posts_safe_category_and_keeps_verdict_unverified(tmp_path, monkeypatch, capsys):
    event, pr = sample()
    monkeypatch.setattr(review, 'github_json', lambda *a: pr)
    monkeypatch.setenv('OPENAI_API_KEY', 'fake-key-not-to-leak')
    comments = []
    monkeypatch.setattr(review, 'upsert_comment', lambda *args: comments.append(args[3]))
    import factory.tech_lead as agent
    class APIError(Exception):
        status_code = 401
    monkeypatch.setattr(agent, 'review_pr', lambda *a: (_ for _ in ()).throw(APIError('fake-key-not-to-leak')))
    result = review.execute(event, REPO, 'token', True, 'test-model', tmp_path)
    assert result['verdict'] == 'NAO_VERIFICADO'
    assert result['failure_category'] == 'AUTH_OR_PERMISSION'
    assert 'AUTH_OR_PERMISSION' in comments[0]
    assert 'fake-key-not-to-leak' not in comments[0] + capsys.readouterr().out
