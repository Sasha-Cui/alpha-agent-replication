"""Preserve full long parameters without killing old MLflow's async logger."""

import hashlib
from pathlib import Path
from alpha_evolve.openrouter_budget import atomic_json


def install_long_parameter_logging(recorder_class, output):
    output = Path(output)
    destination = output / "mlflow_parameter_overflow.json"
    native = recorder_class.log_params
    recorded = {}

    def log_params(self, **kwargs):
        safe = dict(kwargs)
        for name, value in kwargs.items():
            rendered = str(value)
            encoded = rendered.encode("utf8")
            if len(encoded) > 900:
                digest = hashlib.sha256(encoded).hexdigest()
                entry = {"full_original_log_value": rendered, "utf8_bytes": len(encoded), "sha256": digest}
                if name in recorded and recorded[name] != entry:
                    raise ValueError("A logged scientific parameter changed within one experiment")
                recorded[name] = entry
                safe[name] = f"Full value: mlflow_parameter_overflow.json; sha256={digest}; utf8_bytes={len(encoded)}"
        if recorded:
            atomic_json(
                destination,
                {
                    "scope": "Metadata-only size adapter. Original parameter strings are preserved in full; model/data/configuration objects are not modified.",
                    "parameters": recorded,
                },
            )
        return native(self, **safe)

    recorder_class.log_params = log_params
