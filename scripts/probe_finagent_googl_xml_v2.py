#!/usr/bin/env python3
"""Network-disabled native prefix replay; stop before the first new future request."""
from pathlib import Path
import importlib.util,json,sys,socket
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from alpha_evolve.publication_replay import ReadOnlyReplay
from alpha_evolve.openrouter_budget import sha256,atomic_json
from finagent_googl_xml_alias_v2 import load_witness,install,validate_prefixes
class PrefixProbeComplete(RuntimeError):pass

def main():
    witness=load_witness();out=ROOT/'artifacts/fidelity_completion_v2'/witness['probe_run']
    if out.exists():raise ValueError('Preserve any existing prefix-probe output; never blindly restart')
    def denied(*args,**kwargs):raise RuntimeError('Prefix probe networking disabled')
    socket.socket.connect=denied;socket.create_connection=denied
    source=ROOT/'scripts/run_finagent_fidelity_v2.py';spec=importlib.util.spec_from_file_location('unchanged_finagent_xml_probe_driver',source);driver=importlib.util.module_from_spec(spec);spec.loader.exec_module(driver)
    install(driver,out,witness)
    class ProbeMeter(ReadOnlyReplay):
        def request(self,*args,**kwargs):
            try:return super().request(*args,**kwargs)
            except RuntimeError as error:
                if not str(error).startswith('Offline response is not complete in the frozen cache: '):raise
                key=str(error).rsplit(' ',1)[-1]
                if key in self.frozen_state['calls']:raise RuntimeError('Existing unresolved request is not a new continuation request') from error
                proof=validate_prefixes(out,witness)
                proof.update(first_absent_future_request_hash=key,network_calls=0,ledger_mutations=0,wrapper_sha256=sha256(Path(__file__)),adapter_sha256=sha256(ROOT/'scripts/finagent_googl_xml_alias_v2.py'),protocol_sha256=sha256(ROOT/'paper_runs/fidelity_completion_v2/finagent_googl_xml_alias_protocol.json'))
                atomic_json(out/'xml_prefix_probe_validation.json',proof)
                raise PrefixProbeComplete('Verified prefix and alias; stopped before new request '+key) from error
    driver.WaitingMeter=ProbeMeter
    sys.argv=[str(source),'--offline','--output-name',witness['probe_run'],'--recipe',str(ROOT/witness['recipe_path'])]
    try:driver.main()
    except RuntimeError as error:
        expected="Validation worker failed; others were allowed to finish: {'native_causal': 1}"
        p=out/'xml_prefix_probe_validation.json'
        if str(error)!=expected or not p.exists():raise
        proof=json.loads(p.read_text())
        if proof['status']!='all_original_completed_prefixes_and_single_alias_match' or (out/'completion.json').exists():raise ValueError('Prefix probe overclaimed source completion')
        proof['probe_status']='pass_expected_stop_before_new_request_not_full_replay';atomic_json(p,proof)
        print('GOOGL_XML_PREFIX_PROBE_PASS',proof['records'],proof['first_absent_future_request_hash'],flush=True)
    else:raise ValueError('Expected an absent post-failure request; inspect before claiming prefix-probe pass')
if __name__=='__main__':main()
