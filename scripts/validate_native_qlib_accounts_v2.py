#!/usr/bin/env python3
# ruff: noqa: E402 - central source bootstrap
"""Independent native cash, positions, fills, fee rules and reported metric checks."""

from pathlib import Path
import argparse
import sys
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from alpha_evolve.openrouter_budget import atomic_json, sha256


def series(data, metric):
    raw = data.data[metric]
    return pd.Series(raw.data, index=pd.Index(raw.index.tolist()), dtype=float)


def validate(workspace, config_name="conf_cn_combined.yaml"):
    report = pd.read_pickle(workspace / "ret.pkl")
    paths = list(workspace.glob("mlruns/*/*/artifacts/portfolio_analysis/positions_normal_1day.pkl"))
    if len(paths) != 1:
        raise ValueError("Native recorder identity is ambiguous")
    positions = pd.read_pickle(paths[0])
    indicators = pd.read_pickle(paths[0].with_name("indicators_normal_1day_obj.pkl"))
    import yaml

    config = yaml.safe_load((workspace / config_name).read_text())
    backtest = config["port_analysis_config"]["backtest"]
    initial = float(backtest["account"])
    exchange = backtest["exchange_kwargs"]
    if exchange["deal_price"] != "open":
        raise ValueError("Unexpected native fill clock")
    if report.index.has_duplicates or not report.index.is_monotonic_increasing:
        raise ValueError("Invalid native calendar")
    if not np.isfinite(report.to_numpy()).all():
        raise ValueError("Nonfinite account report")
    previous_nav = previous_cash = initial
    previous_amounts = {}
    previous_cost = previous_turnover = 0.0
    errors = {
        key: 0.0
        for key in [
            "nav_components",
            "net_return",
            "fee_increment",
            "turnover_increment",
            "position_value",
            "position_cash",
            "fill_value",
            "fee_rule",
            "fill_cost_total",
            "fill_turnover_total",
            "cash_conservation",
            "share_conservation",
        ]
    }
    trade_rows = []
    for date, row in report.iterrows():

        def check(key, actual, expected, scale=1):
            difference = abs(float(actual) - float(expected)) / max(1.0, float(scale))
            errors[key] = max(errors[key], difference)
            if difference > 1e-10:
                raise ValueError(f"{date} {key} inconsistent: {difference}")

        nav = float(row.account)
        if nav <= 0 or row.cash < -1e-10 * initial:
            raise ValueError("Nonpositive NAV or material borrowing")
        fee_increment = float(row.total_cost) - previous_cost
        notional_increment = float(row.total_turnover) - previous_turnover
        check("nav_components", nav, row.cash + row.value, nav)
        check("net_return", nav / previous_nav - 1, row["return"] - row.cost)
        check("fee_increment", fee_increment / previous_nav, row.cost)
        check("turnover_increment", notional_increment / previous_nav, row.turnover)
        position = positions[date]
        amounts = {stock: float(position.get_stock_amount(stock)) for stock in position.get_stock_list()}
        if any(value < -1e-10 for value in amounts.values()):
            raise ValueError("Unexpected short position")
        value = sum(amounts[stock] * float(position.get_stock_price(stock)) for stock in amounts)
        check("position_value", value, row.value, nav)
        check("position_cash", position.get_cash(), row.cash, nav)
        indicator = indicators.order_indicator_his[date]
        signed_notional = traded = fees = 0.0
        quantity_delta = {}
        if indicator.data:
            table = pd.concat(
                {
                    name: series(indicator, name)
                    for name in ["deal_amount", "trade_price", "trade_value", "trade_cost", "trade_dir"]
                },
                axis=1,
            )
            for stock, fill in table.iterrows():
                if fill.deal_amount == 0:
                    if fill.trade_cost != 0:
                        raise ValueError("Fee on an unfilled order")
                    continue
                if not np.isfinite(fill.to_numpy()).all() or fill.trade_price <= 0 or fill.trade_dir not in [0, 1]:
                    raise ValueError("Invalid fill")
                sign = 1 if fill.trade_dir == 1 else -1
                if float(fill.deal_amount) * sign < 0:
                    raise ValueError("Signed fill quantity disagrees with its direction")
                amount = abs(float(fill.deal_amount))
                notional = amount * float(fill.trade_price)
                rate = exchange["open_cost"] if fill.trade_dir == 1 else exchange["close_cost"]
                expected_fee = max(float(exchange["min_cost"]), notional * float(rate))
                check("fill_value", fill.trade_value, sign * notional, previous_nav)
                check("fee_rule", fill.trade_cost, expected_fee, previous_nav)
                sign = 1 if fill.trade_dir == 1 else -1
                signed_notional += sign * notional
                traded += notional
                fees += float(fill.trade_cost)
                quantity_delta[stock] = quantity_delta.get(stock, 0) + sign * amount
                trade_rows.append(
                    {
                        "date": date,
                        "instrument": stock,
                        "amount": amount,
                        "price": float(fill.trade_price),
                        "direction": int(fill.trade_dir),
                        "notional": notional,
                        "fee": float(fill.trade_cost),
                    }
                )
        check("fill_cost_total", fees, fee_increment, previous_nav)
        check("fill_turnover_total", traded, notional_increment, previous_nav)
        check("cash_conservation", previous_cash - signed_notional - fees, row.cash, previous_nav)
        for stock in set(previous_amounts) | set(amounts) | set(quantity_delta):
            expected = previous_amounts.get(stock, 0) + quantity_delta.get(stock, 0)
            check(
                "share_conservation",
                amounts.get(stock, 0),
                expected,
                max(abs(expected), abs(previous_amounts.get(stock, 0)), 1),
            )
        previous_nav = nav
        previous_cash = float(row.cash)
        previous_amounts = amounts
        previous_cost = float(row.total_cost)
        previous_turnover = float(row.total_turnover)
    metrics = pd.read_csv(workspace / "qlib_res.csv", index_col=0).iloc[:, 0]
    metric_errors = {}
    for label, values in [
        ("without_cost", report["return"] - report.bench),
        ("with_cost", report["return"] - report.cost - report.bench),
    ]:
        mean = float(values.mean())
        std = float(values.std(ddof=1))
        cum = values.cumsum()
        calculated = {
            "mean": mean,
            "std": std,
            "annualized_return": mean * 238,
            "information_ratio": mean / std * np.sqrt(238),
            "max_drawdown": float((cum - cum.cummax()).min()),
        }
        for key, value in calculated.items():
            native = float(metrics["1day.excess_return_" + label + "." + key])
            error = abs(native - value)
            metric_errors[label + "." + key] = error
            if error > 1e-10:
                raise ValueError("Native excess metric mismatch: " + label + "." + key)
    return (
        report,
        pd.DataFrame(trade_rows),
        {
            "status": "pass",
            "days": len(report),
            "filled_orders": len(trade_rows),
            "maximum_normalized_errors": errors,
            "native_metric_errors": metric_errors,
            "native_metric_convention": "238-day linear annualized excess return, sample-standard-deviation IR and additive excess-curve drawdown. These are not portfolio CAGR or wealth drawdown.",
            "initial_capital": initial,
            "exchange": exchange,
            "report_sha256": sha256(workspace / "ret.pkl"),
            "positions_sha256": sha256(paths[0]),
            "orders_sha256": sha256(paths[0].with_name("indicators_normal_1day_obj.pkl")),
        },
    )


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--run-name", required=True)
    args = p.parse_args()
    run = ROOT / "artifacts/fidelity_completion_v2" / args.run_name
    manifest = json.loads((run / "used_factor_manifest.json").read_text())
    out = run / "independent_accounts"
    out.mkdir(exist_ok=True)
    proofs = []
    for row in manifest["experiments"]:
        workspace = Path(row["workspace"])
        report, fills, proof = validate(workspace, row.get("native_config", "conf_cn_combined.yaml"))
        report.to_csv(out / f"experiment_{row['index']}_account.csv", index_label="date")
        fills.to_csv(out / f"experiment_{row['index']}_fills.csv", index=False)
        proof["experiment_index"] = row["index"]
        proofs.append(proof)
        print("NATIVE_ACCOUNT_PASS", args.run_name, row["index"], proof["days"], proof["filled_orders"], flush=True)
    atomic_json(
        out / "validation.json",
        {
            "status": "pass",
            "experiments": proofs,
            "script_sha256": sha256(Path(__file__)),
            "scope": "Independent accounting from saved fills/positions and native fee rules. No model call, new-period evaluation, data equivalence or full-paper reproduction claim.",
        },
    )


if __name__ == "__main__":
    main()
