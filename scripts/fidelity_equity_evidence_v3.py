"""Retain frozen v2 admission, adding intrinsic walltime ancestry/settlement gates."""
from pathlib import Path
import json
from alpha_evolve.openrouter_budget import sha256
from fidelity_equity_evidence_v2 import validate_source as validate_v2, final_output_guard
from finagent_walltime_evidence_v2 import validate_admission

def validate_source(root,run,recipe_path,case,*,frozen=False):
    result=validate_v2(root,run,recipe_path,case,frozen=frozen)
    run=Path(run);wrapper=run/'wrapper.json';data=json.loads(wrapper.read_text()) if wrapper.exists() else {}
    expected={s+'_walltime_continuation_v2' for s in ['finagent_AAPL','finagent_MSFT','finagent_TSLA_schema_repair']}
    if run.name in expected or 'walltime_continuation' in data:
        proof=json.loads((Path(root)/'artifacts/fidelity_completion_v2'/(run.name+'_full_replay_validation.json')).read_text())
        replay=Path(root)/'artifacts/fidelity_completion_v2'/proof['replay']
        result['walltime_continuation_admission']=validate_admission(root,run,proof,replay)
    result['validator_v3_sha256']=sha256(Path(__file__))
    return result
