from __future__ import annotations

import pandas as pd

from alpha_evolve.in_spirit import p1gpt_layered_workflow_scores


DOMAINS = {
    "fundamental": [("be_me", 1), ("gp_at", 1), ("ocf_at", 1), ("f_score", 1), ("z_score", 1), ("qmj_prof", 1)],
    "technical": [("ret_12_1", 1), ("ret_6_1", 1), ("ret_1_0", 1), ("prc_highprc_252d", 1), ("rvol_21d", -1)],
    "semiconductor_cycle": [("saleq_su", 1), ("niq_su", 1), ("prc_highprc_252d", 1), ("turnover_126d", 1)],
    "news": [("niq_su", 1), ("saleq_su", 1), ("turnover_126d", 1), ("ret_1_0", 1)],
}
RISK = [("rvol_21d", -1), ("beta_60m", -1), ("z_score", 1), ("qmj_safety", 1)]


def fixture(months: int = 10, securities: int = 50) -> pd.DataFrame:
    import numpy as np

    rng = np.random.default_rng(149)
    dates = np.repeat(pd.date_range("2000-01-31", periods=months, freq="ME"), securities)
    ids = np.tile(np.arange(securities), months)
    frame = pd.DataFrame({"month": dates, "security_id": ids})
    features = list(
        dict.fromkeys(
            [feature for specifications in DOMAINS.values() for feature, _ in specifications]
            + [feature for feature, _ in RISK]
        )
    )
    for feature in features:
        frame[feature] = rng.normal(size=len(frame))
    frame["ret_exc_lead1m"] = rng.normal(scale=0.1, size=len(frame))
    return frame


def test_p1gpt_runs_five_layers_nine_agents_and_confidence_decision():
    frame = fixture()
    scores, history = p1gpt_layered_workflow_scores(frame, DOMAINS, RISK)
    assert scores.notna().all()
    assert history.layer_count.eq(5).all()
    assert history.agent_count.eq(9).all()
    assert history.domain_agent_count.eq(4).all()
    assert history.supporting_agent_count.eq(4).all()
    assert history.integrated_report_count.eq(7).all()
    assert history.mean_confidence.between(0.0, 1.0).all()
    assert (history.buy_count + history.hold_count + history.sell_count).eq(50).all()
    assert history.finite_scores.eq(50).all()


def test_p1gpt_is_deterministic_and_ignores_all_return_outcomes():
    frame = fixture()
    scores, history = p1gpt_layered_workflow_scores(frame, DOMAINS, RISK)
    changed = frame.copy()
    changed["ret_exc_lead1m"] *= -1000
    changed_scores, changed_history = p1gpt_layered_workflow_scores(changed, DOMAINS, RISK)
    pd.testing.assert_series_equal(scores, changed_scores)
    pd.testing.assert_frame_equal(history, changed_history)


def test_p1gpt_rejects_a_missing_domain_agent():
    frame = fixture()
    invalid = dict(DOMAINS)
    invalid.pop("news")
    try:
        p1gpt_layered_workflow_scores(frame, invalid, RISK)
    except ValueError as error:
        assert "four frozen domain agents" in str(error)
    else:
        raise AssertionError("incomplete P1GPT domain layer was accepted")
