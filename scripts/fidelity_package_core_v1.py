"""Byte-preserving archive primitives; no source/model/account execution."""
from pathlib import Path, PurePosixPath
from contextlib import contextmanager
import fcntl, hashlib, io, json, os, re, shutil, tarfile, threading

SECRET = re.compile(rb'sk-or-v1-[0-9a-fA-F]{64}|sk-proj-[A-Za-z0-9_-]{40,}|-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----')

def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(4*1024*1024),b''):h.update(chunk)
    return h.hexdigest()

def stable_identity(path):
    p=Path(path)
    if p.is_symlink() or not p.is_file():raise ValueError('Expected regular payload: '+str(p))
    s=p.stat();return (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns)

def safe_member(name):
    p=PurePosixPath(name)
    if not name or name in {'.','..'} or p.is_absolute() or '..' in p.parts or '\\' in name or any(c in name for c in '\x00\r\n') or p.as_posix()!=name:
        raise ValueError('Unsafe archive member')
    return name

def credential_name(path):
    p=PurePosixPath(path)
    return any(x=='.env' or x.startswith('.env.') or x in {'id_rsa','id_ed25519','credentials.json'} for x in p.parts)

def scan_secret(data,label):
    if SECRET.search(data):raise ValueError('Credential-shaped bytes blocked: '+label)

class VerifiedReader:
    """Check the exact bytes tarfile consumed, including chunk-spanning credentials."""
    def __init__(self,path):
        self.path=Path(path);self.before=stable_identity(self.path);self.stream=self.path.open('rb');self.h=hashlib.sha256();self.tail=b'';self.bytes=0
    def read(self,n=-1):
        data=self.stream.read(n);self.h.update(data);scan_secret(self.tail+data,str(self.path));self.tail=(self.tail+data)[-512:];self.bytes+=len(data);return data
    def finish(self,expected):
        self.stream.close()
        if self.bytes!=self.before[2] or self.h.hexdigest()!=expected or stable_identity(self.path)!=self.before:raise ValueError('Payload changed while packaging: '+str(self.path))
    def close(self):self.stream.close()

@contextmanager
def locked_snapshot(paths):
    """Keep actual outer flock ownership while frozen read-only gates re-enter it.

    Only exclusive re-entry for the exact already-locked inode is recognized.
    No scientific/request check is replaced. Inner unlock/downgrade and cross-thread
    use fail closed. Other locks retain ordinary flock behavior. The original
    flock is restored before the owning descriptors release their locks.
    """
    original=fcntl.flock;owner=threading.get_ident();handles=[];held={};reentries=[]
    try:
        for item in paths:
            p=Path(item)
            if p.is_symlink() or not p.is_file():raise ValueError('Canonical lock must already exist and be regular')
            f=p.open('r+');s=os.fstat(f.fileno());key=(s.st_dev,s.st_ino)
            if key in held:
                f.close();raise ValueError('Duplicate outer lock identity')
            handles.append(f);original(f,fcntl.LOCK_EX);held[key]=(p,f)
        def reentrant(fd,operation):
            number=fd if isinstance(fd,int) else fd.fileno();s=os.fstat(number);key=(s.st_dev,s.st_ino)
            if key not in held:return original(fd,operation)
            if threading.get_ident()!=owner or operation!=fcntl.LOCK_EX:raise ValueError('Unsupported nested snapshot lock operation')
            p,outer=held[key];current=p.stat();outer_stat=os.fstat(outer.fileno())
            if (current.st_dev,current.st_ino)!=key or (outer_stat.st_dev,outer_stat.st_ino)!=key:raise ValueError('Canonical lock identity replaced')
            reentries.append(str(p));return None
        fcntl.flock=reentrant
        yield {'reentries':reentries,'locked_paths':[str(p) for p in paths]}
    finally:
        fcntl.flock=original
        for f in reversed(handles):
            original(f,fcntl.LOCK_UN);f.close()

def add_bytes(tar,name,data,mode=0o600):
    safe_member(name);scan_secret(data,name);info=tarfile.TarInfo(name);info.size=len(data);info.mode=mode;info.mtime=0;tar.addfile(info,io.BytesIO(data))

def add_payload(tar,name,path,expected,mode=0o600):
    safe_member(name)
    if credential_name(str(path)):raise ValueError('Credential filename cannot enter an archive')
    reader=VerifiedReader(path);info=tarfile.TarInfo(name);info.size=reader.before[2];info.mode=mode;info.mtime=0
    try:tar.addfile(info,reader);reader.finish(expected)
    finally:reader.close()

def hash_current(path,expected=None):
    reader=VerifiedReader(path)
    try:
        for _ in iter(lambda:reader.read(4*1024*1024),b''):pass
        h=reader.h.hexdigest();reader.finish(h if expected is None else expected);return h
    finally:reader.close()

def verify_tar(path,expected):
    """Read every regular member fully; reject traversal, links, duplicates and extras."""
    seen=set();total=0
    with tarfile.open(path,'r:gz') as tar:
        for member in tar:
            safe_member(member.name)
            if not member.isfile() or member.name in seen or member.name not in expected:raise ValueError('Unexpected, duplicate or nonregular archive member')
            row=expected[member.name]
            if member.size!=row['bytes']:raise ValueError('Archive member size changed')
            h=hashlib.sha256();count=0;tail=b''
            with tar.extractfile(member) as f:
                for data in iter(lambda:f.read(4*1024*1024),b''):
                    h.update(data);scan_secret(tail+data,member.name);tail=data[-512:];count+=len(data)
            if count!=row['bytes'] or h.hexdigest()!=row['sha256']:raise ValueError('Archive member bytes changed')
            seen.add(member.name);total+=count
    if seen!=set(expected):raise ValueError('Archive members missing')
    return {'status':'pass','members':len(seen),'uncompressed_bytes':total,'sha256':digest(path)}

def copy_durable(source,target,expected):
    source=Path(source);target=Path(target)
    if target.exists() or target.is_symlink():raise ValueError('Preserve existing second-copy path')
    if stable_identity(source)[2]+10*1024**3>shutil.disk_usage(target.parent).free:raise ValueError('Insufficient durable second-copy capacity with10GiB headroom')
    with source.open('rb') as a,target.open('xb') as b:
        shutil.copyfileobj(a,b,4*1024*1024);b.flush();os.fsync(b.fileno())
    if digest(source)!=expected or digest(target)!=expected or (source.stat().st_dev,source.stat().st_ino)==(target.stat().st_dev,target.stat().st_ino):raise ValueError('Second-copy integrity or independence failed')
    target.chmod(0o400)
    return {'path':str(target),'sha256':expected,'bytes':target.stat().st_size,'independent_inode':True}
