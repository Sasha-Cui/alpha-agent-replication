import sys,unittest
from pathlib import Path
from types import SimpleNamespace as NS
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'src')]
from quanta_walltime_continuation_v3 import assert_boundary,assert_cached_code,assert_native_work
from run_quanta_walltime_continuation_v3 import strict_guard,ReconstructionRefused
class Guards(unittest.TestCase):
 def exp(self,code='a',parents=()):return NS(sub_workspace_list=[NS(code_dict={'factor.py':code})],based_experiments=list(parents))
 def test_exact_boundary(self):assert_boundary('uncached_quantaalpha.factors.coder.factor.execute',{'cache_key':'k'},{'boundary':{'cache_key':'k'}},'r',{'rng_state_sha256':'r'})
 def test_api_cannot_replace_factor_boundary(self):
  with self.assertRaises(ValueError):assert_boundary('next_api_request',{'cache_key':'k'},{'boundary':{'cache_key':'k'}},'r',{'rng_state_sha256':'r'})
 def test_wrong_factor_boundary(self):
  with self.assertRaises(ValueError):assert_boundary('uncached_quantaalpha.factors.coder.factor.execute',{'cache_key':'other'},{'boundary':{'cache_key':'k'}},'r',{'rng_state_sha256':'r'})
 def test_rng_difference_refused(self):
  with self.assertRaises(ValueError):assert_boundary('uncached_quantaalpha.factors.coder.factor.execute',{'cache_key':'k'},{'boundary':{'cache_key':'k'}},'wrong',{'rng_state_sha256':'r'})
 def test_same_model_code(self):assert_cached_code(self.exp(parents=[self.exp('p')]),self.exp(parents=[self.exp('p')]))
 def test_weak_key_code_collision(self):
  with self.assertRaises(ValueError):assert_cached_code(self.exp('wrong'),self.exp())
 def test_weak_key_parent_code_collision(self):
  with self.assertRaises(ValueError):assert_cached_code(self.exp(parents=[self.exp('p')]),self.exp(parents=[self.exp('wrong')]))
 def test_missing_parent(self):
  with self.assertRaises(ValueError):assert_cached_code(self.exp(parents=[self.exp()]),self.exp())
 def test_before_gate_no_native_execution(self):
  with self.assertRaises(ValueError):assert_native_work(False,False,'new',set(),'/tmp/test/results/a','/tmp/test')
 def test_replay_no_native_execution(self):
  with self.assertRaises(ValueError):assert_native_work(True,True,'new',set(),'/tmp/test/results/a','/tmp/test')
 def test_old_result_never_reexecuted(self):
  with self.assertRaises(ValueError):assert_native_work(True,False,'old',{'old'},'/tmp/test/results/a','/tmp/test')
 def test_other_workspace_refused(self):
  with self.assertRaises(ValueError):assert_native_work(True,False,'new',set(),'/tmp/old/results/a','/tmp/test')
 def test_new_work_allowed_after_gate(self):assert_native_work(True,False,'new',{'old'},'/tmp/test/results/a','/tmp/test')
 def test_guard_errors_cannot_be_swallowed_as_native_task_failure(self):
  with self.assertRaises(ReconstructionRefused):strict_guard(assert_cached_code,self.exp('wrong'),self.exp())
class PartialAndNativeWorkspaceGuards(unittest.TestCase):
 def test_actual_new_native_model_root_allowed(self):
  assert_native_work(True,False,'new',{'old'},'/tmp/test/git_ignore_folder/RD-Agent_workspace/uuid','/tmp/test')
 def test_original_native_model_root_stays_forbidden(self):
  with self.assertRaises(ValueError):assert_native_work(True,False,'new',{'old'},'/tmp/original/git_ignore_folder/RD-Agent_workspace/uuid','/tmp/test')
 def test_other_new_run_directory_is_not_native_root(self):
  with self.assertRaises(ValueError):assert_native_work(True,False,'new',{'old'},'/tmp/test/arbitrary/uuid','/tmp/test')
 def plan(self):return {'partial_model':{'model_cache_key':'model','code_identity':{'codes':['a'],'parents':[[]]}},'partial_counts':{'chat':2264,'embedding':379,'quality':419,'pool':33,'loops':34}}
 def test_exact_partial_boundary_allowed(self):
  from quanta_walltime_continuation_v3 import assert_partial_boundary
  p=self.plan();assert_partial_boundary('model',p['partial_counts'],p['partial_model']['code_identity'],p)
 def test_missing_partial_reply_blocks_future_work(self):
  from quanta_walltime_continuation_v3 import assert_partial_boundary
  p=self.plan();counts={**p['partial_counts'],'chat':2263}
  with self.assertRaises(ValueError):assert_partial_boundary('model',counts,p['partial_model']['code_identity'],p)
 def test_pending_model_code_change_blocks_future_work(self):
  from quanta_walltime_continuation_v3 import assert_partial_boundary
  p=self.plan()
  with self.assertRaises(ValueError):assert_partial_boundary('model',p['partial_counts'],{'codes':['wrong'],'parents':[[]]},p)
 def test_other_model_cannot_replace_pending_model(self):
  from quanta_walltime_continuation_v3 import assert_partial_boundary
  p=self.plan()
  with self.assertRaises(ValueError):assert_partial_boundary('other',p['partial_counts'],p['partial_model']['code_identity'],p)

if __name__=='__main__':unittest.main()
