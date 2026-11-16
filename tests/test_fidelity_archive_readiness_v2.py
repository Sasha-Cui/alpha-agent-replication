"""Guard classification, not a fake financial or archive-completion fixture."""
from pathlib import Path
import copy,sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from fidelity_archive_readiness_v2 import assess_requests
class ArchiveReadinessGuards(unittest.TestCase):
    def setUp(self):
        self.calls={'terminal':{'status':'reserved','study':'test','pid':17,'reserved_usd':.12}}
        self.w={'terminal':{'trial':8,'expected_entry':dict(self.calls['terminal'])}}
    def run_gate(self,**kw):
        args=dict(sources_closed=True,fresh_dual_store_check=True);args.update(kw)
        return assess_requests(self.calls,self.w,{},set(),set(),**args)
    def test_known_terminal_is_retained_not_refunded(self):
        before=copy.deepcopy((self.calls,self.w));r=self.run_gate();self.assertTrue(r['cache_snapshot_request_gate_pass']);self.assertEqual(r['retained_terminal_reservation_usd'],.12);self.assertEqual((self.calls,self.w),before);self.assertFalse(r['archive_created'])
    def test_unknown_reserved_blocks(self):
        self.calls['other']={'status':'reserved','study':'live','pid':99,'reserved_usd':.4};self.assertFalse(self.run_gate()['cache_snapshot_request_gate_pass'])
    def test_between_requests_not_ready_without_source_closure(self):self.assertFalse(self.run_gate(sources_closed=False)['cache_snapshot_request_gate_pass'])
    def test_historical_absence_is_not_fresh_snapshot_authority(self):self.assertFalse(self.run_gate(fresh_dual_store_check=False)['cache_snapshot_request_gate_pass'])
    def test_changed_owner_refused(self):
        self.calls['terminal']['pid']=18
        with self.assertRaises(ValueError):self.run_gate()
    def test_changed_charge_refused(self):
        self.calls['terminal']['reserved_usd']=0
        with self.assertRaises(ValueError):self.run_gate()
    def test_missing_reserved_entry_refused(self):
        self.calls.clear()
        with self.assertRaises(ValueError):self.run_gate()
    def test_cache_response_refused(self):
        with self.assertRaises(ValueError):assess_requests(self.calls,self.w,{}, {'terminal'},set(),sources_closed=True,fresh_dual_store_check=True)
    def test_journal_only_response_refused(self):
        with self.assertRaises(ValueError):assess_requests(self.calls,self.w,{},set(),{'terminal'},sources_closed=True,fresh_dual_store_check=True)
    def test_unknown_status_fails_closed(self):
        self.calls['new_status']={'status':'pending_transport','study':'new','pid':42,'reserved_usd':.3}
        result=self.run_gate();self.assertFalse(result['cache_snapshot_request_gate_pass']);self.assertEqual(result['unsupported_request_statuses'],{'pending_transport':1})
    def test_retry_mapping_refused(self):
        with self.assertRaises(ValueError):assess_requests(self.calls,self.w,{'terminal':{'attempt':1}},set(),set(),sources_closed=True,fresh_dual_store_check=True)
if __name__=='__main__':unittest.main()
