#!/usr/bin/env python3
"""Source-motivated daily equal-weight reference for the completed EFS pilot.

Added after inspection of the pilot; descriptive context, not a new confirmatory
contrast. Uses the identical observed-history eligibility and close execution.
"""
from __future__ import annotations
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd

from alpha_evolve.economic_fidelity import daily_account, monthly_compound
from alpha_evolve.openrouter_budget import sha256

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'paper_runs/economic_fidelity/efs_v1'
PRIVATE = ROOT/'artifacts/economic_fidelity/v1'


def main():
    frame = pd.read_parquet(PRIVATE/'efs_us50_daily.parquet')
    prices = frame.pivot(index='date', columns='ticker', values='adjusted_close').sort_index().sort_index(axis=1)
    dates = pd.DatetimeIndex(pd.read_csv(OUT/'llm_daily_returns.csv').date)
    locations = prices.index.get_indexer(dates)
    targets = []
    for index in locations:
        history = prices.iloc[index-30:index].to_numpy()
        if history.shape[0] != 30:
            raise ValueError('missing past-only formation history')
        eligible = np.isfinite(history).all(axis=0) & (history>0).all(axis=0)
        weights = eligible.astype(float)/eligible.sum()
        if not np.isfinite(prices.iloc[index].to_numpy()[weights>0]).all():
            raise ValueError('missing selected execution price')
        targets.append(weights)
    targets = np.array(targets)
    price_returns = (prices/prices.shift(1)-1).reindex(dates).to_numpy()
    total_returns = frame.pivot(index='date',columns='ticker',values='ret').reindex(index=dates,columns=prices.columns).to_numpy()
    spec = importlib.util.spec_from_file_location('independent_efs_account',ROOT/'scripts/validate_efs_economic_fidelity.py')
    independent = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(independent)
    daily = pd.DataFrame({'date':dates})
    monthly, metrics, errors = None, [], {}
    for label, r in [('price',price_returns),('total',total_returns)]:
        for cost in (0,10):
            name = f'{label}_cost_{cost}'
            values,turn,fees = daily_account(targets,r,cost)
            verification = independent.independent_account(targets,r,cost/10000)
            error = float(np.max(np.abs(values-verification)))
            if error>1e-11:
                raise ValueError('independent account mismatch')
            errors[name] = error
            daily[name] = values
            daily[name+'_traded_notional'] = turn
            daily[name+'_fee_drag'] = fees
            months = monthly_compound(dates,values)
            if monthly is None:
                monthly = pd.DataFrame({'month':months.index.to_timestamp('M')})
            monthly[name] = months.to_numpy()
            wealth = np.cumprod(1+values)
            metrics.append({'case':name,'days':len(values),'months':len(months),
                'cagr':float(wealth[-1]**(252/len(values))-1),
                'sharpe_zero_rf':float(values.mean()/values.std(ddof=1)*np.sqrt(252)),
                'max_drawdown':float(np.min(wealth/np.maximum.accumulate(np.r_[1.,wealth])[1:]-1)),
                'ending_wealth':float(wealth[-1]),'mean_one_way_traded_notional':float(turn.mean())})
    daily.to_csv(OUT/'equal_weight_daily_returns.csv',index=False)
    monthly.to_csv(OUT/'equal_weight_monthly_returns.csv',index=False)
    pd.DataFrame(metrics).to_csv(OUT/'equal_weight_metrics.csv',index=False)
    private = PRIVATE/'equal_weight_daily_weights.parquet'
    pd.DataFrame(targets,index=dates,columns=prices.columns).to_parquet(private)
    manifest = {'status':'complete','scope':'source-motivated descriptive reference, added after pilot inspection',
        'portfolio':'daily equal weight across stocks with thirty complete prior positive closes; execute at following close',
        'same_calendar_as_llm':True,'new_model_calls':0,'confirmatory_contrast':False,
        'independent_account_max_errors':errors,'implementation_sha256':sha256(Path(__file__)),
        'input_sha256':sha256(PRIVATE/'efs_us50_daily.parquet'),'private_weights_sha256':sha256(private),
        'output_sha256':{p.name:sha256(p) for p in OUT.glob('equal_weight_*.csv')}}
    (OUT/'equal_weight_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(manifest,indent=2))


if __name__=='__main__':
    main()
