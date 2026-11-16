import sys,unittest
from pathlib import Path
from types import SimpleNamespace as NS
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'src')]
from quanta_walltime_continuation_v2 import assert_boundary,assert_cached_code,assert_native_work
from run_quanta_walltime_continuation_v2 import strict_guard,ReconstructionRefused
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
if __name__=='__main__':unittest.main()
