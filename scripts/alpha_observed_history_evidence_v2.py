"""Evidence catalogue for a separately labelled all-trial observed-history sensitivity."""
from pathlib import Path
import json,hashlib
from alpha_evolve.openrouter_budget import sha256
from alpha_constructor_abort_v3 import validate_five as validate_alpha_five_attempts
from fidelity_alpha_early_abort_v2 import validate_early_abort
SCOPE='exploratory_all20_observed_history_sensitivity'

def expected_runs():return [f'alphaagent_rounds_paper_gpt35_{i:02d}' for i in range(1,21)]

def verify_protocol(protocol):
    if protocol.get('scope')!=SCOPE or protocol.get('planned_trials')!=list(range(1,21)) or protocol.get('run_names')!=expected_runs():raise ValueError('Observed-history population or scope changed')
    for flag in ['no_new_llm_calls','no_changed_generation_or_failure_handling','does_not_replace_strict_primary','does_not_complete_original_four_case_family','does_not_enter_original54_secondary_family','original_primary_gates_unchanged']:
        if protocol.get(flag) is not True:raise ValueError('Observed-history claim boundary changed: '+flag)
    if protocol.get('existing_early_abort_witnesses')!=[12]:raise ValueError('New aborts require a separate witnessed evidence amendment')

def verify_first_corrected_prefix(run,path,replay,done):
    # Trial01 predates the uniform20-trial replay schema. Its existing proof is
    # a corrected prefix of an independently fully replayed bounded parent.
    # Validate that evidence chain explicitly; never invent missing fields.
    from validate_publication_replay import compare
    if run.name!='alphaagent_rounds_paper_gpt35_01' or done['attempted_rounds']!=5:raise ValueError('Unexpected prefix-proof case')
    parent=run.parent/'alphaagent_bounded_paper_gpt35_01';other=run.parent/(parent.name+'_offline_replay')
    parent_path=parent/'full_replay_validation.json';full=json.loads(parent_path.read_text())
    if full.get('status')!='pass' or full.get('difference_count')!=0 or full.get('network_calls')!=0 or full.get('ledger_mutations')!=0:raise ValueError('Bounded parent full replay is invalid')
    if set(full['artifact_hashes'])!={'model_calls.json','embedding_calls.json','stages.json','trajectories.json'}:raise ValueError('Bounded parent proof incomplete')
    for name,row in full['artifact_hashes'].items():
        if sha256(parent/name)!=row['original_sha256'] or sha256(other/name)!=row['replay_sha256']:raise ValueError('Bounded parent replay artifact changed')
    if replay.get('status')!='pass' or replay.get('difference_count')!=0 or replay.get('network_calls')!=0 or replay.get('failed_round_indices')!=done['failed_round_indices']:raise ValueError('Corrected prefix record invalid')
    if set(replay.get('request_hashes',{}))!={'model_calls.json','embedding_calls.json'}:raise ValueError('Corrected request prefix proof incomplete')
    errors=[];maximum=[0.0]
    for name,row in replay['request_hashes'].items():
        if name not in ['model_calls.json','embedding_calls.json'] or sha256(parent/name)!=row['original'] or sha256(run/name)!=row['replay']:raise ValueError('Corrected prefix request bytes changed')
        old=json.loads((parent/name).read_text());new=json.loads((run/name).read_text())
        if len(old)!=row['original_events'] or len(new)!=row['retained_events']:raise ValueError('Corrected prefix event count changed')
        compare(old[:len(new)],new,name,errors,maximum)
    old=json.loads((parent/'stages.json').read_text());new=json.loads((run/'stages.json').read_text())
    cleaned=lambda rows:[{k:v for k,v in r.items() if k!='started_utc'} for r in rows]
    compare(cleaned([r for r in old if r['loop_index']<5]),cleaned(new),'corrected_stages',errors,maximum)
    hist=json.loads((parent/'trajectories.json').read_text());rounds=[r['loop_index'] for r in old if r['stage']=='feedback' and r.get('completed')]
    hist=[r for i,r in zip(rounds,hist) if i<5];actual=json.loads((run/'trajectories.json').read_text())
    finance=lambda rows:[{k:v for k,v in r.items() if k not in ['workspace','factor_workspaces']} for r in rows]
    compare(finance(hist),finance(actual),'corrected_histories',errors,maximum)
    if errors:raise ValueError('Corrected prefix no longer matches: '+str(errors[:2]))
    return {'path':str(path),'sha256':sha256(path),'attempted_rounds':5,'schema':'corrected_first_five_prefix_of_fully_replayed_bounded_parent','parent_full_replay_sha256':sha256(parent_path),'maximum_rechecked_numeric_difference':maximum[0],'corrected_artifact_hashes':{n:sha256(run/n) for n in ['model_calls.json','embedding_calls.json','stages.json','trajectories.json']}}


def verify_replay(run,filename,done):
    path=run/filename;replay=json.loads(path.read_text())
    if run.name=='alphaagent_rounds_paper_gpt35_01':return verify_first_corrected_prefix(run,path,replay,done)
    if replay.get('status')!='pass' or replay.get('difference_count')!=0 or replay.get('network_calls')!=0 or replay.get('ledger_mutations')!=0:raise ValueError('Observed source replay failed/incomplete')
    if replay.get('attempted_rounds')!=done['attempted_rounds'] or replay.get('failed_round_indices')!=done['failed_round_indices']:raise ValueError('Replay attempt/failure counts differ')
    names={'model_calls.json','embedding_calls.json','stages.json','trajectories.json'}
    if set(replay.get('artifact_hashes',{}))!=names:raise ValueError('Complete observed replay artifacts are required')
    replay_root=run.parent/(run.name+('_observed_abort_replay' if filename=='observed_abort_replay_validation.json' else '_offline_replay'))
    for name,row in replay['artifact_hashes'].items():
        if sha256(run/name)!=row['original_sha256'] or sha256(replay_root/name)!=row['replay_sha256']:raise ValueError('Observed replay bytes changed')
    return {'path':str(path),'sha256':sha256(path),'attempted_rounds':done['attempted_rounds']}

def source_evidence(root,private,name,protocol,source_digest,evaluation_digest):
    if name not in expected_runs():raise ValueError('Unplanned source trial')
    run=private/name;done=json.loads((run/'execution_exit.json').read_text());trial=expected_runs().index(name)+1
    recipe=json.loads((run/'execution_recipe.json').read_text())
    if recipe.get('model')!='openai/gpt-3.5-turbo':raise ValueError('Observed-history model route changed')
    if len(json.loads((run/'model_calls.json').read_text()))!=done['model_calls']:raise ValueError('Returned chat count changed')
    if recipe.get('trial')!='paper_gpt35' or recipe.get('replicate')!=trial or recipe.get('native_rng_seed')!=20260917+trial-1:raise ValueError('Source trial/model/seed identity changed')
    if done['status']=='native_early_abort':
        if trial in protocol['existing_early_abort_witnesses']:
            validate_early_abort(run,root=root)
        else:
            require_additional_witness(root,trial,run)
            from alpha_constructor_abort_v3 import validate_early
            validate_early(run,root=root)
        replay_name='observed_abort_replay_validation.json'
    else:
        if trial == 15:require_additional_witness(root,trial,run)
        validate_alpha_five_attempts(run,root=root)
        replay_name='full_replay_validation.json'
    replay=verify_replay(run,replay_name,done)
    used_path=run/'used_factor_manifest.json';used=json.loads(used_path.read_text())
    if used.get('run')!=name or used.get('selection_basis')!='all source-accepted programs; no evaluation-return selection':raise ValueError('Source-used program identity/selection changed')
    if used.get('diagnostic_early_abort',False)!=(done['status']=='native_early_abort'):raise ValueError('Early-abort scope marker changed')
    rounds=[r['loop_index'] for r in json.loads((run/'stages.json').read_text()) if r['stage']=='feedback' and r.get('completed')]
    if used['successful_source_rounds']!=rounds or len(used['experiments'])!=done['completed_trajectories']:raise ValueError('Source backtest/history count changed')
    # No witnessed zero-backtest case currently exists. A future such case must
    # get its own exact source evidence, not a vacuous accounting pass.
    if not used['experiments'] or not used['programs']:raise ValueError('Zero-program outcome requires its separate exact witness; no vacuous admission')
    account_path=run/'independent_accounts/validation.json';account=json.loads(account_path.read_text())
    if account.get('status')!='pass' or len(account['experiments'])!=len(used['experiments']):raise ValueError('Observed source accounts incomplete')
    by_index={r['experiment_index']:r for r in account['experiments']}
    if len(by_index)!=len(used['experiments']):raise ValueError('Duplicate/missing native account identity')
    for experiment in used['experiments']:
        workspace=Path(experiment['workspace']);a=by_index[experiment['index']]
        if a['status']!='pass' or sha256(workspace/'ret.pkl')!=a['report_sha256']:raise ValueError('Validated native report changed')
        positions=list(workspace.glob('mlruns/*/*/artifacts/portfolio_analysis/positions_normal_1day.pkl'))
        if len(positions)!=1 or sha256(positions[0])!=a['positions_sha256'] or sha256(positions[0].with_name('indicators_normal_1day_obj.pkl'))!=a['orders_sha256']:raise ValueError('Native positions/orders changed')
        if sha256(root/experiment['matrix'])!=experiment['matrix_sha256']:raise ValueError('Native source-used matrix changed')
    proofs=[]
    for row in used['programs']:
        code=root/row['code']
        if sha256(code)!=row['sha256']:raise ValueError('Used program changed')
        p=run/'causality_full_universe'/(row['sha256']+'.json');proof=json.loads(p.read_text())
        if proof.get('status')!='pass' or proof['code_sha256']!=row['sha256'] or proof['input_sha256']!=evaluation_digest or proof['source_python_sha256']!=source_digest:raise ValueError('Full-universe program proof missing/changed')
        proofs.append({'path':str(p.relative_to(root)),'sha256':sha256(p),'code_sha256':row['sha256']})
    return {'trial':trial,'run':name,'native_status':done['status'],'attempted_rounds':done['attempted_rounds'],'failed_round_indices':done['failed_round_indices'],'unattempted_round_indices':done.get('unattempted_round_indices',[]),'completed_trajectories':done['completed_trajectories'],'used_program_count':len(used['programs']),'execution_exit_sha256':sha256(run/'execution_exit.json'),'recipe_sha256':sha256(run/'execution_recipe.json'),'used_manifest_sha256':sha256(used_path),'replay':replay,'account_validation_sha256':sha256(account_path),'program_proofs':proofs,'strict_budget_complete':done['attempted_rounds']==5}

def complete_catalogue(root):
    root=Path(root);private=root/'artifacts/fidelity_completion_v2';public=root/'paper_runs/fidelity_completion_v2'
    protocol_path=public/'alpha_observed_history_sensitivity_protocol.json';protocol=json.loads(protocol_path.read_text());verify_protocol(protocol)
    required=['execution_exit.json','used_factor_manifest.json','independent_accounts/validation.json']
    missing={name:[f for f in required if not (private/name/f).exists()] for name in expected_runs()}
    missing={n:v for n,v in missing.items() if v}
    for row in protocol['frozen_context'].values():
        if sha256(root/row['path'])!=row['sha256']:raise ValueError('Frozen scope context changed')
    if missing:raise ValueError('All20 observed source outcomes/gates are required; missing: '+json.dumps(missing,sort_keys=True))
    frozen_protocol=private/'alpha_observed_history_scope_20260918/frozen_sources/alpha_observed_history_sensitivity_protocol.json'
    if sha256(protocol_path)!=sha256(frozen_protocol):raise ValueError('Frozen observed-history protocol changed; preserve and explicitly amend rather than silently rewrite')
    source=private/'dependencies/alphaagent_95e478';hashes={str(p.relative_to(source)):sha256(p) for p in sorted(source.rglob('*.py'))}
    sd=hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()
    bounded=json.loads((private/'bounded_factor_inputs/manifest.json').read_text());ed=bounded['inputs']['alphaagent/evaluation']['sha256']
    rows=[source_evidence(root,private,n,protocol,sd,ed) for n in expected_runs()]
    return {'scope':SCOPE,'status':'all20_observed_histories_verified_not_an_economic_result','protocol_sha256':sha256(protocol_path),'source_python_sha256':sd,'evaluation_data_sha256':ed,'trials':rows,'planned_rounds':100,'actual_attempted_rounds':sum(r['attempted_rounds'] for r in rows),'unattempted_rounds':sum(len(r['unattempted_round_indices']) for r in rows),'strict_primary_eligibility':False,'implementation_sha256':sha256(Path(__file__))}


def validate_observed_library(path,root):
    root=Path(root);path=Path(path);library=json.loads(path.read_text());folder=path.parent
    if library.get('source_scope')!=SCOPE or library.get('strict_primary_eligibility') is not False or library.get('case')!='alphaagent':raise ValueError('Not the declared observed-history library')
    catalogue_path=folder/'observed_source_catalogue.json'
    if sha256(catalogue_path)!=library.get('observed_source_catalogue_sha256'):raise ValueError('Observed source catalogue changed')
    catalogue=json.loads(catalogue_path.read_text())
    if catalogue!=complete_catalogue(root):raise ValueError('Complete source evidence or scope implementation changed')
    expected={r['run']:r['used_manifest_sha256'] for r in catalogue['trials']}
    if library.get('source_manifests')!=expected or library.get('experiment_index_filter') is not None:raise ValueError('Observed library omits/substitutes trials')
    provider=Path(json.loads((root/'artifacts/fidelity_completion_v2/quantaalpha_data/manifest.json').read_text())['provider_path'])
    if library.get('data_sha256')!=catalogue['evaluation_data_sha256'] or library.get('membership_sha256')!=sha256(provider/'instruments/csi500.txt'):raise ValueError('Observed evaluation data/universe changed')
    required=set()
    for name in expected:
        used=json.loads((root/'artifacts/fidelity_completion_v2'/name/'used_factor_manifest.json').read_text())
        required.update(r['sha256'] for r in used['programs'])
    actual=[r['code_sha256'] for r in library['programs']]
    if set(actual)!=required or len(actual)!=len(required):raise ValueError('Observed library omits/substitutes source-used programs')
    for filename,key in [('fixed_factors.parquet','matrix_sha256'),('fixed_factors.pkl','pickle_sha256')]:
        if sha256(folder/filename)!=library[key]:raise ValueError('Observed library matrix changed')
    for r in library['programs']:
        if sha256(folder/(r['code_sha256']+'.parquet'))!=r['output_sha256']:raise ValueError('Observed program column changed')
    return library,catalogue


def require_additional_witness(root,trial,run):
    root=Path(root)
    path=root/'paper_runs/fidelity_completion_v2/alpha_observed_abort_admission_v3.json'
    frozen=root/'artifacts/fidelity_completion_v2/alpha_constructor_abort_v3_20260918/alpha_observed_abort_admission_v3_frozen.json'
    if sha256(path)!=sha256(frozen):raise ValueError('Additional witness admission was changed')
    extension=json.loads(path.read_text())
    if extension['scope']!=SCOPE or extension['original_protocol_sha256']!=sha256(root/'paper_runs/fidelity_completion_v2/alpha_observed_history_sensitivity_protocol.json'):raise ValueError('Additional witness is not bound to the separate scope')
    row=extension['admissions'].get(str(trial))
    if row is None or row['run']!=run.name:raise ValueError('Unwitnessed additional source outcome')
    for path_key,hash_key in [('diagnosis_path','diagnosis_sha256'),('evidence_path','evidence_sha256')]:
        if sha256(root/row[path_key])!=row[hash_key]:raise ValueError('Additional outcome evidence changed')
    if sha256(root/extension['validator_path'])!=extension['validator_sha256'] or sha256(root/extension['validator_archive'])!=extension['validator_sha256']:raise ValueError('Frozen additional-outcome validator changed')
    return row
