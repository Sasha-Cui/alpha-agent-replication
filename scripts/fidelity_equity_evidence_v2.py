"""Read-only, byte-bound full-replay admission for final equity accounting."""
from pathlib import Path
import json
from alpha_evolve.openrouter_budget import sha256
from validate_publication_replay import compare,read
CASE_NAMES={'finmem':'FinMem','tradingagents':'TradingAgents','finagent':'FinAgent'}

def assert_replay_header(proof,case,count,*,frozen=False):
    if proof.get('status')!='pass' or proof.get('difference_count')!=0 or proof.get('differences')!=[]:
        raise ValueError('Full replay has not passed without differences')
    if proof.get('records')!=count or proof.get('replay_records')!=count:
        raise ValueError('Replay record population differs from completed source')
    if proof.get('case')!=('finmem' if frozen else CASE_NAMES[case]):
        raise ValueError('Replay case substituted')
    if not frozen and (proof.get('network_allowed') is not False or proof.get('ledger_mutations_allowed') is not False):
        raise ValueError('Replay does not document read-only execution')

def final_output_guard(public,private):
    if public.exists() or private.exists():
        raise ValueError('Preserve existing final account output or partial attempt; inspect before rerun')

def validate_source(root,run,recipe_path,case,*,frozen=False):
    root=Path(root);run=Path(run);recipe_path=Path(recipe_path)
    if case not in CASE_NAMES:raise ValueError('Unplanned equity case')
    completion_path=run/'completion.json';done=json.loads(completion_path.read_text());recipe=json.loads(recipe_path.read_text())
    if done.get('status')!='complete':raise ValueError('Source execution incomplete')
    inputs=root/'artifacts/publication_upgrade_v1/finmem_inputs.json' if frozen else Path(recipe['input_file'])
    if sha256(recipe_path)!=done['recipe_sha256'] or sha256(inputs)!=done['input_sha256']:raise ValueError('Source input or recipe changed')
    suffix='json' if case=='tradingagents' else 'jsonl';decisions=run/('decisions.'+suffix);records=read(decisions)
    key='decisions_sha256' if case=='tradingagents' else 'decision_sha256'
    if sha256(decisions)!=done.get(key):raise ValueError('Completed decisions changed or not bound')
    if frozen:
        if run!=root/'artifacts/publication_upgrade_v1/finmem_native' or case!='finmem':raise ValueError('Unplanned frozen original')
        proof_path=root/'artifacts/publication_upgrade_v1/finmem_full_replay_validation.json'
        replay=root/'artifacts/publication_upgrade_v1/finmem_offline_replay'
    else:
        proof_path=root/'artifacts/fidelity_completion_v2'/(run.name+'_full_replay_validation.json')
        replay=None
    proof=json.loads(proof_path.read_text());assert_replay_header(proof,case,len(records),frozen=frozen)
    if not frozen:
        if proof.get('original')!=run.name or proof.get('recipe_sha256')!=sha256(recipe_path) or proof.get('original_script_sha256')!=done['script_sha256']:raise ValueError('Replay/source identity or recipe changed')
        name=proof.get('replay','')
        if not name or Path(name).name!=name or name==run.name:raise ValueError('Invalid replay identity')
        replay=root/'artifacts/fidelity_completion_v2'/name
        if sha256(decisions)!=proof['original_sha256']:raise ValueError('Replayed source bytes changed')
    else:
        expected={str(decisions.relative_to(root)):sha256(decisions)}
        if proof.get('source_sha256')!=expected:raise ValueError('Frozen source/replay binding changed')
    target=replay/('decisions.'+suffix)
    if sha256(target)!=proof['replay_sha256']:raise ValueError('Full replay bytes changed')
    other=json.loads((replay/'completion.json').read_text())
    if other.get('status')!='complete' or other.get('offline') is not True or other.get('recipe_sha256')!=done['recipe_sha256'] or other.get('input_sha256')!=done['input_sha256']:raise ValueError('Offline replay completion/input/recipe changed')
    if other.get(key)!=sha256(target):raise ValueError('Replay completion does not bind its decisions')
    replay_records=read(target)
    errors,delta=compare(records,replay_records)
    if errors:raise ValueError('Full recorded replay no longer matches: '+str(errors[:3]))
    xml_admission=None
    if case=='finagent':
        wrapper_path=run/'wrapper.json'
        wrapper_data=json.loads(wrapper_path.read_text()) if wrapper_path.exists() else {}
        if run.name=='finagent_GOOGL_company_news_xml_repair' or 'xml_format_adaptation' in wrapper_data or 'xml_format_adaptation' in proof:
            from finagent_googl_xml_continuation_evidence_v2 import validate_admission
            xml_admission=validate_admission(root,run,proof,replay)
    prefix_rows=[]
    private=root/'artifacts/fidelity_completion_v2'
    prefixes=[]
    if case=='finagent':
        q=private/'nfs_resume_20260917'/recipe['symbol']/'decisions.jsonl'
        if q.exists():prefixes.append(('nfs_preserved',q))
    wrapper=run/'wrapper.json'
    if wrapper.exists():
        w=json.loads(wrapper.read_text())
        if w.get('preserved_prefix_path'):prefixes.append(('source_schema',Path(w['preserved_prefix_path'])))
    if not frozen:
        for recovery in sorted(private.glob('transport_recovery*/recovery.json')):
            metadata=json.loads(recovery.read_text())
            for row in metadata['runs']:
                if row['name']==run.name:
                    q=recovery.parent/run.name/'artifacts/fidelity_completion_v2'/run.name/('decisions.'+suffix)
                    if not q.exists():raise ValueError('Transport source prefix missing')
                    prefixes.append(('transport',q))
    for kind,p in prefixes:
        prior=read(p)
        if len(prior)>len(records):raise ValueError('Preserved prefix longer than complete source')
        issues,maximum=compare(prior,records[:len(prior)])
        if issues:raise ValueError('Preserved source prefix changed: '+str(p))
        prefix_rows.append({'kind':kind,'path':str(p.relative_to(root)),'sha256':sha256(p),'records':len(prior),'maximum_numeric_difference':maximum[0]})
    return {'status':'pass','source_run':str(run.relative_to(root)),'case':case,'records':len(records),'full_replay_proof_sha256':sha256(proof_path),'source_completion_sha256':sha256(completion_path),'replay_completion_sha256':sha256(replay/'completion.json'),'original_decisions_sha256':sha256(decisions),'replay_decisions_sha256':sha256(target),'recipe_sha256':sha256(recipe_path),'input_sha256':sha256(inputs),'current_full_record_recomparison_maximum_difference':delta[0],'preserved_prefixes':prefix_rows,'xml_format_adaptation_admission':xml_admission,'frozen_original_evidence':frozen,'scope':'Read-only current byte/prefix/replay binding. No model rerun, account result, independent human review or full-paper fidelity claim.','validator_sha256':sha256(Path(__file__))}
