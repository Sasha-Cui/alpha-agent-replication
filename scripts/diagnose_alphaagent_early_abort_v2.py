#!/usr/bin/env python3
"""Bind trial12's logged failed request without retrying a paid HTTP400."""
from pathlib import Path
import sys,json,hashlib,fcntl,copy,sqlite3,socket,shutil,subprocess
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from alpha_evolve.publication_replay import ReadOnlyReplay
from alpha_evolve.openrouter_budget import atomic_json,sha256
PRIVATE=ROOT/'artifacts/fidelity_completion_v2'
RUN=PRIVATE/'alphaagent_rounds_paper_gpt35_12'
OUT=PRIVATE/'alpha_trial12_early_abort_20260918'
KEY='c8061be5982779ddeff6c1fbc67d773a431b2e2f6228817d8837094373988a9b'

def identity(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def main():
    if (OUT/'diagnosis.json').exists():raise ValueError('Preserve completed diagnosis')
    paths=list(RUN.glob('*.json'))+list((RUN/'log/__session__').glob('*/*'))+[RUN.with_suffix('.log')]
    paths += list((RUN/'log').rglob('common_logs.log'))
    paths += [ROOT/'scripts'/n for n in ['run_alphaagent_rounds_v2.py','replay_alphaagent_rounds_v2.py','export_alphaagent_used_factors_v2.py']]
    paths += [ROOT/'src/alpha_evolve/publication_llm.py']
    rows=[]
    for p in paths:
        if not p.is_file():continue
        q=OUT/'original'/p.relative_to(ROOT);q.parent.mkdir(parents=True,exist_ok=True)
        if q.exists():raise ValueError('Preserve earlier extraction attempt')
        shutil.copy2(p,q);assert sha256(q)==sha256(p)
        rows.append(dict(path=str(p.relative_to(ROOT)),copy=str(q.relative_to(ROOT)),sha256=sha256(p)))
    atomic_json(OUT/'preservation_manifest.json',{'files':rows})
    terminal=subprocess.check_output(['/opt/slurm/current/bin/sacct','-j','26502926_12','--format=JobID%30,JobIDRaw,State,ExitCode,Elapsed,MaxRSS','--parsable2','--noheader'],text=True)
    assert '26502926_12|26545165|FAILED|1:0|' in terminal
    (OUT/'terminal_job.txt').write_text(terminal)
    stages=json.loads((RUN/'stages.json').read_text());calls=json.loads((RUN/'model_calls.json').read_text())
    assert len(calls)==215 and stages[-1]['loop_index']==2 and stages[-1]['stage']=='factor_construct' and stages[-1]['completed'] is False
    assert stages[-1]['model_calls_before']==73 and stages[-1]['model_calls_after']==215
    log_path=RUN/'log/r/llm_messages/3887669/common_logs.log';text=log_path.read_text()
    system_at=text.rindex('Role:system\nContent: ')+len('Role:system\nContent: ')
    user_at=text.rindex('Role:user\nContent: ')
    rawsystem=text[system_at:user_at];rawuser=text[user_at+len('Role:user\nContent: '):]
    root=ROOT/'runs/economic_fidelity/openrouter'
    with (root/'project_spend.lock').open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        meter=ReadOnlyReplay(root,'unused','openai/gpt-3.5-turbo',study='fidelity_v2_alphaagent_source_search',study_cap=20)
    entry=meter.frozen_state['calls'][KEY]
    assert entry['pid']==3887669 and entry['status']=='reserved' and entry['reserved_usd']==.028655
    cached=meter.cached_response(calls[-1]['request_hash']);assert cached['response'].get('id')==calls[-1]['response_id']
    template=copy.deepcopy(cached['request']);template['seed']=1990215
    matched=[]
    for a in range(5):
        for b in range(5):
            # Enumerate ONLY suffix formatting newlines added by the source log.
            if a and not rawsystem.endswith('\n'*a):continue
            if b and not rawuser.endswith('\n'*b):continue
            body=copy.deepcopy(template);body['messages']=[{'role':'system','content':rawsystem[:-a] if a else rawsystem},{'role':'user','content':rawuser[:-b] if b else rawuser}]
            env={'endpoint':'chat/completions','request':body}
            if identity(env)==KEY:matched.append((env,a,b))
    assert len(matched)==1,len(matched)
    envelope,a,b=matched[0];atomic_json(OUT/'failed_request.json',envelope)
    with sqlite3.connect('file:'+str(root/'response_cache.sqlite3')+'?mode=ro',uri=True) as c:
        n=c.execute('SELECT COUNT(*) FROM responses WHERE request_hash=?',(KEY,)).fetchone()[0]
    length=(root/'cohort_responses.jsonl').stat().st_size;matches=0
    with (root/'cohort_responses.jsonl').open('rb') as f:
        while f.tell()<length:
            line=f.readline()
            if KEY.encode() in line and json.loads(line).get('request_hash')==KEY:matches+=1
    assert n==matches==0
    def forbidden(*a,**kw):raise RuntimeError('Diagnosis cannot access the network')
    socket.create_connection=forbidden;socket.socket.connect=forbidden
    import tiktoken
    enc=tiktoken.encoding_for_model('gpt-3.5-turbo')
    counts=[len(enc.encode(m['content'])) for m in envelope['request']['messages']]
    metadata=PRIVATE/'alpha_trial08_failure_20260918/openrouter_gpt35_endpoints.json'
    endpoints=json.loads(metadata.read_text())['data']['endpoints'];limit=next(e['context_length'] for e in endpoints if e['provider_name']=='OpenAI')
    total=sum(counts)+envelope['request']['max_tokens'];assert total>limit
    result={'status':'exact_logged_failed_request_bound_no_retry','source_run':RUN.name,'attempted_rounds':3,'planned_rounds':5,
        'completed_trajectories':2,'failed_round_indices':[2],'unattempted_round_indices':[3,4],
        'successful_http_chat_responses':215,'last_constructor_returned_responses':142,'failed_request_hash':KEY,'failed_reservation':entry,
        'exact_source_log_sha256':sha256(log_path),'source_log_formatting_newlines_removed':{'system':a,'user':b},
        'reconstruction':'Literal final system/user log messages, source request defaults from the previous cached envelope, next fixed seed, and a unique cryptographic match to the reserved failed request. No regenerated factor, truncated prompt or speculative provider message.',
        'content_tokens':counts,'requested_output_tokens':envelope['request']['max_tokens'],'content_plus_requested_output_tokens':total,
        'archived_current_context_length':limit,'endpoint_metadata_sha256':sha256(metadata),
        'cause_boundary':'Request exceeds the archived current context allowance; original provider error body absent. Context overflow is supported, but its precise HTTP400 explanation is not observed.',
        'sqlite_failed_response_rows':n,'journal_failed_response_envelopes':matches,'journal_bytes_scanned':length,
        'network_calls':0,'ledger_mutations':0,'paid_retries':0,'native_five_attempt_budget_complete':False,
        'strict_primary_eligibility':False,'script_sha256':sha256(Path(__file__))}
    atomic_json(OUT/'diagnosis.json',result)
    print(json.dumps({k:v for k,v in result.items() if k not in ['reconstruction','cause_boundary','failed_reservation']}))
if __name__=='__main__':main()
