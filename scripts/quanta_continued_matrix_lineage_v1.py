"""Accept only exact source-admitted original/new native matrices for continued proofs."""
from pathlib import Path
import json
from alpha_evolve.openrouter_budget import sha256
SOURCE_RUN='quantaalpha_paper_parameters_walltime_continuation_v3'
SETUP='artifacts/fidelity_completion_v2/quanta_continued_proof_setup_20260920_0732'
PROTOCOL='paper_runs/fidelity_completion_v2/quanta_continued_proof_protocol_v1.json'

def validate_protocol(root):
    root=Path(root);public=root/PROTOCOL;frozen=root/SETUP/'frozen_protocol.json'
    if sha256(public)!=sha256(frozen):raise ValueError('Continued proof protocol changed')
    d=json.loads(public.read_text())
    if d['source_run']!=SOURCE_RUN or d['financial_expressions_changed'] or d['completed_source_model_rerun_allowed']:raise ValueError('Continued proof scope changed')
    for row in d['bindings']:
        if sha256(root/row['path'])!=row['sha256']:raise ValueError('Continued proof method/evidence changed: '+row['path'])
    return sha256(public)

def assert_use_binding(root,use,bindings):
    root=Path(root);key=(use.get('experiment_index'),use.get('column'))
    if key not in bindings:raise ValueError('Unknown experiment/column matrix use')
    expected=bindings[key]
    if use.get('matrix')!=expected['matrix'] or use.get('matrix_sha256')!=expected['matrix_sha256']:
        raise ValueError('Matrix path/hash differs from the exact admitted experiment')
    path=root/use['matrix'];workspace=root/expected['workspace']
    if path.resolve()!=workspace.resolve()/'combined_factors_df.parquet' or path.resolve()!=path.absolute():
        raise ValueError('Matrix is not the exact canonical native workspace artifact')
    if sha256(path)!=expected['matrix_sha256']:raise ValueError('Native matrix bytes changed')
    return path

def load_matrix_scope(root,run,manifest,case,debug_fixture=False,data_file=None):
    root=Path(root);run=Path(run)
    if case!='quantaalpha' or debug_fixture or data_file is not None or run.resolve()!=(root/'artifacts/fidelity_completion_v2'/SOURCE_RUN).resolve():
        raise ValueError('This proof adapter permits only the completed continued Quanta full-universe case')
    if manifest is None or Path(manifest).resolve()!=(run/'used_factor_manifest.json').resolve():raise ValueError('Exact source-used manifest required')
    protocol_sha=validate_protocol(root)
    from quanta_paper_evaluation_evidence_v6 import source_gate
    evidence=source_gate(root)
    closure=json.loads((run/'source_export_accounts_completion.json').read_text())
    if closure['status']!='continued_source_full_replay_export_accounts_pass' or closure['source_evidence']!=evidence or closure['script_sha256']!=sha256(root/'scripts/close_quanta_continued_source_v5.py'):
        raise ValueError('Actual source export/account closure changed')
    used=json.loads(Path(manifest).read_text());population=json.loads((run/'native_model_population_validation.json').read_text())
    permitted=set(population['pool_workspaces']);done=json.loads((run/'continuation_completion.json').read_text())
    hashes=dict(done['new_native_model_artifacts'])
    lineage=json.loads((root/'artifacts/fidelity_completion_v2/quanta_continuation_setup_20260919_after_reset/v3/native_artifact_lineage.json').read_text())
    for row in lineage['original_model_cache_entries']:
        for f in row['files']:
            if f['path'] in hashes and hashes[f['path']]!=f['sha256']:raise ValueError('Conflicting original/new artifact identity')
            hashes[f['path']]=f['sha256']
    bindings={}
    for exp in used['experiments']:
        workspace=str(Path(exp['workspace']).relative_to(root));matrix=exp['matrix']
        if workspace not in permitted or hashes.get(matrix)!=exp['matrix_sha256']:
            raise ValueError('Matrix lacks exact original/new saved native artifact ancestry')
        for column in exp['features']:
            key=(exp['index'],column)
            if key in bindings:raise ValueError('Duplicate native matrix column identity')
            bindings[key]={'matrix':matrix,'matrix_sha256':exp['matrix_sha256'],'workspace':workspace}
    for program in used['programs']:
        for use in program['uses']:assert_use_binding(root,use,bindings)
    receipt={'scope':'exact_original_or_continued_native_matrix_artifact_not_arbitrary_external_path','proof_protocol_sha256':protocol_sha,'used_manifest_sha256':sha256(Path(manifest)),'source_completion_sha256':sha256(run/'continuation_completion.json'),'source_replay_sha256':sha256(run/'full_replay_validation.json'),'source_closure_sha256':sha256(run/'source_export_accounts_completion.json'),'population_sha256':sha256(run/'native_model_population_validation.json'),'matrix_guard_sha256':sha256(Path(__file__)),'admitted_experiments':len(used['experiments']),'all_program_uses_preflighted_before_factor_execution':True}
    return bindings,receipt
