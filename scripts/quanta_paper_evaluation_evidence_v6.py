"""Strict source and fixed-library gates for the distinct Quanta parameter sensitivity."""
from pathlib import Path
import json,hashlib
from alpha_evolve.openrouter_budget import sha256
SCOPE='exploratory_quanta_paper_parameter_fixed_library_sensitivity'
SOURCE_RUN='quantaalpha_paper_parameters_walltime_continuation_v3'
OUTPUT_PREFIX='quantaalpha_paper_parameters'
from quanta_continued_source_admission_v4 import admission,evaluation_adapter as adapter
from quanta_native_population_v3 import validate_receipt

def protocol(root):
    p=root/'paper_runs/fidelity_completion_v2/quanta_paper_parameter_evaluation_protocol.json'
    frozen=root/'artifacts/fidelity_completion_v2/quanta_paper_eval_setup_20260918'/p.name
    if sha256(p)!=sha256(frozen):raise ValueError('Frozen variant evaluation protocol changed')
    d=json.loads(p.read_text())
    if d['scope']!=SCOPE or d['source_run']!=OUTPUT_PREFIX or d['new_primary_substitution'] is not False or d['new_llm_api_calls']!=0:raise ValueError('Variant source/scope/claim changed')
    for r in d['frozen_context'].values():
        if sha256(root/r['path'])!=r['sha256']:raise ValueError('Frozen evaluation context changed')
    return d,sha256(p)

def source_gate(root,*,require_causality=False):
    root=Path(root);plan,pdigest=protocol(root);private=root/'artifacts/fidelity_completion_v2';run=private/SOURCE_RUN
    names=['execution_exit.json','full_replay_validation.json','used_factor_manifest.json','independent_accounts/validation.json']
    absent=[n for n in names if not (run/n).exists()]
    if absent:raise ValueError('Quanta variant source gates incomplete: '+', '.join(absent))
    lineage=admission(root)
    done=json.loads((run/'execution_exit.json').read_text());rp=json.loads((run/'full_replay_validation.json').read_text());recipe=json.loads((run/'recipe.json').read_text());used=json.loads((run/'used_factor_manifest.json').read_text());accounts=json.loads((run/'independent_accounts/validation.json').read_text())
    lineage['native_population_gate']=validate_receipt(root,run,used)
    if done['status']!='native_pipeline_returned' or rp['status']!='pass' or rp['difference_count']!=0 or rp['network_calls']!=0 or rp['ledger_mutations']!=0:raise ValueError('Quanta source/full replay gate failed')
    if recipe.get('model')!='openai/gpt-5.2' or recipe.get('max_tokens')!=3000 or recipe.get('reasoning_effort')!='none':raise ValueError('Variant source model/decoding changed')
    if recipe['paper_parameter_protocol_sha256']!=plan['source_protocol_sha256'] or recipe['wrapper_sha256']!=sha256(root/'scripts/run_quantaalpha_paper_parameters_v2.py') or recipe['parameter_wiring_sha256']!=sha256(root/'src/alpha_evolve/quantaalpha_paper_parameters_v2.py'):raise ValueError('Variant executed recipe/wiring changed')
    boundary_path=private/'bounded_factor_inputs/manifest.json'
    if recipe['bounded_input_manifest_sha256']!=sha256(boundary_path) or recipe['data_manifest_sha256']!=sha256(private/'quantaalpha_data/manifest.json'):raise ValueError('Generation boundary or provider lineage changed')
    boundary=json.loads(boundary_path.read_text())
    for name in ['quantaalpha/search','quantaalpha/debug']:
        row=boundary['inputs'][name]
        if sha256(Path(row['path']))!=row['sha256']:raise ValueError('Bounded generation data changed')
    replay=private/(SOURCE_RUN+'_offline_replay');required={'model_calls.json','embedding_calls.json','parameter_wiring.json','quality_gate_events.json','log/evolution_state.json','log/trajectory_pool.json'}
    if set(rp.get('artifact_hashes',{}))!=required:raise ValueError('Variant replay omits source state/telemetry')
    for n,r in rp['artifact_hashes'].items():
        if sha256(run/n)!=r['original'] or sha256(replay/n)!=r['replay']:raise ValueError('Variant replay bytes changed')
    if len(json.loads((run/'model_calls.json').read_text()))!=done['model_calls']:raise ValueError('Returned model response count changed')
    wiring=json.loads((run/'parameter_wiring.json').read_text())
    if wiring['constructor_limits']!={'base_features':6,'duplication':5,'symbol_length':250} or wiring['native_file_edits']!=0:raise ValueError('Executed paper parameters differ')
    pool=json.loads((run/'log/trajectory_pool.json').read_text());trajectories=pool['trajectories']
    if used['run']!=SOURCE_RUN or used['selection_basis']!='all source-accepted programs; no evaluation-return selection' or used['trajectory_pool_sha256']!=sha256(run/'log/trajectory_pool.json') or rp['trajectories']!=len(trajectories):raise ValueError('Variant used trajectory population changed')
    if {e['trajectory_id'] for e in used['experiments']}!=set(trajectories) or any(not 0<=e['round_idx']<5 for e in used['experiments']):raise ValueError('Variant task subset or phase substituted')
    if not used['programs'] or not used['experiments']:raise ValueError('No evaluable source library; do not fabricate factors')
    if accounts['status']!='pass' or len(accounts['experiments'])!=len(used['experiments']):raise ValueError('Variant source accounts incomplete')
    source=private/'dependencies/quantaalpha_b7ceb27'
    hashes={str(p.relative_to(source)):sha256(p) for p in sorted(source.rglob('*.py'))}
    if used['source_python_hashes']!=hashes:raise ValueError('Pinned native source changed')
    sd=hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()
    for name,h in used['snapshot_sha256'].items():
        if sha256(root/name)!=h:raise ValueError('Native task snapshot changed')
    byindex={r['experiment_index']:r for r in accounts['experiments']}
    for e in used['experiments']:
        w=Path(e['workspace']);a=byindex[e['index']]
        positions=list(w.glob('mlruns/*/*/artifacts/portfolio_analysis/positions_normal_1day.pkl'))
        if a['status']!='pass' or sha256(w/'ret.pkl')!=a['report_sha256'] or len(positions)!=1 or sha256(positions[0])!=a['positions_sha256'] or sha256(positions[0].with_name('indicators_normal_1day_obj.pkl'))!=a['orders_sha256'] or sha256(root/e['matrix'])!=e['matrix_sha256']:raise ValueError('Native backtest/matrix/account binding changed')
    expected_data=sha256(private/'quantaalpha_data/full/daily_pv.h5')
    proofs=[]
    for row in used['programs']:
        if sha256(root/row['code'])!=row['sha256']:raise ValueError('Source-used code changed')
        if require_causality:
            p=run/'causality_full_universe'/(row['sha256']+'.json');proof=json.loads(p.read_text())
            if proof['status']!='pass' or proof['code_sha256']!=row['sha256'] or proof['input_sha256']!=expected_data or proof['source_python_sha256']!=sd:raise ValueError('Variant full-universe program gate failed')
            proofs.append({'path':str(p.relative_to(root)),'sha256':sha256(p)})
    return {'scope':SCOPE,'protocol_sha256':pdigest,'continuation_lineage':lineage,'run':SOURCE_RUN,'source_exit_sha256':sha256(run/'execution_exit.json'),'source_recipe_sha256':sha256(run/'recipe.json'),'source_replay_sha256':sha256(run/'full_replay_validation.json'),'used_manifest_sha256':sha256(run/'used_factor_manifest.json'),'account_gate_sha256':sha256(run/'independent_accounts/validation.json'),'source_python_sha256':sd,'data_sha256':expected_data,'actual_trajectories':len(trajectories),'program_count':len(used['programs']),'program_proofs':proofs,'strict_primary_eligibility':False}

def validate_fixed(path,root):
    root=Path(root);path=Path(path);library=json.loads(path.read_text());evidence=source_gate(root,require_causality=True)
    if library['case']!='quantaalpha' or library['source_manifests']!={SOURCE_RUN:evidence['used_manifest_sha256']} or library.get('experiment_index_filter') is not None:raise ValueError('Variant fixed library changed source/task scope')
    used=json.loads((root/'artifacts/fidelity_completion_v2'/SOURCE_RUN/'used_factor_manifest.json').read_text())
    if {p['code_sha256'] for p in library['programs']}!={p['sha256'] for p in used['programs']} or len(library['programs'])!=len(used['programs']):raise ValueError('Variant fixed library drops or replaces programs')
    provider=Path(json.loads((root/'artifacts/fidelity_completion_v2/quantaalpha_data/manifest.json').read_text())['provider_path'])
    if library['data_sha256']!=evidence['data_sha256'] or library['membership_sha256']!=sha256(provider/'instruments/csi300.txt'):raise ValueError('Variant evaluation data/universe changed')
    for filename,key in [('fixed_factors.parquet','matrix_sha256'),('fixed_factors.pkl','pickle_sha256')]:
        if sha256(path.parent/filename)!=library[key]:raise ValueError('Variant fixed matrix changed')
    for row in library['programs']:
        if sha256(path.parent/(row['code_sha256']+'.parquet'))!=row['output_sha256']:raise ValueError('Variant factor column changed')
    return library,evidence
