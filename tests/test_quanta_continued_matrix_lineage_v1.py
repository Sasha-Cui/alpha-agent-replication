from pathlib import Path
import sys,hashlib
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from quanta_continued_matrix_lineage_v1 import assert_use_binding,load_matrix_scope

def fixture(root,branch='original'):
 w=root/branch/'model';w.mkdir(parents=True);p=w/'combined_factors_df.parquet';p.write_bytes(b'exact native matrix')
 rel=str(p.relative_to(root));h=hashlib.sha256(p.read_bytes()).hexdigest();use={'experiment_index':0,'column':'factor','matrix':rel,'matrix_sha256':h};bindings={(0,'factor'):{'matrix':rel,'matrix_sha256':h,'workspace':str(w.relative_to(root))}}
 return p,use,bindings

@pytest.mark.parametrize('branch',['original','continued'])
def test_exact_admitted_old_or_new_workspace_is_accepted(tmp_path,branch):
 p,use,b=fixture(tmp_path,branch);assert assert_use_binding(tmp_path,use,b)==p

@pytest.mark.parametrize('field,value',[('experiment_index',1),('column','other'),('matrix','other/combined_factors_df.parquet'),('matrix_sha256','altered')])
def test_identity_changes_refused(tmp_path,field,value):
 p,use,b=fixture(tmp_path);use[field]=value
 with pytest.raises(ValueError):assert_use_binding(tmp_path,use,b)

def test_changed_native_bytes_refused(tmp_path):
 p,use,b=fixture(tmp_path);p.write_bytes(b'changed')
 with pytest.raises(ValueError):assert_use_binding(tmp_path,use,b)

def test_equal_hash_at_unbound_external_path_refused(tmp_path):
 p,use,b=fixture(tmp_path);x=tmp_path/'unbound';x.write_bytes(p.read_bytes());use['matrix']='unbound'
 with pytest.raises(ValueError):assert_use_binding(tmp_path,use,b)

def test_symlink_substitution_refused(tmp_path):
 p,use,b=fixture(tmp_path);x=tmp_path/'outside';x.write_bytes(p.read_bytes());p.unlink();p.symlink_to(x)
 with pytest.raises(ValueError):assert_use_binding(tmp_path,use,b)

def test_misbound_workspace_refused(tmp_path):
 p,use,b=fixture(tmp_path);b[(0,'factor')]['workspace']='wrong'
 with pytest.raises(ValueError):assert_use_binding(tmp_path,use,b)

@pytest.mark.parametrize('case,debug,data',[('alphaagent',False,None),('quantaalpha',True,None),('quantaalpha',False,Path('other.h5'))])
def test_scope_override_refused_before_any_factor_work(tmp_path,case,debug,data):
 with pytest.raises(ValueError):load_matrix_scope(tmp_path,tmp_path,None,case,debug,data)
