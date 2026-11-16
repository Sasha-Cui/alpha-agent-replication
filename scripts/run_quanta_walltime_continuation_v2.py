#!/usr/bin/env python3
"""Continue only after the actual reconstructed boundary; reuse every old model."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,contextvars,hashlib,importlib.util,json,os,pickle,random,socket,subprocess,sys,fcntl
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from alpha_evolve.openrouter_budget import sha256,atomic_json,read_key
from alpha_evolve.publication_llm import CohortOpenRouter
from quanta_walltime_continuation_v2 import load_scope,assert_boundary,assert_cached_code,assert_native_work,locked_budget_and_orphan,verify_models,finish_source,validate_completed_source,LIVE,REPLAY,REQUIRED_FILES
from quanta_walltime_continuation_v2 import PROTOCOL as CONT_PROTOCOL, SETUP as CONT_SETUP
from alpha_evolve.publication_replay import ReadOnlyReplay
from validate_publication_replay import compare
from quanta_walltime_reconstruction_v3 import identity,task_key,select_identity,checked_cache_bytes,assert_recorded_request,assert_boundary_counts,permit_library_process
SETUP=ROOT/'artifacts/fidelity_completion_v2/quanta_reconstruction_setup_20260919_0337/v4'
PROTOCOL=ROOT/'paper_runs/fidelity_completion_v2/quanta_walltime_reconstruction_protocol_v4.json'
CTX=contextvars.ContextVar('native_trajectory_identity_context',default=None)
class BoundaryReached(BaseException):pass
class ReconstructionRefused(BaseException):pass

def strict_guard(function,*a,**k):
    try:return function(*a,**k)
    except Exception as error:raise ReconstructionRefused(str(error)) from error

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--construction-only',action='store_true');parser.add_argument('--replay',action='store_true');args=parser.parse_args()
    if sha256(PROTOCOL)!=sha256(SETUP/'frozen_protocol.json'):raise ValueError('Frozen reconstruction scope changed')
    plan,scope,actual_probe=load_scope();original=ROOT/scope['original_run'];source=ROOT/'artifacts/fidelity_completion_v2'/LIVE
    out=ROOT/'artifacts/fidelity_completion_v2'/((REPLAY if args.replay else LIVE)+('_constructor_readiness' if args.construction_only else ''))
    lineage=json.loads((CONT_SETUP/'native_artifact_lineage.json').read_text());model_rows={r['cache_key']:r for r in lineage['original_model_cache_entries']}
    complete=validate_completed_source(source) if args.replay else None
    cache_index=dict(complete['cache_artifacts'] if args.replay else scope['cache_artifacts'])
    old_keys=set(scope['cache_artifacts']);all_loop_ids=dict(complete['loop_ids'] if args.replay else scope['loop_ids']);all_pool_ids=dict(complete['pool_ids'] if args.replay else scope['pool_ids'])
    target_pool=json.loads(((source if args.replay else original)/'log/trajectory_pool.json').read_text())
    gate_passed=False;network_allowed=False;native_context=[];model_events=[];cache_root=None
    original_connect=socket.socket.connect;original_connection=socket.create_connection
    locked_budget_and_orphan(scope)
    if out.exists():raise ValueError('Preserve and diagnose existing reconstruction attempt; never overwrite')
    for row in scope['bindings']:
        if sha256(ROOT/row['path'])!=row['sha256']:raise ValueError('Reconstruction dependency changed: '+row['path'])
    out.mkdir();source_path=ROOT/'scripts/run_quantaalpha_paper_parameters_v2.py'
    original_chat=json.loads((ROOT/scope['chat_path']).read_text());original_embed=json.loads((ROOT/scope['embedding_path']).read_text());original_quality=json.loads((ROOT/scope['quality_path']).read_text());original_pool=json.loads((ROOT/scope['pool_path']).read_text())
    chat_keys=[r['request_hash'] for r in original_chat];embedding_keys=[r['request_hash'] for r in original_embed];orphan=scope['orphan']
    replay_chat=json.loads((source/'model_calls.json').read_text()) if args.replay else None
    replay_embed=json.loads((source/'embedding_calls.json').read_text()) if args.replay else None
    used={'chat':0,'embedding':0,'orphan':0};visited_loops=[];visited_pools=[];cache_events=[];verified_cache={};hooks_installed=False;runtime_metadata_preload=False;original_popen=subprocess.Popen
    def deny(*a,**k):raise ReconstructionRefused('Network or uncached subprocess/model execution forbidden')
    def guarded_connect(self,*a,**k):
        if not network_allowed or args.replay:return deny()
        return original_connect(self,*a,**k)
    def guarded_connection(*a,**k):
        if not network_allowed or args.replay:return deny()
        return original_connection(*a,**k)
    socket.socket.connect=guarded_connect;socket.create_connection=guarded_connection;os.system=deny
    def safe_popen(command,*a,**kw):
        if native_context:
            context=native_context[-1]
            if not gate_passed or args.replay or Path(kw.get('cwd','')).resolve()!=Path(context['workspace']).resolve():return deny()
            return original_popen(command,*a,**kw)
        args0=command
        return metadata_popen(args0,*a,**kw)
    def metadata_popen(args,*a,**kw):
        if runtime_metadata_preload:
            if any(used.values()) or visited_loops or visited_pools or kw.get('shell',False):raise ReconstructionRefused('Runtime preload must precede all source work and use no shell')
            with (out/'runtime_import_processes.jsonl').open('a') as f:f.write(json.dumps({'command':args,'scope':'Trusted PyTables import and CPU/library metadata only; actor and native execution guards already installed'})+'\n')
            return original_popen(args,*a,**kw)
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
        nonlocal gate_passed
        if gate_passed:raise ReconstructionRefused('Unexpected attempt to repeat the original boundary gate')
        try:
            chats=json.loads((out/'model_calls.json').read_text());embeds=json.loads((out/'embedding_calls.json').read_text());quality=json.loads((out/'quality_gate_events.json').read_text());pool=json.loads((out/'log/trajectory_pool.json').read_text())
            assert_boundary_counts(len(chats),len(embeds),len(quality),len(pool['trajectories']),len(visited_loops),scope)
            recompare(original_chat,chats[:len(original_chat)],'all_recorded_chat_requests')
            recompare(original_embed,embeds,'all_recorded_embedding_requests')
            recompare(original_quality,quality[:len(original_quality)],'all_recorded_quality_events')
            for filename in ['runtime.json','parameter_wiring.json']:
                recompare(json.loads((original/filename).read_text()),json.loads((out/filename).read_text()),filename)
            left=json.loads((original/'recipe.json').read_text());right=json.loads((out/'recipe.json').read_text())
            left.pop('frozen_at_utc',None);right.pop('frozen_at_utc',None);recompare(left,right,'recipe_except_construction_timestamp')
            a=dict(original_pool);b=dict(pool);a.pop('saved_at',None);b.pop('saved_at',None);recompare(a,b,'all_original_pool_fields_except_save_time')
            for cache_key in verified_cache:
                row=cache_index[cache_key]
                if sha256(ROOT/row['copy'])!=row['sha256']:raise ValueError('Reused cache bytes changed during reconstruction')
            if chats[-1]['request_hash']!=orphan['request_hash'] or used['orphan']!=1 or len(visited_pools)!=scope['pool_count']:raise ValueError('Durable orphan or native identity trace missing')
            expected_loops=list(scope['loop_ids'].values());expected_pools=list(scope['pool_ids'].values())
            if sorted(visited_loops)!=sorted(expected_loops) or sorted(visited_pools)!=sorted(expected_pools):raise ValueError('Loop/pool identity populations differ')
        except (Exception,ReconstructionRefused) as error:
            atomic_json(out/'reconstruction_refusal.json',{'boundary_kind':kind,'details':details,'reason':str(error),'chat_requests_returned':used['chat'],'embedding_requests_returned':used['embedding'],'orphan_reuses':used['orphan'],'visited_loop_count':len(visited_loops),'visited_pool_count':len(visited_pools),'new_model_calls':0,'native_factor_or_backtest_execution':0,'full_source_completion_claim':False})
            raise ReconstructionRefused('Incomplete reconstruction at '+kind+': '+str(error)) from error
        state=rng_state();atomic_json(out/'reconstructed_rng_state.json',state)
        strict_guard(assert_boundary,kind,details,plan,sha256(out/'reconstructed_rng_state.json'),actual_probe)
        strict_guard(verify_models,lineage);budget=strict_guard(locked_budget_and_orphan,scope)
        result={'status':'observed_state_reconstructed_stopped_before_uncached_future_work','recorded_at_utc':datetime.now(timezone.utc).isoformat(),'boundary_kind':kind,'boundary_details':details,'recorded_chats_matched':scope['chat_count'],'additional_durable_orphan_reused':1,'recorded_embeddings_matched':scope['embedding_count'],'recorded_quality_events_matched':scope['quality_event_count'],'pool_entries_matched':scope['pool_count'],'loop_ids_preserved':visited_loops,'pool_ids_preserved':visited_pools,'cache_reuse_events':cache_events,'python_numpy_rng_reconstructed_from_source_control_flow':True,'original_in_memory_rng_snapshot_available':False,'rng_state_sha256':sha256(out/'reconstructed_rng_state.json'),'ignored_metadata':['trajectory_pool.saved_at','recipe.frozen_at_utc only'],'protocol_sha256':sha256(PROTOCOL),'script_sha256':sha256(Path(__file__)),'model_calls_sha256':sha256(out/'model_calls.json'),'embedding_calls_sha256':sha256(out/'embedding_calls.json'),'quality_events_sha256':sha256(out/'quality_gate_events.json'),'pool_sha256':sha256(out/'log/trajectory_pool.json'),'new_model_calls':0,'native_factor_or_backtest_execution':0,'ledger_cache_journal_mutations':0,'source_continuation_submitted':False,'full_source_completion_claim':False,'economic_credit':False}
        result.update(status='exact_original_state_and_actual_boundary_reconstructed_before_continuation',continuation_protocol_sha256=sha256(CONT_PROTOCOL),actual_probe_receipt_sha256=sha256(ROOT/plan['reconstruction_receipt']),native_artifact_lineage_sha256=sha256(CONT_SETUP/'native_artifact_lineage.json'),budget=budget,source_continuation_submitted=True)
        atomic_json(out/'continuation_prefix_gate.json',result);gate_passed=True
    class Meter(ReadOnlyReplay):
        def __init__(self,*a,**k):
            with (ROOT/'runs/economic_fidelity/openrouter/project_spend.lock').open('a+') as lock:
                fcntl.flock(lock,fcntl.LOCK_EX);super().__init__(*a,**k)
            self.sequence_index=0;self.live=None;self.live_args=a;self.live_kwargs=k
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
            nonlocal network_allowed
            if args.replay:
                expected=replay_chat if endpoint=='chat/completions' else replay_embed if endpoint=='embeddings' else None
                if expected is None or self.sequence_index>=len(expected) or expected[self.sequence_index]['request_hash']!=key:raise ReconstructionRefused('Full replay request ordinal/envelope changed')
            elif not gate_passed:
                try:kind=assert_recorded_request(endpoint,self.sequence_index,key,chat_keys,embedding_keys,orphan['request_hash'])
                except ValueError as error:raise ReconstructionRefused(str(error)) from error
                if kind=='future_boundary':raise ReconstructionRefused('An API boundary cannot replace the witnessed unfinished factor calculation')
            if args.replay or not gate_passed:
                result=super().request(endpoint,payload,**kwargs)
            else:
                if self.live is None:
                    a=list(self.live_args);a[1]=read_key(ROOT.parent/'KnowledgeTemplate/.env');k=dict(self.live_kwargs);k['offline']=False
                    self.live=CohortOpenRouter(*a,**k)
                network_allowed=True
                try:result=self.live.request(endpoint,payload,**kwargs)
                finally:network_allowed=False
            self.sequence_index+=1;used['chat' if endpoint=='chat/completions' else 'embedding']+=1
            return result
        def snapshot(self):
            if args.replay or not gate_passed:return super().snapshot()
            return locked_budget_and_orphan(scope)

    spec=importlib.util.spec_from_file_location('frozen_quanta_state_reconstruction_driver',source_path);driver=importlib.util.module_from_spec(spec);spec.loader.exec_module(driver);driver.ReadOnlyReplay=Meter
    def install_hooks():
        nonlocal hooks_installed,runtime_metadata_preload,cache_root
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
        original_generate=StrategyTrajectory.generate_id;original_factor=FactorFBWorkspace.execute;original_develop=QlibFactorRunner.develop;original_native=QlibFBWorkspace.execute
        cache_root=Path(RD_AGENT_SETTINGS.pickle_cache_folder_path_str).resolve()
        if not cache_root.is_relative_to(out):raise ReconstructionRefused('New cache must stay inside the new run')
        def persist_ids():atomic_json(out/'native_identity_lineage.json',{'loop_ids':all_loop_ids,'pool_ids':all_pool_ids})
        def resolve(kind,key,generate_args):
            table=all_loop_ids if kind=='loop' else all_pool_ids
            if key in table:return table[key]
            if args.replay or not gate_passed:raise ReconstructionRefused('Unknown identity before gate or during replay')
            tid=original_generate(*generate_args)
            if tid in set(all_loop_ids.values())|set(all_pool_ids.values()):raise ReconstructionRefused('Native future timestamp identity collided')
            table[key]=tid;persist_ids();return tid
        def run_task(*a,**k):
            task=k.get('task',a[0] if a else None);key=task_key(task['direction_id'],task['round_idx'],task['phase'])
            tid=resolve('loop',key,(task['direction_id'],task['round_idx'],task['phase']))
            if tid in visited_loops:raise ReconstructionRefused('Repeated existing loop')
            visited_loops.append(tid);token=CTX.set(('loop',key))
            try:return original_task(*a,**k)
            finally:CTX.reset(token)
        def create_pool(self,*a,**k):
            task=k.get('task',a[0] if a else None);key=task_key(task['direction_id'],task['round_idx'],task['phase'])
            tid=resolve('pool',key,(task['direction_id'],task['round_idx'],task['phase']))
            if tid in visited_pools:raise ReconstructionRefused('Repeated existing pool entry')
            token=CTX.set(('pool',key))
            try:result=original_pool_create(self,*a,**k)
            finally:CTX.reset(token)
            if result.trajectory_id!=tid:raise ReconstructionRefused('Native pool identity differs')
            visited_pools.append(tid);return result
        def generate_id(direction_id,round_idx,phase,timestamp=None):
            context=CTX.get();key=task_key(direction_id,round_idx,phase)
            if context is None or context[1]!=key:raise ReconstructionRefused('Unbound native timestamp identity request')
            return resolve(context[0],key,(direction_id,round_idx,phase,timestamp))
        def initialize(self,*a,**k):
            original_init(self,*a,**k)
            if self.trajectory_id in target_pool['trajectories']:self.created_at=target_pool['trajectories'][self.trajectory_id]['created_at']
            elif args.replay or not gate_passed:raise ReconstructionRefused('Unknown pool identity before gate or during replay')
        def cache_load(kind,key):
            cache_key=kind+'/'+str(key)+'.pkl'
            if not gate_passed and cache_key==plan['boundary']['cache_key']:stop('uncached_'+kind,{'cache_key':cache_key})
            row=cache_index.get(cache_key)
            if row is None:
                if args.replay or not gate_passed:raise ReconstructionRefused('Unrecorded computation before gate or during replay: '+cache_key)
                return None
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
            kind='quantaalpha.factors.coder.factor.execute';cache_key=kind+'/'+key+'.pkl';cached=cache_load(kind,key)
            if cache_key in cache_index:return cached
            strict_guard(assert_native_work,gate_passed,args.replay,cache_key,old_keys,self.workspace_path,out)
            if data_type not in ['Debug','All']:raise ReconstructionRefused('Unknown factor data scope')
            if cache_key==plan['boundary']['cache_key'] and (data_type!=plan['boundary']['data_type'] or hashlib.sha256(self.code_dict['factor.py'].encode()).hexdigest()!=plan['boundary']['sha256']):raise ReconstructionRefused('Boundary code/data type changed')
            native_context.append({'kind':'factor','cache_key':cache_key,'workspace':str(self.workspace_path)})
            state=rng_state()
            try:result=original_factor(self,data_type)
            finally:native_context.pop()
            if rng_state()!=state:raise ReconstructionRefused('New factor execution changed parent RNG; preserve and diagnose')
            p=cache_root/cache_key
            if not p.is_file():raise ReconstructionRefused('New factor result did not enter its native cache')
            cache_index[cache_key]={'copy':str(p.relative_to(ROOT)),'sha256':sha256(p),'bytes':p.stat().st_size,'lineage':'new_native_result_after_exact_observed_prefix_gate'}
            return result
        def codes(exp):return [getattr(x,'code_dict',{}).get('factor.py') if x is not None else None for x in getattr(exp,'sub_workspace_list',[])]
        def develop(self,exp,use_local=True):
            kind='quantaalpha.factors.runner.develop';key=CachedRunner.get_cache_key(self,exp,use_local=use_local);cache_key=kind+'/'+key+'.pkl';cached=cache_load(kind,key)
            if cache_key in cache_index:
                strict_guard(assert_cached_code,exp,cached)
                workspace=Path(cached.experiment_workspace.workspace_path)
                if cache_key in old_keys:
                    if str(workspace.relative_to(ROOT))!=model_rows[cache_key]['workspace']:raise ReconstructionRefused('Original model workspace lineage changed')
                    label='original_native_artifact_reused'
                else:
                    if not workspace.is_relative_to(source if args.replay else out):raise ReconstructionRefused('New result refers outside the continued source')
                    label='continued_native_artifact_reused'
                state=rng_state();result=assign(self,exp,cached_res=cached);result.experiment_workspace=cached.experiment_workspace
                if rng_state()!=state:raise ReconstructionRefused('Cached model assignment changed parent RNG')
            else:
                strict_guard(assert_native_work,gate_passed,args.replay,cache_key,old_keys,exp.experiment_workspace.workspace_path,out)
                state=rng_state();result=original_develop(self,exp,use_local=use_local)
                if rng_state()!=state:raise ReconstructionRefused('New model execution changed parent RNG; preserve and diagnose')
                workspace=Path(result.experiment_workspace.workspace_path);label='new_native_execution'
                p=cache_root/cache_key
                if not p.is_file():raise ReconstructionRefused('New model result did not enter its native cache')
                cache_index[cache_key]={'copy':str(p.relative_to(ROOT)),'sha256':sha256(p),'bytes':p.stat().st_size,'lineage':'new_native_result_after_exact_observed_prefix_gate'}
            model_events.append({'cache_key':cache_key,'workspace':str(workspace.relative_to(ROOT)),'lineage':label})
            atomic_json(out/'model_result_lineage.json',model_events)
            return result
        def guarded_native(self,*a,**k):
            strict_guard(assert_native_work,gate_passed,args.replay,'native_workspace',set(),self.workspace_path,out)
            if (self.workspace_path/'ret.pkl').exists():raise ReconstructionRefused('Completed native model cannot be executed again')
            native_context.append({'kind':'model','workspace':str(self.workspace_path)})
            try:return original_native(self,*a,**k)
            finally:native_context.pop()

        mining._run_evolution_task=run_task;EvolutionController.create_trajectory_from_loop_result=create_pool;StrategyTrajectory.generate_id=staticmethod(generate_id);StrategyTrajectory.__init__=initialize
        FactorFBWorkspace.execute=factor_execute;QlibFactorRunner.develop=develop;QlibFBWorkspace.execute=guarded_native
        # Preload trusted HDF dependencies before the first source request. Their
        # native library/CPU introspection is not factor or backtest execution.
        runtime_metadata_preload=True
        try:
            import tables
        finally:runtime_metadata_preload=False
        if any(used.values()) or visited_loops or visited_pools:raise ReconstructionRefused('Runtime preload performed source work')
        if rng_state()!=before:raise ReconstructionRefused('Hook installation changed seeded startup RNG state')
        hooks_installed=True;atomic_json(out/'hook_installation.json',{'status':'installed_after_original_source_seed_and_import_initialization','rng_state_sha256':identity(before),'native_module_files_unchanged':True,'multi_proc_n':RD_AGENT_SETTINGS.multi_proc_n,'use_auto_chat_cache_seed_gen':LLM_SETTINGS.use_auto_chat_cache_seed_gen})
    base_atomic=driver.atomic_json
    def observed_atomic(path,value):
        result=base_atomic(path,value)
        if Path(path)==out/'parameter_wiring.json' and not hooks_installed:install_hooks()
        return result
    driver.atomic_json=observed_atomic
    sys.argv=[str(source_path),'--offline','--output-name',out.name]+(['--probe'] if args.construction_only else [])
    driver.main()
    if args.construction_only:
        construction=json.loads((out/'construction_probe.json').read_text())
        if construction.get('paid_calls')!=0 or any(used.values()) or not hooks_installed or gate_passed:raise ReconstructionRefused('Constructor readiness performed unexpected source work')
        atomic_json(out/'software_readiness.json',{'status':'native_constructor_and_rng_neutral_hook_installation_pass','protocol_sha256':sha256(CONT_PROTOCOL),'runner_sha256':sha256(Path(__file__)),'new_model_calls':0,'native_factor_or_backtest_execution':0,'actual_prefix_reconstruction_completed':False})
        print('CONTINUATION_CONSTRUCTOR_PASS_NOT_LIVE_OR_REPLAY_COMPLETION',flush=True)
        return
    if not gate_passed:raise ReconstructionRefused('Source returned without the exact reconstructed boundary gate')
    if args.replay:
        differences=[];maximum=[0.0];hashes={}
        for name in REQUIRED_FILES:
            left=json.loads((source/name).read_text());right=json.loads((out/name).read_text())
            if name.endswith('trajectory_pool.json'):left.pop('saved_at',None);right.pop('saved_at',None)
            compare(left,right,name,differences,maximum);hashes[name]={'original':sha256(source/name),'replay':sha256(out/name)}
        if used['chat']!=len(replay_chat) or used['embedding']!=len(replay_embed):raise ReconstructionRefused('Incomplete full replay request population')
        if set(visited_loops)!=set(all_loop_ids.values()) or set(visited_pools)!=set(all_pool_ids.values()):raise ReconstructionRefused('Incomplete full replay identity population')
        for key in verified_cache:
            if sha256(ROOT/cache_index[key]['copy'])!=cache_index[key]['sha256']:raise ReconstructionRefused('Used replay cache changed')
        validate_completed_source(source);verify_models(lineage)
        result={'status':'pass' if not differences else 'fail','difference_count':len(differences),'differences':differences[:50],'maximum_numeric_difference':maximum[0],'trajectories':len(target_pool['trajectories']),'artifact_hashes':hashes,'network_calls':0,'ledger_mutations':0,'native_factor_or_backtest_execution':0,'continuation_protocol_sha256':sha256(CONT_PROTOCOL),'continuation_completion_sha256':sha256(source/'continuation_completion.json'),'source_prefix_gate_sha256':sha256(source/'continuation_prefix_gate.json'),'replay_prefix_gate_sha256':sha256(out/'continuation_prefix_gate.json'),'loop_ids_preserved':len(visited_loops),'pool_ids_preserved':len(visited_pools),'metadata_rule':'Ignore only pool.saved_at. Preserve exact request sequence, both identity namespaces, original/new native result lineage, parent selection, codes, metrics, feedback and creation timestamps.','replay_script_sha256':sha256(Path(__file__))}
        atomic_json(source/'full_replay_validation.json',result)
        if differences:raise ReconstructionRefused('Completed replay differs; preserve and diagnose')
        print('QUANTA_FULL_CONTINUATION_REPLAY_PASS',flush=True)
    else:
        finish_source(out,scope,all_loop_ids,all_pool_ids,cache_root,model_events)
        print('QUANTA_CONTINUED_SOURCE_COMPLETE_FULL_REPLAY_REQUIRED',flush=True)
if __name__=='__main__':main()
