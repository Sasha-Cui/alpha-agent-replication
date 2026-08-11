#!/usr/bin/env python3
"""Run released FinRL-DeepSeek checkpoints on released trade CSVs.

The paper audit consumes this driver's hash-validated outputs. It uses the
authors' environment modules unchanged and provides only the tiny
Gymnasium/SB3 import surface those modules require.
"""
from __future__ import annotations

import argparse
import importlib
import json
import sys
import types
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.distributions.normal import Normal


def install_import_stubs() -> type:
    gym = types.ModuleType("gymnasium")
    spaces = types.ModuleType("gymnasium.spaces")
    utils = types.ModuleType("gymnasium.utils")
    seeding = types.ModuleType("gymnasium.utils.seeding")

    class Env:
        pass

    class Box:
        def __init__(self, low, high, shape):
            self.low = low
            self.high = high
            self.shape = tuple(shape)

    class Discrete:
        def __init__(self, n):
            self.n = n

    def np_random(seed=None):
        return np.random.default_rng(seed), seed

    gym.Env = Env
    gym.spaces = spaces
    spaces.Box = Box
    spaces.Discrete = Discrete
    utils.seeding = seeding
    seeding.np_random = np_random

    sb3 = types.ModuleType("stable_baselines3")
    common = types.ModuleType("stable_baselines3.common")
    vec_env = types.ModuleType("stable_baselines3.common.vec_env")

    class DummyVecEnv:
        def __init__(self, env_fns):
            self.envs = [f() for f in env_fns]

        def reset(self):
            return np.asarray([self.envs[0].reset()[0]])

    vec_env.DummyVecEnv = DummyVecEnv
    sys.modules.update(
        {
            "gymnasium": gym,
            "gymnasium.spaces": spaces,
            "gymnasium.utils": utils,
            "gymnasium.utils.seeding": seeding,
            "stable_baselines3": sb3,
            "stable_baselines3.common": common,
            "stable_baselines3.common.vec_env": vec_env,
        }
    )
    return Box


BOX = install_import_stubs()


def mlp(sizes, activation, output_activation=nn.Identity):
    layers = []
    for j in range(len(sizes) - 1):
        act = activation if j < len(sizes) - 2 else output_activation
        layers += [nn.Linear(sizes[j], sizes[j + 1]), act()]
    return nn.Sequential(*layers)


class MLPGaussianActor(nn.Module):
    def __init__(self, obs_dim, act_dim, hidden_sizes, activation):
        super().__init__()
        self.log_std = nn.Parameter(torch.as_tensor(-0.5 * np.ones(act_dim, dtype=np.float32)))
        self.mu_net = mlp([obs_dim] + list(hidden_sizes) + [act_dim], activation)

    def distribution(self, obs):
        return Normal(self.mu_net(obs), torch.exp(self.log_std))


class MLPCritic(nn.Module):
    def __init__(self, obs_dim, hidden_sizes, activation):
        super().__init__()
        self.v_net = mlp([obs_dim] + list(hidden_sizes) + [1], activation)

    def forward(self, obs):
        return torch.squeeze(self.v_net(obs), -1)


class MLPActorCritic(nn.Module):
    def __init__(self, observation_space, action_space, hidden_sizes=(64, 64), activation=nn.Tanh):
        super().__init__()
        self.pi = MLPGaussianActor(
            observation_space.shape[0], action_space.shape[0], hidden_sizes, activation
        )
        self.v = MLPCritic(observation_space.shape[0], hidden_sizes, activation)

    def step(self, obs, stochastic=True):
        with torch.no_grad():
            pi = self.pi.distribution(obs)
            action = pi.sample() if stochastic else pi.mean
            value = self.v(obs)
            log_prob = pi.log_prob(action).sum(axis=-1)
        return action.numpy(), value.numpy(), log_prob.numpy()


INDICATORS = [
    "macd",
    "boll_ub",
    "boll_lb",
    "rsi_30",
    "cci_30",
    "dx_30",
    "close_30_sma",
    "close_60_sma",
]


def load_trade(path: Path, llm: str):
    df = pd.read_csv(path).drop(columns=["Unnamed: 0"])
    dates = df["date"].unique()
    df["new_idx"] = df["date"].map({date: i for i, date in enumerate(dates)})
    df = df.set_index("new_idx")
    if llm in {"sentiment", "risk"}:
        df["llm_sentiment"] = df["llm_sentiment"].fillna(0)
    if llm == "risk":
        df["llm_risk"] = df["llm_risk"].fillna(3)
    return df


def make_env(cls, df, extra_features):
    n = df.tic.nunique()
    return cls(
        df=df,
        stock_dim=n,
        hmax=100,
        initial_amount=1_000_000,
        num_stock_shares=[0] * n,
        buy_cost_pct=[0.001] * n,
        sell_cost_pct=[0.001] * n,
        reward_scaling=1e-4,
        state_space=1 + 2 * n + (len(INDICATORS) + extra_features) * n,
        action_space=n,
        tech_indicator_list=INDICATORS,
        turbulence_threshold=70,
        risk_indicator_col="vix",
        print_verbosity=10_000,
    )


def predict(model, environment, stochastic):
    state, _ = environment.reset()
    with torch.no_grad():
        for _ in range(len(environment.df.index.unique())):
            tensor = torch.as_tensor((state,), dtype=torch.float32)
            action = model.step(tensor, stochastic=stochastic)[0][0]
            state, _, done, _, _ = environment.step(action)
            if done:
                break
    return np.asarray(environment.asset_memory, dtype=float)


def tail_metrics(assets):
    normalized = pd.Series(assets[1:] / assets[1] * 1_000_000)
    returns = normalized.pct_change().dropna()
    lower = np.percentile(returns, 5)
    upper = np.percentile(returns, 95)
    cvar = returns[returns <= lower].mean()
    rachev = returns[returns >= upper].mean() / abs(returns[returns <= lower].mean())
    return {
        "n_assets": int(len(assets)),
        "n_returns": int(len(returns)),
        "initial_asset": float(assets[0]),
        "final_asset": float(assets[-1]),
        "cvar": float(cvar),
        "rachev_ratio": float(rachev),
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--artifacts", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--deterministic", action="store_true")
    args = p.parse_args()
    sys.path.insert(0, str(args.source))

    base_df = load_trade(args.artifacts / "data/trade_data_2019_2023.csv", "base")
    sent_df = load_trade(args.artifacts / "data/trade_data_deepseek_sentiment_2019_2023.csv", "sentiment")
    risk_df = load_trade(args.artifacts / "data/trade_data_deepseek_risk_2019_2023.csv", "risk")
    specs = [
        ("PPO", "env_stocktrading", base_df, 0, "agent_ppo_100_epochs_20k_steps.pth"),
        ("CPPO", "env_stocktrading", base_df, 0, "agent_cppo_100_epochs_20k_steps.pth"),
        ("PPO-DeepSeek 10%", "env_stocktrading_llm", sent_df, 1, "agent_ppo_deepseek_100_epochs_20k_steps.pth"),
        ("PPO-DeepSeek 1%", "env_stocktrading_llm_1", sent_df, 1, "agent_ppo_deepseek_100_epochs_20k_steps_1.pth"),
        ("PPO-DeepSeek 0.1%", "env_stocktrading_llm_01", sent_df, 1, "agent_ppo_deepseek_100_epochs_20k_steps_01.pth"),
        ("CPPO-DeepSeek 10%", "env_stocktrading_llm_risk", risk_df, 2, "agent_cppo_deepseek_100_epochs_20k_steps.pth"),
        ("CPPO-DeepSeek 1%", "env_stocktrading_llm_risk_1", risk_df, 2, "agent_cppo_deepseek_100_epochs_20k_steps_1.pth"),
        ("CPPO-DeepSeek 0.1%", "env_stocktrading_llm_risk_01", risk_df, 2, "agent_cppo_deepseek_100_epochs_20k_steps_01.pth"),
    ]
    torch.manual_seed(args.seed)
    results = {}
    for label, module_name, df, extra, checkpoint in specs:
        cls = importlib.import_module(module_name).StockTradingEnv
        env = make_env(cls, df, extra)
        model = MLPActorCritic(env.observation_space, env.action_space, hidden_sizes=(512, 512))
        model.load_state_dict(
            torch.load(args.artifacts / "agents" / checkpoint, map_location="cpu", weights_only=True)
        )
        model.eval()
        assets = predict(model, env, stochastic=not args.deterministic)
        metrics = tail_metrics(assets)
        metrics.update({"checkpoint": checkpoint, "environment_module": module_name})
        results[label] = metrics
        print(label, json.dumps(metrics, sort_keys=True), flush=True)
    payload = {
        "seed": args.seed,
        "action_mode": "mean" if args.deterministic else "sample",
        "source_revision": "5c21a923214bca6370800efd45f8c6c1ef776ae7",
        "results": results,
    }
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
