#!/usr/bin/env python3
"""Restore verified Qlib files and fetch immutable public QuantaAlpha HDF inputs."""
from pathlib import Path, PurePosixPath
import json
import hashlib
import tarfile
import urllib.request
import shutil
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/fidelity_completion_v2/quantaalpha_data'
REVISION='d63bf5ba30d1d169023110377cbbe93a90a74e07'

def digest(path):
    value=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):value.update(block)
    return value.hexdigest()

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    deps=json.loads((ROOT/'artifacts/publication_upgrade_v1/dependency_archives/manifest.json').read_text())['dependencies']
    record=next(r for r in deps if r['name']=='quantaalpha_provider')
    archive=ROOT/record['archive_path'];assert digest(archive)==record['archive_sha256']
    target=Path(record['source_path']);restored=0;identical=0
    with tarfile.open(archive) as tar:
        for member in tar:
            rel=PurePosixPath(member.name)
            if not member.isfile() or rel.is_absolute() or '..' in rel.parts:raise ValueError('Unsafe dependency member')
            path=target/str(rel);data=tar.extractfile(member).read()
            if path.exists():
                if path.read_bytes()!=data:raise ValueError('Existing provider data differs: '+str(path))
                identical+=1
            else:
                path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data);restored+=1
    print('PROVIDER_RESTORED',restored,'IDENTICAL',identical,flush=True)
    tree_url=f'https://huggingface.co/api/datasets/QuantaAlpha/qlib_csi300/tree/{REVISION}?recursive=true'
    with urllib.request.urlopen(tree_url,timeout=30) as response:tree=json.load(response)
    files=[]
    for name,folder in [('daily_pv.h5','full'),('daily_pv_debug.h5','debug')]:
        metadata=next(r for r in tree if r['path']==name)
        expected=metadata.get('lfs',{}).get('oid')
        dest=OUT/folder/'daily_pv.h5';dest.parent.mkdir(exist_ok=True)
        url=f'https://huggingface.co/datasets/QuantaAlpha/qlib_csi300/resolve/{REVISION}/{name}'
        if not dest.exists():
            partial=dest.with_suffix('.download')
            with urllib.request.urlopen(url,timeout=60) as response,partial.open('wb') as sink:shutil.copyfileobj(response,sink,1024*1024)
            if expected and digest(partial)!=expected:raise ValueError('HuggingFace LFS checksum mismatch')
            partial.replace(dest)
        actual=digest(dest)
        if expected and actual!=expected:raise ValueError('Existing HDF checksum mismatch')
        files.append({'source_url':url,'path':str(dest),'bytes':dest.stat().st_size,'sha256':actual,'upstream_lfs_sha256':expected})
        print('HDF_READY',name,dest.stat().st_size,actual,flush=True)
    result={'status':'complete','created_at_utc':datetime.now(timezone.utc).isoformat(),'dataset_revision':REVISION,'provider_path':str(target),'provider_archive_sha256':record['archive_sha256'],'restored_provider_files':restored,'existing_identical_files':identical,'hdf_files':files}
    (OUT/'manifest.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
