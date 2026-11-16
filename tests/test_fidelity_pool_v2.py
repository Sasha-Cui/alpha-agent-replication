import hashlib
import pytest
from alpha_evolve.fidelity_pool_v2 import merge_discoveries, eligible_discoveries


def row(code, day, origin='llm_generated'):
    return {hashlib.sha256(code.encode()).hexdigest(): {'code':code,'name':'x','origin':origin,'created_index':day}}


def test_future_discovery_is_unavailable_until_its_decision_close():
    old = row('seed',-1,'paper_seed_family')
    future = row('future',7)
    merged = merge_discoveries({'a':{**old,**future}})
    assert set(eligible_discoveries(merged,6)) == set(old)
    assert set(eligible_discoveries(merged,7)) == set(old)|set(future)
    assert set(eligible_discoveries(merged,6,hindsight=True)) == set(merged)


def test_duplicate_discoveries_use_earliest_causal_availability():
    merged = merge_discoveries({'a':row('x',9),'b':row('x',3)})
    value = next(iter(merged.values()))
    assert value['created_index'] == 3
    assert len(value['discoveries']) == 2
    assert not eligible_discoveries(merged,2)
    assert eligible_discoveries(merged,3)


def test_changed_code_or_missing_date_fails():
    bad = row('x',3)
    next(iter(bad.values()))['code'] = 'y'
    with pytest.raises(ValueError):
        merge_discoveries({'a':bad})
    with pytest.raises(ValueError):
        merge_discoveries({'a':row('x',-1)})
