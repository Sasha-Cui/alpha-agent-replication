"""Restore verified private payloads into a NEW destination; never execute research."""
from pathlib import Path
import argparse,hashlib,json,os,shutil,tarfile,tempfile
from fidelity_package_core_v2 import safe_member,digest

def restore(archive,destination,prefix='',relative_links=False,*,expected_hash=None):
    archive=Path(archive);destination=Path(destination)
    if expected_hash is None or digest(archive)!=expected_hash:raise ValueError('Expected archive SHA-256 is required and must match')
    if destination.exists() or destination.is_symlink():raise ValueError('Destination must not exist; never overwrite a checkout')
    with tarfile.open(archive,'r:gz') as tar:
        member=tar.getmember('PACKAGE_INDEX.json')
        if not member.isfile() or member.size>200*1024**2:raise ValueError('Invalid package index')
        index=json.load(tar.extractfile(member))
    if index['schema']!='fidelity-private-content-index-v1':raise ValueError('Not a private content-index archive')
    rows=[r for r in index['files'] if r['logical_path'].startswith(prefix)];names=[safe_member(r['logical_path']) for r in rows]
    if len(set(names))!=len(names):raise ValueError('Duplicate restore path')
    required={r['sha256'] for r in rows};byhash={}
    for r in rows:byhash.setdefault(r['sha256'],[]).append(r)
    destination.parent.mkdir(parents=True,exist_ok=True)
    if sum(r['bytes'] for r in rows)+10*1024**3>shutil.disk_usage(destination.parent).free:raise ValueError('Insufficient restore capacity with10GiB headroom')
    destination.mkdir(mode=0o700)
    completed=[]
    with tempfile.TemporaryDirectory(prefix='fidelity-blobs-',dir=destination.parent) as temp:
        seen=set()
        with tarfile.open(archive,'r:gz') as tar:
            for m in tar:
                safe_member(m.name)
                if not m.isfile():raise ValueError('Archive contains a link or nonregular entry')
                if not m.name.startswith('blobs/'):continue
                h=m.name.removeprefix('blobs/')
                if h not in required:continue
                if h in seen:raise ValueError('Duplicate content blob')
                seen.add(h);p=Path(temp)/h;expected=byhash[h][0]['bytes']
                if m.size!=expected:raise ValueError('Blob size mismatch')
                with tar.extractfile(m) as a,p.open('xb') as b:shutil.copyfileobj(a,b,4*1024*1024);b.flush();os.fsync(b.fileno())
                if digest(p)!=h:raise ValueError('Blob checksum mismatch')
                for row in byhash[h]:
                    out=destination/row['logical_path'];out.parent.mkdir(parents=True,exist_ok=True)
                    with p.open('rb') as a,out.open('xb') as b:shutil.copyfileobj(a,b,4*1024*1024);b.flush();os.fsync(b.fileno())
                    if digest(out)!=h:raise ValueError('Restored file checksum mismatch')
                    out.chmod(row['mode']&0o777);os.utime(out,ns=(row['mtime_ns'],row['mtime_ns']));completed.append(row['logical_path'])
                p.unlink()
        if seen!=required:raise ValueError('Missing content blobs')
    links=[]
    for row in index['symlinks']:
        if not row['path'].startswith(prefix):continue
        safe_member(row['path']);safe_member(row['target']);created=False
        if relative_links and row['target'] in completed:
            out=destination/row['path'];out.parent.mkdir(parents=True,exist_ok=True)
            if out.exists() or out.is_symlink():raise ValueError('Symlink restore would overwrite a file')
            os.symlink(os.path.relpath(destination/row['target'],out.parent),out);created=True
        links.append({**row,'relative_link_created':created})
    receipt={'status':'regular_file_bytes_verified','files':len(completed),'links':links,'archive_sha256':digest(archive),'native_jobs_executed':0,'original_absolute_layout_reproduced':False,'note':'Original symlink text is preserved in this receipt. Optional relative links relocate targets inside the new tree and do not establish original absolute-layout or full-paper fidelity.'}
    with (destination/'RESTORATION_RECEIPT.json').open('x') as f:json.dump(receipt,f,indent=2);f.write('\n')
    return receipt

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--archive',type=Path,required=True);p.add_argument('--destination',type=Path,required=True);p.add_argument('--expected-sha256',required=True);p.add_argument('--prefix',default='');p.add_argument('--relative-links',action='store_true');a=p.parse_args()
    result=restore(a.archive,a.destination,a.prefix,a.relative_links,expected_hash=a.expected_sha256);print(json.dumps({'status':result['status'],'files':result['files'],'native_jobs_executed':0}))
