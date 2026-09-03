#!/usr/bin/env python3
"""Audit whether CryptoTrade LSTM decisions depend on prices after decision time.

The caller census replaces model calls with a no-trade sentinel solely to inspect
call arguments; it is not a portfolio replay. The counterexamples execute the
unaltered LSTM function (CPU substitution only) for fixed seed 0, look-back 5,
and 100 epochs, changing only a later price. No counterexample earns result credit.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
from contextlib import redirect_stdout

import run_cryptotrade_lstm_probe as native


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def load_namespace(source):
    # Match only the already disclosed import/device/constructor adaptations.
    text = (source / "run_baseline.py").read_text(encoding="utf-8")
    text = text.split("strategy = 'optimal'", 1)[0]
    for old, new in (
        ("device = 'cuda:7'", "device = 'cpu'"),
        ("import matplotlib.pyplot as plt\n", ""),
        ("Namespace(starting_date=sargs['starting_date'], ending_date=sargs['ending_date'])",
         "Namespace(starting_date=sargs['starting_date'], ending_date=sargs['ending_date'], dataset='eth')"),
    ):
        if text.count(old) != 1:
            raise ValueError(f"Source adaptation anchor changed: {old}")
        text = text.replace(old, new)
    sys.path.insert(0, str(source))
    namespace = {"__name__": "cryptotrade_temporal_audit"}
    with redirect_stdout(io.StringIO()):
        exec(compile(text, "run_baseline.py", "exec"), namespace)
    return namespace


def digest_array(array):
    import numpy as np
    array = np.ascontiguousarray(array, dtype="<f8")
    header = json.dumps(list(array.shape)).encode() + b"\n"
    return hashlib.sha256(header + array.tobytes()).hexdigest()


def worker(source, output):
    import numpy as np
    import pandas as pd
    import torch

    native.validate_source(source)
    connections = []
    original_connect = socket.socket.connect

    def deny_network(sock, address):
        if sock.family in (socket.AF_INET, socket.AF_INET6):
            connections.append(repr(address))
            raise OSError("network disabled by CryptoTrade temporality audit")
        return original_connect(sock, address)

    socket.socket.connect = deny_network
    namespace = load_namespace(source)
    original_lstm = namespace["lstm_strategy"]
    census = []
    for regime, (start, end) in native.PAPER_PERIODS.items():
        selected = namespace["df"].loc[
            (namespace["df"]["date"] >= start) & (namespace["df"]["date"] <= end)
        ]
        dates = selected["date"].reset_index(drop=True)

        def inspect_call(df, start_date, end_date, look_back=5):
            caller = sys._getframe(1)
            if caller.f_code.co_name != "run_strategy":
                raise AssertionError("unexpected LSTM caller")
            decision_date = caller.f_locals["date"]
            data = df.loc[(df["date"] >= start_date) & (df["date"] <= end_date)]
            used_dates = data["date"].reset_index(drop=True)
            if list(used_dates) != list(dates):
                raise AssertionError("caller did not pass the entire fixed regime")
            census.append({
                "regime": regime,
                "decision_date": str(decision_date.date()),
                "decision_price": float(caller.f_locals["open_price"]),
                "passed_start": start_date,
                "passed_end": end_date,
                "lookback": look_back,
                "scaler_rows": len(data),
                "future_scaler_rows": int((used_dates > decision_date).sum()),
                "future_supervised_target_rows": int((used_dates.iloc[look_back:] > decision_date).sum()),
                "future_inference_rows": int((used_dates.iloc[-look_back:] > decision_date).sum()),
                "comparison_price_date": str(used_dates.iloc[-1].date()),
                "inference_window_end": str(used_dates.iloc[-1].date()),
                "tomorrow_relative_to_decision": str((decision_date + pd.Timedelta(days=1)).date()),
                "model_nominal_forecast_date": str((used_dates.iloc[-1] + pd.Timedelta(days=1)).date()),
                "temporally_valid": False,
                "census_only_no_model_or_portfolio_result": True,
            })
            return "Hold"

        namespace["lstm_strategy"] = inspect_call
        before = len(census)
        with redirect_stdout(io.StringIO()):
            namespace["run_strategy"]("LSTM", {"starting_date": start, "ending_date": end})
        if [row["decision_date"] for row in census[before:]] != [str(d.date()) for d in dates.iloc[:-1]]:
            raise AssertionError("native decision calendar differs from price calendar")
    namespace["lstm_strategy"] = original_lstm

    probes = []
    for regime, (start, end) in native.PAPER_PERIODS.items():
        original = namespace["df"]
        for scenario, multiplier, outside in (
            ("original", 1.0, False),
            ("terminal_price_doubled", 2.0, False),
            ("terminal_price_halved", 0.5, False),
            ("post_regime_price_doubled_control", 2.0, True),
        ):
            changed_date = pd.Timestamp(end) + pd.Timedelta(days=int(outside))
            altered = original.copy(deep=True)
            mask = altered["date"].dt.strftime("%Y-%m-%d") == str(changed_date.date())
            if int(mask.sum()) != 1:
                raise AssertionError("counterexample must address exactly one row")
            altered.loc[mask, "open"] *= multiplier
            prefix_mask = original["date"] <= start
            pd.testing.assert_frame_equal(original.loc[prefix_mask], altered.loc[prefix_mask])
            for repeat in range(2):
                torch.manual_seed(0)
                np.random.seed(0)
                captured = {}

                def profile(frame, event, arg):
                    if event == "return" and frame.f_code is original_lstm.__code__:
                        values = frame.f_locals
                        captured.update({
                            "action": arg,
                            "comparison_price": round(float(values["current_price"].item()), 8),
                            "predicted_price": round(float(values["next_day_prediction"].item()), 8),
                            "scaler_min": float(values["scaler"].data_min_.item()),
                            "scaler_max": float(values["scaler"].data_max_.item()),
                            "supervised_target_count": int(values["Y"].shape[0]),
                            "train_X_sha256": digest_array(values["X"].cpu().numpy()),
                            "train_Y_sha256": digest_array(values["Y"].cpu().numpy()),
                            "inference_X_sha256": digest_array(values["last_sequence"].cpu().numpy()),
                        })

                previous_profile = sys.getprofile()
                sys.setprofile(profile)
                try:
                    with redirect_stdout(io.StringIO()):
                        original_lstm(altered, start, end, look_back=5)
                finally:
                    sys.setprofile(previous_profile)
                if not captured:
                    raise AssertionError("native LSTM return was not observed")
                probes.append({
                    "regime": regime, "scenario": scenario, "repeat": repeat,
                    "seed": 0, "lookback": 5, "epochs": 100,
                    "decision_date": start, "changed_date": str(changed_date.date()),
                    "decision_price": float(original.loc[original["date"].dt.strftime("%Y-%m-%d") == start, "open"].iloc[0]),
                    "original_terminal_price": float(original.loc[original["date"].dt.strftime("%Y-%m-%d") == end, "open"].iloc[0]),
                    "past_and_present_unchanged": True,
                    "changed_row_strictly_after_decision": changed_date > pd.Timestamp(start),
                    "paper_result_credit": False, **captured,
                })
    if connections:
        raise AssertionError(f"network attempted: {connections}")
    output.write_text(json.dumps({"census": census, "probes": probes}, indent=2) + "\n")


def summarize(census, probes):
    counts = {r: sum(x["regime"] == r for x in census) for r in native.PAPER_PERIODS}
    if counts != {"bear": 65, "sideways": 72, "bull": 61}:
        raise AssertionError(counts)
    if not all(x["future_supervised_target_rows"] > 0 and x["future_inference_rows"] > 0 for x in census):
        raise AssertionError("expected future input paths changed")
    if len(probes) != 24:
        raise AssertionError("counterexample census incomplete")
    repeats = {}
    for row in probes:
        repeats.setdefault((row["regime"], row["scenario"]), []).append(row)
    firsts = {}
    for key, values in repeats.items():
        a, b = ({k: v for k, v in x.items() if k != "repeat"} for x in values)
        if a != b:
            raise AssertionError(f"non-repeatable temporal probe {key}")
        firsts[key] = values[0]
    flips = []
    for regime in native.PAPER_PERIODS:
        original = firsts[(regime, "original")]
        control = firsts[(regime, "post_regime_price_doubled_control")]
        for key in ("action", "comparison_price", "predicted_price", "scaler_min", "scaler_max", "train_X_sha256", "train_Y_sha256", "inference_X_sha256"):
            if original[key] != control[key]:
                raise AssertionError(f"post-regime control failed: {regime}/{key}")
        for scenario in ("terminal_price_doubled", "terminal_price_halved"):
            changed = firsts[(regime, scenario)]
            if original["train_Y_sha256"] == changed["train_Y_sha256"]:
                raise AssertionError("future perturbation did not change training targets")
            if original["action"] != changed["action"]:
                flips.append({"regime": regime, "scenario": scenario, "original_action": original["action"], "changed_action": changed["action"]})
    if not flips:
        raise AssertionError("no observed future-only action counterexample")
    return {
        "source_commit": native.SOURCE_COMMIT,
        "source_sha256": native.SOURCE_HASHES,
        "paper_url": "https://aclanthology.org/2024.emnlp-main.63.pdf",
        "paper_sha256": "376606b05f5398c9200b0a560690693ea0a023a97631175ae02528e4dffec5cf",
        "paper_baseline_locator": "Appendix E, item 6, printed page 1105 (PDF page 12)",
        "paper_decision_rule": "today price compared with forecast for tomorrow",
        "decision_count": len(census), "regime_decision_counts": counts,
        "decisions_with_future_training_targets": sum(x["future_supervised_target_rows"] > 0 for x in census),
        "decisions_with_future_inference_inputs": sum(x["future_inference_rows"] > 0 for x in census),
        "comparison_uses_terminal_not_decision_date": all(x["comparison_price_date"] > x["decision_date"] for x in census),
        "native_training_calls": len(probes), "exact_repeat_pairs": len(repeats),
        "post_regime_negative_controls_passed": 3, "future_only_action_flips": flips,
        "caller_census_uses_hold_sentinel_no_training_or_portfolio_credit": True,
        "counterexamples_execute_native_lstm": True,
        "compatible_environment": native.COMPATIBLE_ENVIRONMENT,
        "source_files_modified": False, "paper_result_credit": False,
        "interpretation": "Seed/lookback-stable numbers reproduce an anticipative source path, not the paper's daily predictive trading procedure. Retain numeric correspondences, withhold faithful LSTM result credit.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--python-wrapper", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--worker", action="store_true")
    args = parser.parse_args()
    if args.worker:
        worker(args.source, args.output)
        return
    if args.python_wrapper is None:
        parser.error("--python-wrapper is required")
    native.validate_source(args.source)
    native.environment_snapshot(args.python_wrapper.absolute())
    with tempfile.TemporaryDirectory(prefix="cryptotrade-temporal-") as tmp:
        result_file = Path(tmp) / "worker.json"
        result = subprocess.run(
            [str(args.python_wrapper.absolute()), str(Path(__file__).absolute()), "--worker", "--source", str(args.source), "--output", str(result_file)],
            cwd=args.source, env=native.clean_environment(), capture_output=True, text=True,
        )
        if result.returncode:
            raise RuntimeError(result.stderr[-8000:])
        result = json.loads(result_file.read_text())
    summary = summarize(result["census"], result["probes"])
    args.output.mkdir(parents=True, exist_ok=True)
    write_csv(args.output / "lstm_decision_time_audit.csv", result["census"])
    write_csv(args.output / "lstm_future_price_counterexamples.csv", result["probes"])
    (args.output / "lstm_temporality.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
