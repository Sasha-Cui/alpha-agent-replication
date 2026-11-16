#!/usr/bin/env python3
"""Paired exploratory observed-history contrast; never a strict primary substitute."""
from pathlib import Path
import sys,json
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from alpha_evolve.openrouter_budget import atomic_json,sha256
from alpha_evolve.publication_inference import grouped_t_effect
from alpha_observed_history_evidence_v2 import SCOPE,validate_observed_library
from analyze_native_oos_v2 import core_settings,aligned_difference
from analyze_publication_upgrade import metrics
from native_secondary_evidence_v2 import validate_execution_identity
PRIVATE=ROOT/'artifacts/fidelity_completion_v2'
PUBLIC=ROOT/'paper_runs/fidelity_completion_v2'
ARMS=['alpha158','alpha158_plus_library']

def load_observed_arm(run_name, case, arm, plumbing, *, secondary_unit=None):
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
    if plumbing or secondary_unit is not None or case != 'alphaagent' or arm not in ['alpha158','alpha158_plus_library']:
        raise ValueError('Unexpected observed-history analysis scope')
    if recipe.get('source_scope') != SCOPE or recipe.get('strict_primary_eligibility') is not False:
        raise ValueError('Financial arm lacks the separate observed-history scope')
    library, catalogue = validate_observed_library(libraries[0], ROOT)
    if recipe.get('observed_source_catalogue_sha256') != library['observed_source_catalogue_sha256']:
        raise ValueError('Financial arm/source catalogue identity differs')
    embargo = recipe['embargo']
    provider = Path(json.loads((PRIVATE / 'quantaalpha_data/manifest.json').read_text())['provider_path'])
    calendar = pd.DatetimeIndex(pd.to_datetime((provider / 'calendars/day.txt').read_text().splitlines()))
    expected = calendar[(calendar >= pd.Timestamp(embargo['first_evaluation_execution_open'])) & (calendar <= pd.Timestamp('2025-12-26'))]
    if not frame.index.equals(expected):
        raise ValueError('Observed-history account calendar incomplete; never intersect')
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


def exploratory_result(left,right):
    aligned_difference(left,right)
    result=grouped_t_effect(left.to_numpy(),right.to_numpy(),frequency=252,groups=4,threshold=.02,confidence=.99)
    result['within_margin_using_pointwise99']=result.pop('equivalent_within_margin_tost5')
    result['rules_out_positive_margin_using_pointwise99']=result.pop('rules_out_positive_margin_one_sided5')
    result.update(scope=SCOPE,strict_primary_eligibility=False,project_family_significance_claim=False,
                  original_four_case_family_complete=False,original54_secondary_family_complete=False,
                  raw_p_value_role='Exploratory descriptive diagnostic only; no project-family significance flag')
    return result


def main():
    protocol_path=PUBLIC/'alpha_observed_history_sensitivity_protocol.json'
    protocol=json.loads(protocol_path.read_text())
    if protocol['scope']!=SCOPE:raise ValueError('Unexpected sensitivity protocol')
    calibration=PUBLIC/'native_grouped_calibration/summary.json'
    c=json.loads(calibration.read_text())
    if c['status']!='complete' or len(c['results'])!=8:raise ValueError('Grouped calibration unavailable')
    out=PUBLIC/'alpha_observed_history_sensitivity'
    if out.exists():raise ValueError('Preserve existing sensitivity analysis')
    library,catalogue=validate_observed_library(PRIVATE/'alphaagent_observed20_fixed_library/library_manifest.json',ROOT)
    evidence=[];performance=[];comparisons=[];paths=[]
    for execution in ['native','opening_information']:
        values={};proofs=[]
        for arm in ARMS:
            name='alphaagent_observed20_oos_'+arm+('' if execution=='native' else '_open_information')
            value,proof=load_observed_arm(name,'alphaagent',arm,False)
            identity=validate_execution_identity(name,execution,PRIVATE)
            values[arm]=value;proofs.append(proof)
            evidence.append({**proof,**identity,'execution':execution})
            performance.append({'execution':execution,'arm':arm,**metrics(value,frequency=252)})
            paths.append(value.rename('net_return').reset_index().assign(execution=execution,arm=arm))
        if len({p['core_settings'] for p in proofs})!=1 or len({p['library_manifest_sha256'] for p in proofs})!=1:raise ValueError('Paired arms differ beyond features')
        comparisons.append({'execution':execution,'role':'exploratory_economic_sensitivity' if execution=='opening_information' else 'native_execution_diagnostic',**exploratory_result(values['alpha158_plus_library'],values['alpha158'])})
    out.mkdir()
    for name,data in [('performance',performance),('comparisons',comparisons),('execution_evidence',evidence),('observed_source_catalogue',catalogue)]:atomic_json(out/(name+'.json'),data)
    pd.concat(paths,ignore_index=True).to_csv(out/'daily_net_returns.csv',index=False)
    atomic_json(out/'completion.json',{'status':'exploratory_observed_history_sensitivity_complete_not_primary','scope':SCOPE,
        'protocol_sha256':sha256(protocol_path),'calibration_sha256':sha256(calibration),
        'source_files':{str(p.relative_to(ROOT)):sha256(p) for p in [Path(__file__),ROOT/'scripts/alpha_observed_history_evidence_v2.py',ROOT/'scripts/analyze_native_oos_v2.py',ROOT/'scripts/native_secondary_evidence_v2.py',ROOT/'src/alpha_evolve/publication_inference.py']},
        'strict_primary_eligibility':False,'original_four_case_family_complete':False,'original54_secondary_family_complete':False,
        'actual_source_attempted_rounds':catalogue['actual_attempted_rounds'],'unattempted_rounds':catalogue['unattempted_rounds'],
        'new_llm_calls':0,'language_model_specific_advantage_established':False,'pristine_confirmatory_claim':False,'JKP132_alpha_established':False,'full_original_paper_reproduced':False,
        'inference_boundary':'Pointwise99% grouped arithmetic-mean intervals and descriptive raw p values, conditional on the realized mixed-budget library. No project-family significance declaration. Cagr fields use252-session geometric annualization, not calendar-time CAGR.',
        'outputs':{p.name:sha256(p) for p in out.iterdir() if p.is_file()}})
    print('EXPLORATORY_OBSERVED_HISTORY_SENSITIVITY_COMPLETE_NOT_PRIMARY')
if __name__=='__main__':main()
