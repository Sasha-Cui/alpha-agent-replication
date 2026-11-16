import hashlib
import json
from alpha_evolve.fidelity_qlib_logging_v2 import install_long_parameter_logging


def test_full_long_metadata_retained_without_mutating_model_configuration(tmp_path):
    calls = []

    class Recorder:
        def log_params(self, **kwargs):
            calls.append(kwargs)

    configuration = {"features": ["$close / Ref($close, 1)"] * 158, "num_threads": 20}
    original_features = list(configuration["features"])
    install_long_parameter_logging(Recorder, tmp_path)
    Recorder().log_params(**configuration)
    assert configuration["features"] == original_features
    assert calls[0]["num_threads"] == 20
    assert len(calls[0]["features"].encode("utf8")) < 1000
    saved = json.loads((tmp_path / "mlflow_parameter_overflow.json").read_text())["parameters"]["features"]
    assert saved["full_original_log_value"] == str(original_features)
    assert saved["sha256"] == hashlib.sha256(str(original_features).encode()).hexdigest()


def test_unicode_limit_and_inconsistent_relogging(tmp_path):
    import pytest

    calls = []

    class Recorder:
        def log_params(self, **kwargs):
            calls.append(kwargs)

    install_long_parameter_logging(Recorder, tmp_path)
    r = Recorder()
    r.log_params(feature="因子" * 300)
    assert len(calls[0]["feature"].encode()) < 1000
    with pytest.raises(ValueError, match="changed within one experiment"):
        r.log_params(feature="信号" * 300)
