"""Explicitly witnessed constructor HTTP400 aborts; no retry or invented rounds."""
from pathlib import Path
import json,hashlib,fcntl,copy,sqlite3,shutil,subprocess,sys,os,socket
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from alpha_evolve.openrouter_budget import sha256,atomic_json
from alpha_evolve.publication_replay import ReadOnlyReplay
PRIVATE=ROOT/'artifacts/fidelity_completion_v2'
CASES={14:dict(pid=2420513,round=2,calls=96,before=20,reservation=.0273765,key='914f15d540e6453116f8222af881323b0af10b0eb280c70e307576fcdbb1bafb'),15:dict(pid=2420514,round=4,calls=151,before=84,reservation=.0297075,key='d5a2d39be66896ac71e93565176e8eab979953f30059a9fc2a1ebcad7107fc50')}

def run_name(trial):
    if trial not in CASES:raise ValueError('No separately witnessed case')
    return f'alphaagent_rounds_paper_gpt35_{trial:02d}'

def audit_path(trial):return PRIVATE/'alpha_constructor_abort_v3_20260918'/f'trial{trial:02d}'
def replay_filename(trial):return 'full_replay_validation.json' if CASES[trial]['round']==4 else 'observed_abort_replay_validation.json'
def replay_name(trial):return run_name(trial)+('_offline_replay' if CASES[trial]['round']==4 else '_observed_abort_replay')
def identity(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def read_meter():
    root=ROOT/'runs/economic_fidelity/openrouter'
    with (root/'project_spend.lock').open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        return ReadOnlyReplay(root,'unused','openai/gpt-3.5-turbo',study='fidelity_v2_alphaagent_source_search',study_cap=20)

def verify_stages(stages,c):
    expected=[(i,s) for i in range(c['round']) for s in ['factor_propose','factor_construct','factor_calculate','factor_backtest','feedback']]+[(c['round'],'factor_propose'),(c['round'],'factor_construct')]
    if [(r['loop_index'],r['stage']) for r in stages]!=expected or not all(r.get('completed') for r in stages[:-1]):raise ValueError('Witness does not match the complete observed stage prefix')
    last=stages[-1]
    if last.get('completed') or last.get('error_type')!='MeteredStop' or last.get('model_calls_before')!=c['before'] or last.get('model_calls_after')!=c['calls']:raise ValueError('Constructor abort identity changed')

def diagnose(trial):
    c=CASES[trial];run=PRIVATE/run_name(trial);out=audit_path(trial)
    if out.exists():raise ValueError('Preserve existing diagnosis attempt')
    out.mkdir(parents=True)
    stages=json.loads((run/'stages.json').read_text());verify_stages(stages,c)
    calls=json.loads((run/'model_calls.json').read_text())
    if len(calls)!=c['calls']:raise ValueError('Returned response count changed')
    terminal=subprocess.check_output(['/opt/slurm/current/bin/sacct','-j',f'26502926_{trial}','--format=JobID%30,JobIDRaw,State,ExitCode,Elapsed,MaxRSS','--parsable2','--noheader'],text=True)
    if not any(line.startswith(f'26502926_{trial}|') and '|FAILED|1:0|' in line for line in terminal.splitlines()):raise ValueError('Terminal source identity not verified')
    (out/'terminal_job.txt').write_text(terminal)
    log=run.with_suffix('.log')
    if 'urllib.error.HTTPError: HTTP Error 400: Bad Request' not in log.read_text():raise ValueError('Not the observed HTTP400 case')
    files=list(run.glob('*.json'))+list((run/'log/__session__').glob('*/*'))+list((run/'log').rglob('common_logs.log'))+[log,ROOT/'scripts/run_alphaagent_rounds_v2.py']
    rows=[]
    for p in files:
        if not p.is_file():continue
        q=out/'original'/p.relative_to(ROOT);q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q)
        if sha256(p)!=sha256(q):raise ValueError('Source changed during preservation')
        rows.append({'path':str(p.relative_to(ROOT)),'copy':str(q.relative_to(ROOT)),'sha256':sha256(p)})
    atomic_json(out/'preservation_manifest.json',{'files':rows})
    meter=read_meter();entry=meter.frozen_state['calls'][c['key']]
    if entry['pid']!=c['pid'] or entry['status']!='reserved' or entry['study']!=meter.study or entry['reserved_usd']!=c['reservation']:raise ValueError('Failed reservation identity changed')
    source_log=run/f"log/r/llm_messages/{c['pid']}/common_logs.log";text=source_log.read_text()
    si=text.rindex('Role:system\nContent: ')+len('Role:system\nContent: ');ui=text.rindex('Role:user\nContent: ')
    rawsystem=text[si:ui];rawuser=text[ui+len('Role:user\nContent: '):]
    previous=meter.cached_response(calls[-1]['request_hash']);template=copy.deepcopy(previous['request']);template['seed']=890000+(trial-1)*100000+c['calls']
    candidates=[]
    for a in range(5):
        for b in range(5):
            if a and not rawsystem.endswith('\n'*a):continue
            if b and not rawuser.endswith('\n'*b):continue
            body=copy.deepcopy(template);body['messages']=[{'role':'system','content':rawsystem[:-a] if a else rawsystem},{'role':'user','content':rawuser[:-b] if b else rawuser}]
            envelope={'endpoint':'chat/completions','request':body}
            if identity(envelope)==c['key']:candidates.append((envelope,a,b))
    if len(candidates)!=1:raise ValueError('No unique exact failed-envelope match')
    envelope,a,b=candidates[0];atomic_json(out/'failed_request.json',envelope)
    cache=ROOT/'runs/economic_fidelity/openrouter/response_cache.sqlite3';journal=cache.with_name('cohort_responses.jsonl')
    with sqlite3.connect('file:'+str(cache)+'?mode=ro',uri=True) as conn:n=conn.execute('SELECT COUNT(*) FROM responses WHERE request_hash=?',(c['key'],)).fetchone()[0]
    size=journal.stat().st_size;found=0
    with journal.open('rb') as f:
        while f.tell()<size:
            line=f.readline()
            if c['key'].encode() in line and json.loads(line).get('request_hash')==c['key']:found+=1
    if n or found:raise ValueError('A durable response exists; this is not a response-absent witness')
    def forbidden(*args,**kwargs):raise RuntimeError('Diagnosis must not access the network')
    socket.create_connection=forbidden;socket.socket.connect=forbidden
    import tiktoken
    enc=tiktoken.encoding_for_model('gpt-3.5-turbo')
    counts=[len(enc.encode(m['content'])) for m in envelope['request']['messages']]
    prior_content=sum(len(enc.encode(m['content'])) for m in previous['request']['messages'])
    prior_usage=previous['response']['usage']['prompt_tokens'];overhead=prior_usage-prior_content
    endpoint_path=PRIVATE/'alpha_trial08_failure_20260918/openrouter_gpt35_endpoints.json'
    limit=next(x['context_length'] for x in json.loads(endpoint_path.read_text())['data']['endpoints'] if x['provider_name']=='OpenAI')
    total=sum(counts)+envelope['request']['max_tokens']
    result={'status':'exact_source_logged_request_bound_response_absence_verified','trial':trial,'run':run.name,'witness':c,'attempted_rounds':c['round']+1,'planned_rounds':5,'completed_trajectories':c['round'],'failed_round_indices':[c['round']],'unattempted_round_indices':list(range(c['round']+1,5)),'source_log_sha256':sha256(source_log),'logger_newlines_removed':{'system':a,'user':b},'failed_request_hash':c['key'],'failed_reservation':entry,'content_tokens':counts,'requested_output_tokens':envelope['request']['max_tokens'],'content_plus_requested_output_tokens':total,'previous_prompt_usage_minus_tokenized_content':overhead,'projected_total_using_previous_empirical_overhead':total+overhead,'archived_current_context_length':limit,'content_only_exceeds_archived_limit':total>limit,'projected_total_exceeds_archived_limit':total+overhead>limit,'context_metadata_sha256':sha256(endpoint_path),'provider_error_body_available':False,'cause_boundary':'Context counts and prior observed chat overhead are diagnostics, not an observed provider error explanation or guaranteed exact tokenization. The literal HTTP400 and exact request are independently bound.','sqlite_matches':n,'journal_matches':found,'journal_bytes_scanned':size,'network_calls':0,'ledger_mutations':0,'paid_retries':0,'diagnostic_source_sha256':sha256(Path(__file__))}
    atomic_json(out/'diagnosis.json',result)
    print('EXACT_ABORT_DIAGNOSIS_PASS',trial,total,total+overhead,limit,flush=True)

def validate(run,*,require_replay=True,root=ROOT):
    run=Path(run);root=Path(root);trial=next((i for i in CASES if run.name==run_name(i)),None)
    if trial is None:raise ValueError('Unwitnessed constructor-abort case')
    c=CASES[trial];done=json.loads((run/'execution_exit.json').read_text());attempts=c['round']+1
    expected={'status':'native_final_attempt_failed' if attempts==5 else 'native_early_abort','attempted_rounds':attempts,'planned_rounds':5,'completed_trajectories':c['round'],'model_calls':c['calls'],'failed_round_indices':[c['round']],'unattempted_round_indices':list(range(attempts,5)),'native_five_attempt_budget_complete':attempts==5}
    if any(done.get(k)!=v for k,v in expected.items()):raise ValueError('Observed attempt counts or failure scope changed')
    evidence_path=run/'constructor_abort_evidence_v3.json'
    if sha256(evidence_path)!=done.get('constructor_abort_evidence_sha256'):raise ValueError('Constructor witness changed')
    evidence=json.loads(evidence_path.read_text())
    if evidence.get('witness')!=c or evidence.get('trial')!=trial:raise ValueError('Wrong witnessed abort identity')
    required={str((run/n).relative_to(root)) for n in ['model_calls.json','embedding_calls.json','stages.json','execution_recipe.json','trajectories.json',f"log/__session__/{c['round']}/0_factor_propose"]}
    if not required.issubset({r['path'] for r in evidence['bindings']}):raise ValueError('Observed evidence omits required artifacts')
    for row in evidence['bindings']:
        if sha256(root/row['path'])!=row['sha256']:raise ValueError('Observed artifact changed: '+row['path'])
    verify_stages(json.loads((run/'stages.json').read_text()),c)
    if require_replay:
        proof=json.loads((run/replay_filename(trial)).read_text())
        if proof.get('status')!='pass' or proof.get('difference_count')!=0 or proof.get('network_calls')!=0 or proof.get('ledger_mutations')!=0 or proof.get('attempted_rounds')!=attempts or proof.get('failed_round_indices')!=[c['round']] or proof.get('constructor_abort_evidence_sha256')!=sha256(evidence_path):raise ValueError('Exact complete observed replay required')
        if set(proof.get('artifact_hashes',{}))!={'model_calls.json','embedding_calls.json','stages.json','trajectories.json'}:raise ValueError('Incomplete replay artifact set')
        for name,row in proof['artifact_hashes'].items():
            if sha256(run/name)!=row['original_sha256'] or sha256(run.parent/replay_name(trial)/name)!=row['replay_sha256']:raise ValueError('Observed replay artifact changed')
    return done

def validate_five(run,*,root=ROOT,require_replay=True):
    run=Path(run)
    if run.name in [run_name(i) for i in CASES]:
        done=validate(run,root=root,require_replay=require_replay)
        if done['attempted_rounds']!=5:raise ValueError('Alpha trial lacks all five attempted rounds')
        return done
    from fidelity_alpha_terminal_v2 import validate_alpha_five_attempts
    return validate_alpha_five_attempts(run,root=root,require_replay=require_replay)

def validate_early(run,*,root=ROOT,require_replay=True):
    run=Path(run)
    if run.name in [run_name(i) for i in CASES]:
        done=validate(run,root=root,require_replay=require_replay)
        if done['attempted_rounds']>=5:raise ValueError('Final abort is not an early-abort diagnostic')
        return done
    from fidelity_alpha_early_abort_v2 import validate_early_abort
    return validate_early_abort(run,root=root,require_replay=require_replay)

def finalize(trial):
    c=CASES[trial];run=PRIVATE/run_name(trial);out=audit_path(trial)
    if (run/'execution_exit.json').exists() or (run/'trajectories.json').exists():raise ValueError('Preserve existing extraction')
    d=json.loads((out/'diagnosis.json').read_text())
    if d['witness']!=c or d['status']!='exact_source_logged_request_bound_response_absence_verified':raise ValueError('Diagnosis missing/changed')
    preservation=json.loads((out/'preservation_manifest.json').read_text())
    for row in preservation['files']:
        if sha256(ROOT/row['path'])!=row['sha256'] or sha256(ROOT/row['copy'])!=row['sha256']:raise ValueError('Original attempt changed')
    source=PRIVATE/'dependencies/alphaagent_95e478';recipe=json.loads((run/'execution_recipe.json').read_text())
    for name,h in recipe['source_python_hashes'].items():
        if sha256(source/name)!=h:raise ValueError('Pinned source changed')
    os.environ.update(OPENAI_API_KEY='unused-offline',CHAT_OPENAI_API_KEY='unused-offline')
    sys.path.insert(0,str(source))
    def forbidden(*args,**kwargs):raise RuntimeError('Extraction forbids network')
    socket.create_connection=forbidden;socket.socket.connect=forbidden
    import pickle
    from finalize_alphaagent_terminal_v2 import trajectories
    checkpoint=run/f"log/__session__/{c['round']}/0_factor_propose"
    with checkpoint.open('rb') as f:instance=pickle.load(f)
    if (instance.loop_idx,instance.step_idx,len(instance.trace.hist))!=(c['round'],1,c['round']):raise ValueError('Observed checkpoint/history changed')
    atomic_json(run/'trajectories.json',trajectories(instance))
    files=[run/n for n in ['model_calls.json','embedding_calls.json','stages.json','execution_recipe.json','trajectories.json']]+[checkpoint,Path(__file__),ROOT/'scripts/finalize_alphaagent_terminal_v2.py']
    files += [out/n for n in ['diagnosis.json','failed_request.json','preservation_manifest.json','terminal_job.txt']]+[ROOT/r['copy'] for r in preservation['files']]
    atomic_json(run/'constructor_abort_evidence_v3.json',{'trial':trial,'witness':c,'bindings':[{'path':str(p.relative_to(ROOT)),'sha256':sha256(p)} for p in files],'paid_retries':0,'missing_rounds_imputed':False})
    attempts=c['round']+1
    atomic_json(run/'execution_exit.json',{'status':'native_final_attempt_failed' if attempts==5 else 'native_early_abort','planned_rounds':5,'attempted_rounds':attempts,'completed_trajectories':c['round'],'failed_round_indices':[c['round']],'unattempted_round_indices':list(range(attempts,5)),'model_calls':c['calls'],'finished_stages':c['round']*5+1,'native_loop_idx_at_failure':c['round'],'native_step_idx_at_failure':1,'native_five_attempt_budget_complete':attempts==5,'constructor_abort_evidence_sha256':sha256(run/'constructor_abort_evidence_v3.json'),'native_source_returned':False,'full_original_paper_reproduced':False})
    validate(run,require_replay=False);print('OBSERVED_ABORT_EXTRACTED',trial,attempts,flush=True)

def replay(trial):
    import importlib.util,urllib.error,urllib.request
    from alpha_evolve.fidelity_transport_v2 import retry_stale_read
    from validate_publication_replay import compare
    from finalize_alphaagent_terminal_v2 import trajectories
    c=CASES[trial];original=PRIVATE/run_name(trial);target=PRIVATE/replay_name(trial);done=validate(original,require_replay=False)
    if target.exists():raise ValueError('Preserve existing replay attempt')
    failed=json.loads((audit_path(trial)/'failed_request.json').read_text());driver_path=ROOT/'scripts/run_alphaagent_rounds_v2.py'
    if sha256(driver_path)!=json.loads((original/'execution_recipe.json').read_text())['wrapper_sha256']:raise ValueError('Original driver changed')
    spec=importlib.util.spec_from_file_location('alpha_observed_v3_original_driver',driver_path);driver=importlib.util.module_from_spec(spec);spec.loader.exec_module(driver)
    witness=[]
    class WitnessReplay(ReadOnlyReplay):
        def __init__(self,root,*args,**kwargs):
            def initialize():
                with (Path(root)/'project_spend.lock').open('a+') as lock:
                    fcntl.flock(lock,fcntl.LOCK_EX);super(WitnessReplay,self).__init__(root,*args,**kwargs)
            retry_stale_read(initialize)
        def request(self,endpoint,payload,**kwargs):
            envelope={'endpoint':endpoint,'request':{**payload,'provider':{'order':[self.provider],'allow_fallbacks':False}}}
            if identity(envelope)==c['key']:
                if envelope!=failed or len([r for r in self.request_trace if r['endpoint']=='chat/completions'])!=c['calls']:raise ValueError('Failed request prefix changed')
                entry=self.frozen_state['calls'][c['key']]
                if entry['pid']!=c['pid'] or entry['status']!='reserved' or entry['reserved_usd']!=c['reservation']:raise ValueError('Failure reservation changed')
                witness.append({'request_hash':c['key'],'exact_envelope_match':True,'observed_http_status':400,'network_retry':False})
                raise urllib.error.HTTPError('https://openrouter.ai/api/v1/chat/completions',400,'Bad Request',None,None)
            return super().request(endpoint,payload,**kwargs)
    driver.ReadOnlyReplay=WitnessReplay
    def forbidden(*args,**kwargs):raise RuntimeError('Observed replay cannot send HTTP requests')
    urllib.request.urlopen=forbidden
    sys.argv=[str(driver_path),'--offline','--trial','paper_gpt35','--replicate',str(trial),'--output-name',target.name]
    try:driver.main()
    except BaseException as error:
        if type(error).__name__!='MeteredStop' or not isinstance(error.__cause__,urllib.error.HTTPError) or error.__cause__.code!=400 or len(witness)!=1:raise
        frame=error.__traceback__;instance=None
        while frame:
            if frame.tb_frame.f_code.co_filename==str(driver_path) and frame.tb_frame.f_code.co_name=='main':instance=frame.tb_frame.f_locals['instance']
            frame=frame.tb_next
        if instance is None or (instance.loop_idx,instance.step_idx,len(instance.trace.hist))!=(c['round'],1,c['round']):raise ValueError('Replayed failure state changed')
        atomic_json(target/'trajectories.json',trajectories(instance))
    else:raise ValueError('Observed failure was not reproduced')
    errors=[];maximum=[0.0];proofs={}
    for name in ['model_calls.json','embedding_calls.json','trajectories.json','stages.json']:
        a=json.loads((original/name).read_text());b=json.loads((target/name).read_text())
        if name=='trajectories.json':
            a=[{k:v for k,v in r.items() if k not in ['workspace','factor_workspaces']} for r in a];b=[{k:v for k,v in r.items() if k not in ['workspace','factor_workspaces']} for r in b]
        elif name=='stages.json':
            a=[{k:v for k,v in r.items() if k!='started_utc'} for r in a];b=[{k:v for k,v in r.items() if k!='started_utc'} for r in b]
        compare(a,b,name,errors,maximum);proofs[name]={'original_sha256':sha256(original/name),'replay_sha256':sha256(target/name)}
    atomic_json(target/'execution_exit.json',{'status':'observed_constructor_abort_replayed','attempted_rounds':done['attempted_rounds'],'unattempted_round_indices':done['unattempted_round_indices'],'witness':witness,'new_network_calls':0})
    result={'status':'pass' if not errors else 'fail','trial':'paper_gpt35','replicate':trial,'attempted_rounds':done['attempted_rounds'],'planned_rounds':5,'trajectories':c['round'],'failed_round_indices':done['failed_round_indices'],'unattempted_round_indices':done['unattempted_round_indices'],'native_five_attempt_budget_complete':done['native_five_attempt_budget_complete'],'finished_stages':done['finished_stages'],'constructor_abort_evidence_sha256':sha256(original/'constructor_abort_evidence_v3.json'),'observed_failure_witness':witness,'artifact_hashes':proofs,'difference_count':len(errors),'differences':errors[:50],'maximum_numeric_difference':maximum[0],'network_calls':0,'ledger_mutations':0,'replay_driver_sha256':sha256(Path(__file__)),'executed_native_wrapper_sha256':sha256(driver_path),'full_original_paper_reproduced':False,'scope':'Every observed returned response, embedding, native financial history and exact failed request is replayed. The HTTP400 is an observed stimulus, not a new upstream response. Unattempted rounds are not fabricated.'}
    atomic_json(original/replay_filename(trial),result)
    if errors:raise SystemExit(1)
    validate(original);print('OBSERVED_CONSTRUCTOR_ABORT_REPLAY_PASS',trial,json.dumps(result),flush=True)
