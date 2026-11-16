#!/usr/bin/env python3
"""Reconstruct observed Quanta control flow using only frozen replies/results."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,contextvars,hashlib,importlib.util,json,os,pickle,random,socket,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from alpha_evolve.openrouter_budget import sha256,atomic_json
from alpha_evolve.publication_replay import ReadOnlyReplay
from validate_publication_replay import compare
from quanta_walltime_reconstruction_v3 import identity,task_key,select_identity,checked_cache_bytes,assert_recorded_request,assert_boundary_counts,permit_library_process
SETUP=ROOT/'artifacts/fidelity_completion_v2/quanta_reconstruction_setup_20260919_0337/v3'
PROTOCOL=ROOT/'paper_runs/fidelity_completion_v2/quanta_walltime_reconstruction_protocol_v3.json'
CTX=contextvars.ContextVar('native_trajectory_identity_context',default=None)
class BoundaryReached(BaseException):pass
class ReconstructionRefused(BaseException):pass

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--construction-only',action='store_true');args=parser.parse_args()
    if sha256(PROTOCOL)!=sha256(SETUP/'frozen_protocol.json'):raise ValueError('Frozen reconstruction scope changed')
    scope=json.loads(PROTOCOL.read_text());original=ROOT/scope['original_run'];out=ROOT/(scope['probe_run']+('_constructor_readiness' if args.construction_only else ''))
    if out.exists():raise ValueError('Preserve and diagnose existing reconstruction attempt; never overwrite')
    for row in scope['bindings']:
        if sha256(ROOT/row['path'])!=row['sha256']:raise ValueError('Reconstruction dependency changed: '+row['path'])
    out.mkdir();source_path=ROOT/'scripts/run_quantaalpha_paper_parameters_v2.py'
    original_chat=json.loads((ROOT/scope['chat_path']).read_text());original_embed=json.loads((ROOT/scope['embedding_path']).read_text());original_quality=json.loads((ROOT/scope['quality_path']).read_text());original_pool=json.loads((ROOT/scope['pool_path']).read_text())
    chat_keys=[r['request_hash'] for r in original_chat];embedding_keys=[r['request_hash'] for r in original_embed];orphan=scope['orphan']
    used={'chat':0,'embedding':0,'orphan':0};visited_loops=[];visited_pools=[];cache_events=[];verified_cache={};hooks_installed=False;original_popen=subprocess.Popen
    def deny(*a,**k):raise ReconstructionRefused('Network or uncached subprocess/model execution forbidden')
    socket.socket.connect=deny;socket.create_connection=deny;os.system=deny
    def safe_popen(args,*a,**kw):
        frame=sys._getframe(1);metadata={};library=None
        while frame is not None:
            if frame.f_globals.get('__name__')=='ctypes.util' and str(Path(frame.f_code.co_filename).resolve())==scope['ctypes_util_source']['path']:
                if frame.f_code.co_name=='find_library':library=frame.f_locals.get('name')
                if frame.f_code.co_name in ['_findLib_gcc','_findLib_ld','_get_soname'] and not metadata:
                    metadata={'stdlib_verified':True,'function':frame.f_code.co_name,'temporary_output':getattr(frame.f_locals.get('temp'),'name',None),'soname_file':frame.f_locals.get('f')}
                    library=frame.f_locals.get('name',library)
            frame=frame.f_back
        if permit_library_process(args,shell=kw.get('shell',False),executable=kw.get('executable'),library=library,**metadata):
            with (out/'library_discovery_events.jsonl').open('a') as f:f.write(json.dumps({'function':metadata.get('function','ldconfig'),'library':library,'command':args,'scope':'ctypes library metadata only; no factor/model execution'})+'\n')
            return original_popen(args,*a,**kw)
        return deny(args,*a,**kw)
    subprocess.Popen=safe_popen
    def rng_state():
        import numpy as np
        n=np.random.get_state()
        return {'python':random.getstate(),'numpy':[n[0],n[1].tolist(),int(n[2]),int(n[3]),float(n[4])]}
    def recompare(a,b,label):
        errors=[];maximum=[0.0];compare(a,b,label,errors,maximum)
        if errors or maximum[0]!=0:raise ReconstructionRefused(label+' differs: '+str(errors[:3]))
    def stop(kind,details):
        try:
            chats=json.loads((out/'model_calls.json').read_text());embeds=json.loads((out/'embedding_calls.json').read_text());quality=json.loads((out/'quality_gate_events.json').read_text());pool=json.loads((out/'log/trajectory_pool.json').read_text())
            assert_boundary_counts(len(chats),len(embeds),len(quality),len(pool['trajectories']),len(visited_loops),scope)
            recompare(original_chat,chats[:len(original_chat)],'all_recorded_chat_requests')
            recompare(original_embed,embeds,'all_recorded_embedding_requests')
            recompare(original_quality,quality[:len(original_quality)],'all_recorded_quality_events')
            a=dict(original_pool);b=dict(pool);a.pop('saved_at',None);b.pop('saved_at',None);recompare(a,b,'all_original_pool_fields_except_save_time')
            for cache_key in verified_cache:
                row=scope['cache_artifacts'][cache_key]
                if sha256(ROOT/row['copy'])!=row['sha256']:raise ValueError('Reused cache bytes changed during reconstruction')
            if chats[-1]['request_hash']!=orphan['request_hash'] or used['orphan']!=1 or len(visited_pools)!=scope['pool_count']:raise ValueError('Durable orphan or native identity trace missing')
            expected_loops=list(scope['loop_ids'].values());expected_pools=list(scope['pool_ids'].values())
            if sorted(visited_loops)!=sorted(expected_loops) or sorted(visited_pools)!=sorted(expected_pools):raise ValueError('Loop/pool identity populations differ')
        except (Exception,ReconstructionRefused) as error:
            atomic_json(out/'reconstruction_refusal.json',{'boundary_kind':kind,'details':details,'reason':str(error),'chat_requests_returned':used['chat'],'embedding_requests_returned':used['embedding'],'orphan_reuses':used['orphan'],'visited_loop_count':len(visited_loops),'visited_pool_count':len(visited_pools),'new_model_calls':0,'native_factor_or_backtest_execution':0,'full_source_completion_claim':False})
            raise ReconstructionRefused('Incomplete reconstruction at '+kind+': '+str(error)) from error
        state=rng_state();atomic_json(out/'reconstructed_rng_state.json',state)
        result={'status':'observed_state_reconstructed_stopped_before_uncached_future_work','recorded_at_utc':datetime.now(timezone.utc).isoformat(),'boundary_kind':kind,'boundary_details':details,'recorded_chats_matched':scope['chat_count'],'additional_durable_orphan_reused':1,'recorded_embeddings_matched':scope['embedding_count'],'recorded_quality_events_matched':scope['quality_event_count'],'pool_entries_matched':scope['pool_count'],'loop_ids_preserved':visited_loops,'pool_ids_preserved':visited_pools,'cache_reuse_events':cache_events,'python_numpy_rng_reconstructed_from_source_control_flow':True,'original_in_memory_rng_snapshot_available':False,'rng_state_sha256':sha256(out/'reconstructed_rng_state.json'),'ignored_metadata':['trajectory_pool.saved_at only'],'protocol_sha256':sha256(PROTOCOL),'script_sha256':sha256(Path(__file__)),'model_calls_sha256':sha256(out/'model_calls.json'),'embedding_calls_sha256':sha256(out/'embedding_calls.json'),'quality_events_sha256':sha256(out/'quality_gate_events.json'),'pool_sha256':sha256(out/'log/trajectory_pool.json'),'new_model_calls':0,'native_factor_or_backtest_execution':0,'ledger_cache_journal_mutations':0,'source_continuation_submitted':False,'full_source_completion_claim':False,'economic_credit':False}
        atomic_json(out/'reconstruction_validation.json',result)
        raise BoundaryReached('Exact recorded state reconstructed; stopped before '+kind)
    class Meter(ReadOnlyReplay):
        def __init__(self,*a,**k):super().__init__(*a,**k);self.sequence_index=0
        def cached_response(self,key):
            if key!=orphan['request_hash']:return super().cached_response(key)
            if self.frozen_state['calls'].get(key)!=orphan['entry']:raise ReconstructionRefused('Quanta orphan identity/status/charge changed')
            path=ROOT/orphan['copy']
            if sha256(path)!=orphan['copy_sha256']:raise ReconstructionRefused('Frozen orphan body changed')
            hit=orphan['journal_matches'][0]
            with self.journal.open('rb') as f:f.seek(hit['offset']);line=f.readline()
            if hashlib.sha256(line).hexdigest()!=hit['sha256'] or line!=path.read_bytes():raise ReconstructionRefused('Canonical orphan journal changed')
            used['orphan']+=1;return json.loads(line)
        def request(self,endpoint,payload,**kwargs):
            envelope={'endpoint':endpoint,'request':{**payload,'provider':{'order':[self.provider],'allow_fallbacks':False}}};base=identity(envelope)
            if base in self.recovery_map:envelope['technical_recovery']={'original_request_hash':base,'attempt':self.recovery_map[base]['attempt']}
            key=identity(envelope)
            try:kind=assert_recorded_request(endpoint,self.sequence_index,key,chat_keys,embedding_keys,orphan['request_hash'])
            except ValueError as error:
                atomic_json(out/'request_prefix_mismatch.json',{'endpoint':endpoint,'index':self.sequence_index,'actual_key':key,'envelope':envelope,'error':str(error)});raise ReconstructionRefused(str(error)) from error
            if kind=='future_boundary':
                atomic_json(out/'future_request_envelope.json',envelope)
                stop('next_api_request',{'endpoint':endpoint,'index':self.sequence_index,'request_hash':key,'currently_indexed_status':self.frozen_state['calls'].get(key,{}).get('status'),'genuinely_absent_from_frozen_ledger':key not in self.frozen_state['calls']})
            result=super().request(endpoint,payload,**kwargs);self.sequence_index+=1
            used['chat' if endpoint=='chat/completions' else 'embedding']+=1
            return result
    spec=importlib.util.spec_from_file_location('frozen_quanta_state_reconstruction_driver',source_path);driver=importlib.util.module_from_spec(spec);spec.loader.exec_module(driver);driver.ReadOnlyReplay=Meter
    def install_hooks():
        nonlocal hooks_installed
        if hooks_installed:raise ReconstructionRefused('Reconstruction hooks installed twice')
        before=rng_state()
        import quantaalpha.pipeline.factor_mining as mining
        from quantaalpha.pipeline.evolution.trajectory import StrategyTrajectory
        from quantaalpha.pipeline.evolution.controller import EvolutionController
        from quantaalpha.factors.coder.factor import FactorFBWorkspace
        from quantaalpha.factors.runner import QlibFactorRunner
        from quantaalpha.components.runner import CachedRunner
        from quantaalpha.factors.workspace import QlibFBWorkspace
        from quantaalpha.core.conf import RD_AGENT_SETTINGS
        from quantaalpha.llm.config import LLM_SETTINGS
        if RD_AGENT_SETTINGS.multi_proc_n!=1 or not RD_AGENT_SETTINGS.cache_with_pickle or LLM_SETTINGS.use_auto_chat_cache_seed_gen:raise ReconstructionRefused('Unaccounted parent-process RNG/cache configuration')
        original_task=mining._run_evolution_task;original_pool_create=EvolutionController.create_trajectory_from_loop_result;original_init=StrategyTrajectory.__init__;assign=CachedRunner.assign_cached_result
        def run_task(*a,**k):
            task=k.get('task',a[0] if a else None);key=task_key(task['direction_id'],task['round_idx'],task['phase'])
            try:tid=select_identity('loop',key,scope['loop_ids'],scope['pool_ids'])
            except ValueError:stop('unseen_loop_task',{'task_key':key})
            if tid in visited_loops:raise ReconstructionRefused('Repeated existing loop')
            visited_loops.append(tid);token=CTX.set(('loop',key))
            try:return original_task(*a,**k)
            finally:CTX.reset(token)
        def create_pool(self,*a,**k):
            task=k.get('task',a[0] if a else None);key=task_key(task['direction_id'],task['round_idx'],task['phase'])
            try:tid=select_identity('pool',key,scope['loop_ids'],scope['pool_ids'])
            except ValueError:stop('unseen_pool_entry',{'task_key':key})
            if tid in visited_pools:raise ReconstructionRefused('Repeated existing pool entry')
            token=CTX.set(('pool',key))
            try:result=original_pool_create(self,*a,**k)
            finally:CTX.reset(token)
            if result.trajectory_id!=tid:raise ReconstructionRefused('Native pool identity differs')
            visited_pools.append(tid);return result
        def generate_id(direction_id,round_idx,phase,timestamp=None):
            context=CTX.get();key=task_key(direction_id,round_idx,phase)
            if context is None or context[1]!=key:raise ReconstructionRefused('Unbound native timestamp identity request')
            return select_identity(context[0],key,scope['loop_ids'],scope['pool_ids'])
        def initialize(self,*a,**k):
            original_init(self,*a,**k)
            if self.trajectory_id not in original_pool['trajectories']:raise ReconstructionRefused('New pool identity forbidden during reconstruction')
            self.created_at=original_pool['trajectories'][self.trajectory_id]['created_at']
        def cache_load(kind,key):
            cache_key=kind+'/'+str(key)+'.pkl';row=scope['cache_artifacts'].get(cache_key)
            if row is None:stop('uncached_'+kind,{'cache_key':cache_key})
            state=rng_state()
            if cache_key not in verified_cache:
                try:data=checked_cache_bytes(row,ROOT);value=pickle.loads(data)
                except Exception as error:raise ReconstructionRefused('Preserved cache integrity/read failure: '+cache_key) from error
                verified_cache[cache_key]=True
            else:
                try:
                    with (ROOT/row['copy']).open('rb') as f:value=pickle.load(f)
                except Exception as error:raise ReconstructionRefused('Preserved cache reread failure: '+cache_key) from error
            if rng_state()!=state:raise ReconstructionRefused('Cache load changed parent RNG state')
            cache_events.append({'cache_key':cache_key,'preserved_copy':row['copy'],'sha256':row['sha256'],'native_execution':False,'rng_unchanged':True})
            return value
        def factor_execute(self,data_type='Debug'):
            key=self.hash_func(data_type)
            if key is None:
                if not self.raise_exception and 'factor.py' not in self.code_dict:return self.FB_CODE_NOT_SET,None
                raise ReconstructionRefused('Noncached exception-mode factor execution needs separate evidence')
            return cache_load('quantaalpha.factors.coder.factor.execute',key)
        def codes(exp):return [getattr(x,'code_dict',{}).get('factor.py') if x is not None else None for x in getattr(exp,'sub_workspace_list',[])]
        def develop(self,exp,use_local=True):
            key=CachedRunner.get_cache_key(self,exp,use_local=use_local);cached=cache_load('quantaalpha.factors.runner.develop',key)
            if codes(exp)!=codes(cached):raise ReconstructionRefused('Native feedback cache key matched but factor code differs')
            state=rng_state();result=assign(self,exp,cached_res=cached)
            if rng_state()!=state:raise ReconstructionRefused('Cached feedback assignment changed parent RNG')
            return result
        def forbid_native(*a,**k):raise ReconstructionRefused('No native backtest execution is allowed in this probe')
        mining._run_evolution_task=run_task;EvolutionController.create_trajectory_from_loop_result=create_pool;StrategyTrajectory.generate_id=staticmethod(generate_id);StrategyTrajectory.__init__=initialize
        FactorFBWorkspace.execute=factor_execute;QlibFactorRunner.develop=develop;QlibFBWorkspace.execute=forbid_native
        if rng_state()!=before:raise ReconstructionRefused('Hook installation changed seeded startup RNG state')
        hooks_installed=True;atomic_json(out/'hook_installation.json',{'status':'installed_after_original_source_seed_and_import_initialization','rng_state_sha256':identity(before),'native_module_files_unchanged':True,'multi_proc_n':RD_AGENT_SETTINGS.multi_proc_n,'use_auto_chat_cache_seed_gen':LLM_SETTINGS.use_auto_chat_cache_seed_gen})
    base_atomic=driver.atomic_json
    def observed_atomic(path,value):
        result=base_atomic(path,value)
        if Path(path)==out/'parameter_wiring.json' and not hooks_installed:install_hooks()
        return result
    driver.atomic_json=observed_atomic
    sys.argv=[str(source_path),'--offline','--output-name',out.name]+(['--probe'] if args.construction_only else [])
    try:driver.main()
    except BoundaryReached:
        if not (out/'reconstruction_validation.json').exists() or (out/'execution_exit.json').exists():raise ReconstructionRefused('Bounded probe certification missing or overclaimed')
        print('QUANTA_RECONSTRUCTION_PREFIX_PASS_NO_NEW_MODEL_OR_FACTOR_EXECUTION',flush=True)
    else:
        if not args.construction_only:raise ReconstructionRefused('Unexpected complete source return; inspect before any completion claim')
        construction=json.loads((out/'construction_probe.json').read_text())
        if construction.get('paid_calls')!=0 or any(used.values()) or not hooks_installed:raise ReconstructionRefused('Constructor readiness performed unexpected source work')
        atomic_json(out/'software_readiness.json',{'status':'native_constructor_and_rng_neutral_hook_installation_pass','protocol_sha256':sha256(PROTOCOL),'probe_script_sha256':sha256(Path(__file__)),'hook_installation_sha256':sha256(out/'hook_installation.json'),'new_model_calls':0,'native_factor_or_backtest_execution':0,'actual_prefix_reconstruction_completed':False})
        print('QUANTA_RECONSTRUCTION_SOFTWARE_READINESS_PASS_NOT_SOURCE_RUNTIME',flush=True)
if __name__=='__main__':main()
