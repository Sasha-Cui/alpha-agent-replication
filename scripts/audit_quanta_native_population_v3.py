"""Read only every saved model-cache result and both original/new task namespaces."""
from pathlib import Path
import sys,os,json,pickle,socket,subprocess
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts'),str(ROOT/'artifacts/fidelity_completion_v2/dependencies/quantaalpha_b7ceb27')]
from alpha_evolve.openrouter_budget import sha256,atomic_json
from quanta_walltime_continuation_v3 import LIVE,validate_completed_source
from quanta_native_population_v3 import assert_population

def main():
    run=ROOT/'artifacts/fidelity_completion_v2'/LIVE;out=run/'native_model_population_validation.json'
    if out.exists():raise ValueError('Preserve existing native population audit')
    done=validate_completed_source(run);os.environ.update(OPENAI_API_KEY='unused-read-only',CHAT_OPENAI_API_KEY='unused-read-only',LITELLM_LOCAL_MODEL_COST_MAP='True',DATA_RESULTS_DIR=str(run/'population_import_metadata'))
    def deny(*a,**k):raise RuntimeError('Native population audit forbids network, factor and model execution')
    socket.socket.connect=deny;socket.create_connection=deny;os.system=deny
    from quantaalpha.factors.coder.factor import FactorFBWorkspace
    from quantaalpha.factors.runner import QlibFactorRunner
    from quantaalpha.factors.workspace import QlibFBWorkspace
    FactorFBWorkspace.execute=deny;QlibFactorRunner.develop=deny;QlibFBWorkspace.execute=deny
    import tables
    subprocess.Popen=deny
    actual=[];baselines=[];cache_rows=[]
    for key,row in done['cache_artifacts'].items():
        if not key.startswith('quantaalpha.factors.runner.develop/'):continue
        p=ROOT/row['copy'];assert sha256(p)==row['sha256'];exp=pickle.loads(p.read_bytes());workspace=Path(exp.experiment_workspace.workspace_path);cache_rows.append({'path':str(p.relative_to(ROOT)),'sha256':row['sha256']})
        if (workspace/'ret.pkl').exists():
            name=str(workspace.relative_to(ROOT));actual.append(name)
            if not exp.based_experiments:baselines.append(name)
    pool=json.loads((run/'log/trajectory_pool.json').read_text());pooled=[];checkpoints=[]
    for tid,t in pool['trajectories'].items():
        branch=t['phase']+'_'+str(t['round_idx']).zfill(2)+'_'+str(t['direction_id']).zfill(2);p=run/'log'/branch/'__session__/0/4_feedback'
        loop=pickle.loads(p.read_bytes());assert len(loop.trace.hist)==1;exp=loop.trace.hist[0][1];workspace=Path(exp.experiment_workspace.workspace_path)
        if not (workspace/'ret.pkl').exists():raise ValueError('Pool task has no actual native account')
        pooled.append(str(workspace.relative_to(ROOT)));checkpoints.append({'path':str(p.relative_to(ROOT)),'sha256':sha256(p),'loop_id':loop.trajectory_id,'pool_id':tid})
    assert_population(actual,pooled,baselines)
    atomic_json(out,{'status':'all_native_backtests_accounted_for_in_pool_or_explicit_baseline','source_completion_sha256':sha256(run/'continuation_completion.json'),'backtested_workspaces':actual,'pool_workspaces':pooled,'baseline_workspaces':baselines,'cache_bindings':cache_rows,'checkpoint_bindings':checkpoints,'native_model_factor_calls':0,'new_api_calls':0,'native_LoopBase_load_called':False,'auditor_sha256':sha256(Path(__file__)),'guard_sha256':sha256(ROOT/'scripts/quanta_native_population_v3.py'),'claim':'Physical saved backtest population only. No success-rate, new fit or economic claim.'})
    print('ALL_ACTUAL_NATIVE_BACKTESTS_HAVE_EXPLICIT_POPULATION_LINEAGE',flush=True)
if __name__=='__main__':main()
