#!/usr/bin/env python3
"""Read-only reconstruction of trial08's failed final construction request."""
from pathlib import Path
import sys, os, json, pickle, hashlib, fcntl, socket, copy
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1]
PRIVATE=ROOT/'artifacts/fidelity_completion_v2'
RUN=PRIVATE/'alphaagent_rounds_paper_gpt35_08'
OUT=PRIVATE/'alpha_trial08_failure_20260918'
SOURCE=PRIVATE/'dependencies/alphaagent_95e478'
sys.path[:0]=[str(ROOT/'src'),str(SOURCE)]
from alpha_evolve.publication_replay import ReadOnlyReplay
from alpha_evolve.openrouter_budget import atomic_json, sha256

def identity(x):
    return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def main():
    os.environ.update(OPENAI_API_KEY='unused-offline', CHAT_OPENAI_API_KEY='unused-offline',
        OPENAI_BASE_URL='https://openrouter.ai/api/v1')
    os.chdir(OUT)
    def forbidden(*a,**kw):
        raise AssertionError('No network permitted during diagnosis')
    socket.create_connection=forbidden
    socket.socket.connect=forbidden
    from rdagent.oai.llm_utils import APIBackend
    from rdagent.oai.llm_conf import LLM_SETTINGS
    from rdagent.log import rdagent_logger as logger
    import tiktoken
    logger.set_trace_path(OUT/'diagnostic_log')
    LLM_SETTINGS.openai_api_key='unused-offline'
    LLM_SETTINGS.chat_model='gpt-3.5-turbo'
    LLM_SETTINGS.embedding_model='text-embedding-3-small'
    LLM_SETTINGS.openai_base_url='https://openrouter.ai/api/v1'
    with (ROOT/'runs/economic_fidelity/openrouter/project_spend.lock').open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        meter=ReadOnlyReplay(ROOT/'runs/economic_fidelity/openrouter','unused','openai/gpt-3.5-turbo',
            study='fidelity_v2_alphaagent_source_search',study_cap=20)
    calls=json.loads((RUN/'model_calls.json').read_text())
    assert len(calls)==110
    checkpoints=RUN/'log/__session__/4/0_factor_propose'
    with checkpoints.open('rb') as f:
        instance=pickle.load(f)
    assert instance.loop_idx==4 and instance.step_idx==1 and len(instance.trace.hist)==4
    index=38
    original=APIBackend.__init__
    class MatchedFailure(BaseException): pass
    failed_key='aa8d6503fc69f4c4f42d5561fc1c6110baeb88181c4d033efb85fe0fe7d64b91'
    proofs=[]
    def sdk(**kwargs):
        nonlocal index
        body=copy.deepcopy(kwargs)
        stream=body.pop('stream',False)
        assert body.pop('model')=='gpt-3.5-turbo'
        body.update(model='openai/gpt-3.5-turbo',seed=1590000+index,
                    provider={'order':['OpenAI'],'allow_fallbacks':False})
        envelope={'endpoint':'chat/completions','request':body}
        key=identity(envelope)
        if index==110:
            assert key==failed_key,(key,failed_key)
            entry=meter.frozen_state['calls'][key]
            assert entry['pid']==2814071 and entry['study']==meter.study and entry['status']=='reserved'
            assert abs(entry['reserved_usd']-.030346)<1e-12
            atomic_json(OUT/'failed_request.json',envelope)
            enc=tiktoken.encoding_for_model('gpt-3.5-turbo')
            token_rows=[{'role':m['role'],'content_tokens':len(enc.encode(m['content'])),'characters':len(m['content'])} for m in body['messages']]
            atomic_json(OUT/'diagnosis.json',{
                'status':'exact_failed_request_reconstructed_without_network',
                'trial':8,'attempted_round_index':4,'completed_prior_trajectories':4,
                'construction_successful_response_count':72,'total_completed_chat_calls':110,
                'failed_request_hash':key,'failed_reservation':entry,'checkpoint_sha256':sha256(checkpoints),
                'exact_cached_prefix_requests':proofs,'message_content_token_counts':token_rows,
                'requested_max_tokens':body['max_tokens'],
                'content_tokens_plus_requested_output':sum(x['content_tokens'] for x in token_rows)+body['max_tokens'],
                'token_count_scope':'Tokenizer content-only count; actual chat framing adds tokens. This is not the missing provider error response.',
                'provider_error_body_available':False,'http_status_from_original_traceback':400,
                'cause_claim':'Context overflow is a candidate explanation pending endpoint metadata comparison; the original HTTP400 error body was not retained.',
                'network_calls':0,'ledger_mutations':0,'diagnostic_source_sha256':sha256(Path(__file__))})
            raise MatchedFailure()
        assert index<len(calls) and key==calls[index]['request_hash'],(index,key)
        cached=meter.cached_response(key)
        assert cached['request']==body
        response=cached['response']; choice=response['choices'][0]
        proofs.append({'index':index,'request_hash':key,'response_id':response.get('id')})
        index+=1
        content=choice['message'].get('content') or ''
        if stream:
            return iter([SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=content),finish_reason=choice.get('finish_reason'))])])
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content),finish_reason=choice.get('finish_reason'))],usage=SimpleNamespace(**response.get('usage',{})))
    def init(self,*a,**kw):
        original(self,*a,**kw)
        self.chat_client=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=sdk)))
    APIBackend.__init__=init
    try:
        instance.factor_constructor.convert(instance.loop_prev_out['factor_propose'],instance.trace)
    except MatchedFailure:
        print('EXACT_FAILURE_RECONSTRUCTION_PASS',index)
    else:
        raise AssertionError('Source unexpectedly completed final construction')
if __name__=='__main__':main()
