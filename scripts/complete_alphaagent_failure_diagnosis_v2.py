#!/usr/bin/env python3
"""Complete only tokenizer metadata after the exact failed envelope was saved."""
from pathlib import Path
import sys,json,hashlib,socket,fcntl,os
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from alpha_evolve.openrouter_budget import atomic_json,sha256
from alpha_evolve.publication_replay import ReadOnlyReplay

def identity(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def main():
    audit=ROOT/'artifacts/fidelity_completion_v2/alpha_trial08_failure_20260918'
    run=ROOT/'artifacts/fidelity_completion_v2/alphaagent_rounds_paper_gpt35_08'
    assert not (audit/'diagnosis.json').exists()
    source=(audit/'diagnostic_executed_source.py').read_text()
    assert sha256(audit/'diagnostic_executed_source.py')==sha256(ROOT/'scripts/diagnose_alphaagent_final_http400_v2.py')
    # The completed native reconstruction durably saved this only after index110,
    # exact failed-key equality and every preceding cached-key equality passed.
    assert "assert index<len(calls) and key==calls[index]['request_hash']" in source
    assert source.index('assert key==failed_key')<source.index("atomic_json(OUT/'failed_request.json'")<source.index('enc=tiktoken.encoding_for_model')
    envelope=json.loads((audit/'failed_request.json').read_text());key=identity(envelope)
    assert key=='aa8d6503fc69f4c4f42d5561fc1c6110baeb88181c4d033efb85fe0fe7d64b91'
    log=(audit/'diagnostic.log').read_text()
    assert log.count('has a duplicated subtree size')==66 and log.count('Fail to parse expr')==6
    assert log.count('No network permitted during diagnosis')==10
    assert 'Failed to create chat completion after 10 retries.' in log
    with (ROOT/'runs/economic_fidelity/openrouter/project_spend.lock').open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        meter=ReadOnlyReplay(ROOT/'runs/economic_fidelity/openrouter','unused','openai/gpt-3.5-turbo',study='fidelity_v2_alphaagent_source_search',study_cap=20)
    calls=json.loads((run/'model_calls.json').read_text());assert len(calls)==110
    proofs=[]
    for row in calls[38:]:
        cached=meter.cached_response(row['request_hash'])
        assert identity({k:cached[k] for k in ['endpoint','request']})==row['request_hash']
        assert cached['response'].get('id')==row['response_id']
        proofs.append({k:row[k] for k in ['index','request_hash','response_id']})
    entry=meter.frozen_state['calls'][key];assert entry['pid']==2814071 and entry['status']=='reserved'
    def forbidden(*a,**kw):raise RuntimeError('Tokenizer metadata completion must be offline')
    socket.create_connection=forbidden;socket.socket.connect=forbidden
    import tiktoken
    enc=tiktoken.encoding_for_model('gpt-3.5-turbo');body=envelope['request']
    tokens=[dict(role=m['role'],content_tokens=len(enc.encode(m['content'])),characters=len(m['content'])) for m in body['messages']]
    metadata=json.loads((audit/'openrouter_gpt35_endpoints.json').read_text())
    endpoint=[r for r in metadata['data']['endpoints'] if r['provider_name']=='OpenAI'];assert len(endpoint)==1
    n=sum(r['content_tokens'] for r in tokens)+body['max_tokens'];limit=endpoint[0]['context_length']
    assert n>limit
    result={'status':'exact_failed_request_reconstructed_without_network','trial':8,'attempted_round_index':4,
        'completed_prior_trajectories':4,'construction_returned_response_count':72,'duplication_rejections':66,'expression_parse_rejections':6,
        'total_completed_chat_calls':110,'failed_request_hash':key,'failed_reservation':entry,
        'checkpoint_sha256':sha256(run/'log/__session__/4/0_factor_propose'),
        'exact_cached_prefix_requests':proofs,'message_content_token_counts':tokens,
        'requested_max_tokens':body['max_tokens'],'content_tokens_plus_requested_output':n,
        'archived_endpoint_context_length':limit,'excess_before_chat_framing':n-limit,
        'token_count_scope':'Content-only tokenizer count plus requested output; message framing adds tokens. This is not the missing provider error response.',
        'provider_error_body_available':False,'http_status_from_original_traceback':400,
        'cause_claim':'The exactly reconstructed request exceeds the archived current provider context allowance. This is consistent with context overflow, but the original provider error body was not retained and the exact HTTP400 explanation remains unobserved.',
        'diagnostic_execution_note':'The original diagnostic reproduced all72 native constructor responses and saved the hash-matching failed envelope. Its subsequent optional tokenizer load attempted10 downloads blocked by the socket guard because the cache environment variable was absent. Only tokenizer/postprocessing metadata was completed separately using the existing central cache. The native search and response matching were not rerun.',
        'reconstruction_source_sha256':sha256(audit/'diagnostic_executed_source.py'),
        'reconstruction_log_sha256':sha256(audit/'diagnostic.log'),
        'metadata_completion_source_sha256':sha256(Path(__file__)),
        'network_calls':0,'blocked_tokenizer_download_attempts':10,'ledger_mutations':0}
    atomic_json(audit/'diagnosis.json',result)
    print('EXACT_FAILED_REQUEST_PLUS_OFFLINE_TOKEN_METADATA_PASS',n,limit)
if __name__=='__main__':main()
