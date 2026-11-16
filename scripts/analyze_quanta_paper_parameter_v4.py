#!/usr/bin/env python3
"""Separate exploratory Quanta paper-parameter comparison with explicit common baselines."""
from pathlib import Path
import sys,json
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from alpha_evolve.openrouter_budget import atomic_json,sha256
from alpha_evolve.publication_inference import grouped_t_effect
from analyze_native_oos_v2 import load_arm,core_settings,aligned_difference
from analyze_publication_upgrade import metrics
from native_secondary_evidence_v2 import validate_execution_identity
from quanta_paper_evaluation_evidence_v4 import SCOPE,protocol,validate_fixed
PRIVATE=ROOT/'artifacts/fidelity_completion_v2';PUBLIC=ROOT/'paper_runs/fidelity_completion_v2'
def load_variant_arm(run_name, case, arm, plumbing, *, secondary_unit=None):
    # YAML is supplied by the central Python3.12 analysis runtime. Pure
    # financial/configuration guards remain usable in the Python3.9 test env.
    import yaml

    run = PRIVATE / run_name
    completion = json.loads((run / "completion.json").read_text())
    recipe = json.loads((run / "execution_recipe.json").read_text())
    proof_path = run / "independent_accounts/validation.json"
    proof = json.loads(proof_path.read_text())
    if completion["case"] != case or completion["arm"] != arm:
        raise ValueError("Unexpected arm/case identity")
    if completion["status"] != "native_new_period_run_complete_independent_validation_pending":
        raise ValueError("Native arm is incomplete")
    if proof["status"] != "pass" or proof["recipe_sha256"] != sha256(run / "execution_recipe.json"):
        raise ValueError("Independent accounting gate failed or changed")
    if any(obj["plumbing_search_period_only"] != plumbing for obj in [completion, recipe, proof]):
        raise ValueError("Search-period and later-period evidence cannot be mixed")
    for filename, key in [
        ("ret.pkl", "returns_sha256"),
        ("qlib_res.csv", "metrics_sha256"),
        ("oos_config.yaml", "config_sha256"),
    ]:
        if sha256(run / filename) != completion[key]:
            raise ValueError("Native completed artifact changed")
    account_path = run / "independent_accounts/account.csv"
    if sha256(account_path) != proof["account_csv_sha256"]:
        raise ValueError("Validated account export changed")
    frame = pd.read_csv(account_path, index_col="date", parse_dates=True)
    if frame.index.has_duplicates or not frame.index.is_monotonic_increasing:
        raise ValueError("Invalid account calendar")
    net = frame["return"] - frame["cost"]
    if not np.isfinite(net).all() or (net <= -1).any():
        raise ValueError("Invalid independently accounted net return")
    libraries = [
        path
        for path in PRIVATE.glob("*_fixed_library/library_manifest.json")
        if sha256(path) == recipe["library_manifest_sha256"]
    ]
    if not libraries:
        raise ValueError("Hash-pinned source library unavailable")
    library = json.loads(libraries[0].read_text())
    if plumbing or secondary_unit is not None or case!='quantaalpha' or arm not in ['source4_plus_library','alpha158_plus_library']:
        raise ValueError('Unplanned parameter sensitivity arm')
    library, source_evidence = validate_fixed(libraries[0], ROOT)
    embargo=recipe['embargo']
    provider=Path(json.loads((PRIVATE/'quantaalpha_data/manifest.json').read_text())['provider_path'])
    calendar=pd.DatetimeIndex(pd.to_datetime((provider/'calendars/day.txt').read_text().splitlines()))
    expected=calendar[(calendar>=pd.Timestamp(embargo['first_evaluation_execution_open'])) & (calendar<=pd.Timestamp('2025-12-26'))]
    if not frame.index.equals(expected):raise ValueError('Variant account calendar incomplete; never intersect')
    expected_features = (158 if arm.startswith("alpha158") else 4) + (
        library["distinct_expressions"] if arm.endswith("_plus_library") else 0
    )
    if any(row["features"] != expected_features or row["infinite_values"] for row in proof["processed_features"]):
        raise ValueError("Native processed feature count/finiteness differs from frozen intervention")
    config = yaml.safe_load((run / "oos_config.yaml").read_text())
    return net, {
        "run": run_name,
        "case": case,
        "arm": arm,
        "completion_sha256": sha256(run / "completion.json"),
        "account_validation_sha256": sha256(proof_path),
        "account_sha256": sha256(account_path),
        "recipe_sha256": sha256(run / "execution_recipe.json"),
        "library_manifest_sha256": recipe["library_manifest_sha256"],
        "core_settings": core_settings(config),
        "features": expected_features,
    }


def paired_exploratory(left,right):
    aligned_difference(left,right)
    result=grouped_t_effect(left.to_numpy(),right.to_numpy(),frequency=252,groups=4,threshold=.02,confidence=.99)
    result['within_margin_pointwise99']=result.pop('equivalent_within_margin_tost5')
    result['rules_out_positive_margin_pointwise99']=result.pop('rules_out_positive_margin_one_sided5')
    result.update(scope=SCOPE,project_family_significance_claim=False,original_primary_replaced=False,original54_family_complete=False,isolated_parameter_effect_claim=False)
    return result


def main():
    plan,pdigest=protocol(ROOT)
    library,source=validate_fixed(PRIVATE/'quantaalpha_paper_parameters_fixed_library/library_manifest.json',ROOT)
    original=json.loads((PRIVATE/'quantaalpha_bounded_fixed_library/library_manifest.json').read_text())
    for key in ['data_sha256','membership_sha256']:
        if library[key]!=original[key]:raise ValueError('Variant/baseline data or universe differs')
    out=PUBLIC/'quanta_paper_parameter_sensitivity'
    if out.exists():raise ValueError('Preserve existing sensitivity attempt')
    evidence=[];performance=[];comparisons=[];daily=[]
    for execution in ['native','opening_information']:
        suffix='' if execution=='native' else '_open_information'
        for baseline in ['source4','alpha158']:
            arm=baseline+'_plus_library';base_name=plan['common_baselines' if execution=='native' else 'opening_common_baselines'][baseline]
            source_name='quantaalpha_paper_parameters_oos_'+arm+suffix
            left,lp=load_variant_arm(source_name,'quantaalpha',arm,False)
            right,rp=load_arm(base_name,'quantaalpha',baseline,False)
            if lp['core_settings']!=rp['core_settings']:raise ValueError('Baseline/variant differs beyond feature intervention')
            for values,proof,name,role in [(left,lp,source_name,'variant_augmented'),(right,rp,base_name,'explicitly_reused_common_baseline')]:
                identity=validate_execution_identity(name,execution,PRIVATE)
                evidence.append({**proof,**identity,'execution':execution,'baseline':baseline,'role':role})
                performance.append({'execution':execution,'baseline':baseline,'role':role,'run':name,**metrics(values,frequency=252)})
                daily.append(values.rename('net_return').reset_index().assign(execution=execution,baseline=baseline,role=role,run=name))
            comparisons.append({'execution':execution,'baseline':baseline,'role':'opening_information_exploratory' if suffix else 'native_conformance_diagnostic',**paired_exploratory(left,right)})
    out.mkdir()
    for name,data in [('comparisons',comparisons),('performance',performance),('execution_evidence',evidence),('source_evidence',source)]:atomic_json(out/(name+'.json'),data)
    pd.concat(daily,ignore_index=True).to_csv(out/'daily_net_returns.csv',index=False)
    atomic_json(out/'completion.json',{'status':'separate_exploratory_parameter_sensitivity_complete_not_primary','scope':SCOPE,'protocol_sha256':pdigest,'source_files':{str(p.relative_to(ROOT)):sha256(p) for p in [Path(__file__),ROOT/'scripts/quanta_paper_evaluation_evidence_v4.py',ROOT/'scripts/analyze_native_oos_v2.py',ROOT/'scripts/native_secondary_evidence_v2.py',ROOT/'src/alpha_evolve/publication_inference.py']},'new_llm_calls':0,'baseline_models_refitted':0,'primary_replaced':False,'original_project_family_complete':False,'JKP132_alpha_established':False,'full_original_paper_reproduced':False,'pointwise_intervals_not_simultaneous':True,'pristine_confirmation':False,'outputs':{p.name:sha256(p) for p in out.iterdir() if p.is_file()}})
    print('SEPARATE_QUANTA_PARAMETER_SENSITIVITY_COMPLETE_NOT_PRIMARY')
if __name__=='__main__':main()
