"""Fail-closed primitives for read-only Quanta state reconstruction."""
from pathlib import Path
import hashlib,json

def identity(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def task_key(direction_id,round_idx,phase):return str(int(direction_id))+':'+str(int(round_idx))+':'+str(getattr(phase,'value',phase))

def select_identity(kind,key,loop_ids,pool_ids):
    if kind not in ['loop','pool']:raise ValueError('Identity request outside native loop/pool context')
    table=loop_ids if kind=='loop' else pool_ids
    if key not in table:raise ValueError('No preserved identity for this exact native task')
    return table[key]

def checked_cache_bytes(row,root):
    path=Path(root)/row['copy'];data=path.read_bytes()
    if len(data)!=row['bytes'] or hashlib.sha256(data).hexdigest()!=row['sha256']:raise ValueError('Preserved cache artifact changed')
    return data

def assert_recorded_request(endpoint,index,key,chat_keys,embedding_keys,orphan_key):
    expected=chat_keys if endpoint=='chat/completions' else embedding_keys if endpoint=='embeddings' else None
    if expected is None:raise ValueError('Unexpected endpoint')
    if index<len(expected):
        if key!=expected[index]:raise ValueError('Exact recorded request sequence differs at '+endpoint+':'+str(index))
        return 'recorded'
    if endpoint=='chat/completions' and index==len(expected):
        if key!=orphan_key:raise ValueError('Next source request is not the exact durable orphan')
        return 'orphan'
    return 'future_boundary'

def assert_boundary_counts(chat_count,embedding_count,quality_count,pool_count,loop_count,scope):
    if chat_count!=scope['chat_count']+1 or embedding_count!=scope['embedding_count'] or quality_count<scope['quality_event_count'] or pool_count!=scope['pool_count'] or loop_count!=scope['loop_count']:
        raise ValueError('Unfinished exact-prefix reconstruction cannot authorize a future boundary')
