import json
import pytest
from alpha_evolve.openrouter_budget import MeteredOpenRouter


def test_historical_import_uses_unique_response_costs_and_survives_restart(tmp_path):
    journal = tmp_path / 'usage.jsonl'
    journal.write_text('\n'.join(json.dumps({'response_id': rid, 'cost_usd': cost}) for rid, cost in [('a', 4.), ('b', 3.), ('b', 3.)]))
    client = MeteredOpenRouter(tmp_path / 'meter', 'secret', 'openai/gpt-4.1', study='test')
    client.import_usage(journal)
    client.import_usage(journal)
    assert client.snapshot()['project_committed_usd'] == 7.
    fresh = MeteredOpenRouter(tmp_path / 'meter', 'secret', 'openai/gpt-4.1', study='test')
    assert fresh.snapshot()['project_committed_usd'] == 7.
    assert 'secret' not in client.ledger_path.read_text()


def test_cache_prevents_duplicate_paid_calls(tmp_path):
    calls = []
    def transport(request):
        calls.append(request)
        return {'id': 'r1', 'model': 'gpt-4.1', 'choices': [{'message': {'content': 'ok'}}], 'usage': {'cost': .001}}
    client = MeteredOpenRouter(tmp_path, 'secret', 'openai/gpt-4.1', study='test', transport=transport)
    first = client.complete([{'role': 'user', 'content': 'hello'}])
    fresh = MeteredOpenRouter(tmp_path, 'secret', 'openai/gpt-4.1', study='test', transport=transport)
    assert fresh.complete([{'role': 'user', 'content': 'hello'}]) == first
    assert len(calls) == 1
    assert fresh.snapshot()['study_committed_usd'] == .001


def test_ambiguous_timeout_keeps_reservation_and_refuses_duplicate(tmp_path):
    calls = []
    def transport(request):
        calls.append(request)
        raise TimeoutError('uncertain provider result')
    client = MeteredOpenRouter(tmp_path, 'secret', 'openai/gpt-4.1', study='test', transport=transport)
    with pytest.raises(TimeoutError):
        client.complete([{'role': 'user', 'content': 'hello'}])
    assert client.snapshot()['uncertain_calls'] == 1
    assert client.snapshot()['study_committed_usd'] > 0
    with pytest.raises(RuntimeError, match='ambiguous'):
        client.complete([{'role': 'user', 'content': 'hello'}])
    assert len(calls) == 1


def test_budget_blocks_request_before_network(tmp_path):
    client = MeteredOpenRouter(tmp_path, 'secret', 'openai/gpt-4.1', study='test', study_cap=.00001,
                               transport=lambda _: pytest.fail('must not call network'))
    with pytest.raises(RuntimeError, match='budget'):
        client.complete([{'role': 'user', 'content': 'hello'}])
