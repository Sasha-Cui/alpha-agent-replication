"""Single witnessed response-format alias; no new response and no shared-source edit."""
from pathlib import Path
import contextvars,fcntl,hashlib,json,os,re,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from alpha_evolve.openrouter_budget import sha256,atomic_json
CTX=contextvars.ContextVar('finagent_xml_request',default=None)

def canonical_markup(text,key,witness):
    if key!=witness['request_hash']:return text,False
    if hashlib.sha256(text.encode()).hexdigest()!=witness['response_sha256']:raise ValueError('Witnessed response bytes changed')
    value=text
    for name in ['analysis','summary']:
        if value.count('<'+name+'>')!=1 or value.count('</'+name+'>')!=1:raise ValueError('Ambiguous response schema')
        value=value.replace('<'+name+'>','<string name="'+name+'">').replace('</'+name+'>','</string>')
    if hashlib.sha256(value.encode()).hexdigest()!=witness['normalized_response_sha256']:raise ValueError('Unexpected canonical markup')
    for name in ['analysis','summary']:
        before=re.search('<'+name+'>(.*?)</'+name+'>',text,re.S)
        after=re.search('<string name="'+name+'">(.*?)</string>',value,re.S)
        if before is None or after is None or before.group(1)!=after.group(1):raise ValueError('Response field content changed')
    return value,True

def load_witness(root=ROOT):
    root=Path(root);p=root/'paper_runs/fidelity_completion_v2/finagent_googl_xml_alias_protocol.json';frozen=root/'artifacts/fidelity_completion_v2/finagent_googl_xml_20260918/frozen_protocol.json'
    if sha256(p)!=sha256(frozen):raise ValueError('Frozen response alias scope changed')
    w=json.loads(p.read_text())
    for path,digest in [(w['diagnosis_path'],w['diagnosis_sha256']),(w['preservation_manifest_path'],w['preservation_manifest_sha256']),(w['recipe_path'],w['recipe_sha256']),(w['input_path'],w['input_sha256'])]:
        if sha256(root/path)!=digest:raise ValueError('Response alias input/witness changed')
    if sha256(root/'scripts/run_finagent_fidelity_v2.py')!=w['original_driver_sha256']:raise ValueError('Original driver changed')
    manifest=json.loads((root/w['preservation_manifest_path']).read_text())
    for row in manifest['files']:
        if sha256(root/row['copy'])!=row['sha256']:raise ValueError('Preserved failed case changed')
        if Path(row['path']).is_absolute() and sha256(Path(row['path']))!=row['sha256']:raise ValueError('Frozen native parser/source changed')
    for row in w['prefixes']:
        if sha256(root/row['path'])!=row['sha256']:raise ValueError('Preserved prefix changed')
    return w

def install(driver,out,witness):
    import finagent.prompt.custom as custom
    original_parse=custom.parse_semi_formatted_xml;original_create=driver.Provider.create_completion
    def create(self,*args,**kwargs):
        text,info=original_create(self,*args,**kwargs);CTX.set(info['request_hash']);return text,info
    def parse(text):
        key=CTX.get();normalized,applied=canonical_markup(text,key,witness)
        value,soup=original_parse(normalized)
        if applied:
            expected={name:re.search('<'+name+'>(.*?)</'+name+'>',text,re.S).group(1).replace('\r','').replace('\t','').replace('\n','') for name in ['analysis','summary']}
            if value!=expected:raise ValueError('Native parsed field text changed')
            event={'request_hash':key,'response_sha256':witness['response_sha256'],'normalized_response_sha256':witness['normalized_response_sha256'],'exact_field_text_preserved':True,'new_model_response_requested':False}
            out.mkdir(parents=True,exist_ok=True)
            with (out/'xml_alias_events.lock').open('a+') as lock:
                fcntl.flock(lock,fcntl.LOCK_EX)
                with (out/'xml_alias_events.jsonl').open('a') as stream:stream.write(json.dumps(event,sort_keys=True)+'\n');stream.flush();os.fsync(stream.fileno())
        return value,soup
    driver.Provider.create_completion=create;custom.parse_semi_formatted_xml=parse

def validate_prefixes(out,witness,*,root=ROOT):
    from validate_publication_replay import compare,read
    rows=[]
    for source in witness['prefixes']:
        target=out/'decisions.jsonl' if source['arm']=='shared_training' else out/'validation_arms'/source['arm']/'decisions.jsonl'
        if not target.exists():raise ValueError('An uncached request appeared before required prefix reconstruction')
        old=read(Path(root)/source['path']);new=read(target)
        if len(old)!=source['records'] or len(new)<len(old):raise ValueError('Completed prefix is missing records')
        errors,delta=compare(old,new[:len(old)])
        if errors:raise ValueError('Original completed history changed: '+str(errors[:3]))
        rows.append({'arm':source['arm'],'records':len(old),'original_sha256':source['sha256'],'reconstructed_path':str(target.relative_to(root)),'reconstructed_sha256':sha256(target),'maximum_numeric_difference':delta[0],'difference_count':0})
    events=out/'xml_alias_events.jsonl'
    if not events.exists():raise ValueError('Witnessed response alias has not been exercised')
    actual=[json.loads(x) for x in events.read_text().splitlines()]
    if len(actual)!=1 or actual[0]['request_hash']!=witness['request_hash'] or not actual[0]['exact_field_text_preserved']:raise ValueError('Unexpected response alias invocation')
    return {'status':'all_original_completed_prefixes_and_single_alias_match','prefixes':rows,'alias_events_sha256':sha256(events),'records':sum(x['records'] for x in rows),'source_failure_still_preserved':True,'full_source_completion_claim':False}
