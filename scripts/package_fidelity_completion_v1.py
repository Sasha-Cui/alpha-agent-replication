"""Create byte-indexed private and ordinary public archives after fresh locked gates.
No paid requests or native source/factor/model/account/analysis execution.
"""
from pathlib import Path
from datetime import datetime,timezone
from contextlib import closing
from collections import Counter
import sys,os,json,hashlib,sqlite3,csv,tarfile,subprocess,socket,re,posixpath,stat
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'src'),str(R/'scripts')]
from fidelity_package_core_v1 import digest,hash_current,stable_identity,safe_member,credential_name,locked_snapshot,add_bytes,add_payload,verify_tar,copy_durable
U=R/'paper_runs/fidelity_completion_v2';P=R/'artifacts/fidelity_completion_v2';S=P/'final_package_setup_20260922'

def now():return datetime.now(timezone.utc).isoformat()
def read(p):return json.loads(Path(p).read_text())
def save(p,obj):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x') as f:json.dump(obj,f,indent=2,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
def require(ok,message):
    if not ok:raise ValueError(message)
def deny_network(*a,**k):raise RuntimeError('Final packaging forbids network/model requests')

def completed_receipt(path):
    d=read(path)
    for pk,hk in [('pdf','pdf_sha256'),('numeric_validation','numeric_validation_sha256'),('assistant_visual_review','assistant_visual_review_sha256'),('preservation','preservation_sha256')]:
        if pk in d:require(digest(R/d[pk])==d[hk],'Completed manuscript/report changed: '+pk)
    require(not d.get('independent_human_review',False),'Unestablished human review claim')
    return d

def additional_gates():
    from alpha_evolve.fidelity_efs_pool_evidence_v2 import validate_efs_trial
    from alpha_observed_history_evidence_v2 import validate_observed_library
    from quanta_paper_evaluation_evidence_v7 import validate_fixed
    from native_secondary_evidence_v2 import validate_library,validate_execution_identity
    from admit_finagent_amzn_manual_v1 import admit
    result={'manual_AMZN':admit(),'EFS_sources':{t:validate_efs_trial(R,t) for t in ['gpt41_1','gpt41_2','gpt41_3','deepseek_v3_1','deepseek_v3_2','deepseek_v3_3']}}
    _,result['observed_Alpha_all20']=validate_observed_library(P/'alphaagent_observed20_fixed_library/library_manifest.json',R)
    _,result['Quanta_parameter_fixed']=validate_fixed(P/'quantaalpha_paper_parameters_fixed_library/library_manifest.json',R)
    result['released_Quanta_libraries']={}
    for name in ['quantaalpha_bounded_fixed_library']+[f'quantaalpha_bounded_task_{i:02d}_fixed_library' for i in range(7)]:
        _,ev=validate_library(P/name/'library_manifest.json',R,P);result['released_Quanta_libraries'][name]=ev
    historic=read(P/'manuscript_v2_setup_20260922/historical_method_bindings.json')['bindings']
    old={(x['source'],x['recorded_sha256']):R/x['recorded_method_copy'] for x in historic}
    result['economic_bindings']={}
    for name in ['efs_pooled_analysis','alpha_observed_history_sensitivity','quanta_paper_parameter_sensitivity','native_grouped_oos_quantaalpha','native_secondary_oos_quantaalpha']:
        folder=U/name;done=read(folder/'completion.json')
        for f,h in done['outputs'].items():require(digest(folder/f)==h,'Economic output changed: '+name+'/'+f)
        for f,h in done.get('source_files',{}).items():
            path=R/f
            if digest(path)!=h:path=old.get((f,h))
            require(path is not None and digest(path)==h,'Executed economic method changed: '+f)
        for f,h in done.get('private_outputs',{}).items():require(digest(P/name/f)==h,'Private economic output changed')
        evfile=folder/'execution_evidence.json';n=0
        for row in read(evfile) if evfile.exists() else []:
            if 'run' not in row:continue
            run=P/row['run'];n+=1
            for f,k in [('completion.json','completion_sha256'),('execution_recipe.json','recipe_sha256'),('independent_accounts/validation.json','account_validation_sha256'),('independent_accounts/account.csv','account_sha256')]:
                if k in row:require(digest(run/f)==row[k],'Saved execution binding changed: '+row['run']+'/'+f)
            account=read(run/'independent_accounts/validation.json');require(account['status']=='pass','Native account receipt failed')
            complete=read(run/'completion.json')
            for f,k in [('ret.pkl','returns_sha256'),('qlib_res.csv','metrics_sha256'),('oos_config.yaml','config_sha256')]:
                if k in complete:require(digest(run/f)==complete[k],'Saved return/config changed')
            identity=validate_execution_identity(row['run'],row['execution'],P)
            for k,v in identity.items():
                if k in row:require(row[k]==v,'Prediction/execution identity changed')
        result['economic_bindings'][name]={'completion_sha256':digest(folder/'completion.json'),'executions_checked':n}
    for group in ['grammar_101_103','gpt41','deepseek_v3']:
        folder=U/'efs_pooled'/group;d=read(folder/'completion.json');require(d['status']=='complete' and d['new_model_calls']==0,'EFS pool incomplete')
        for f,h in d['output_sha256'].items():require(digest(folder/f)==h,'EFS pooled output changed')
        for f,h in d['private_weights_sha256'].items():require(digest(P/'efs_pooled'/group/f)==h,'EFS pooled holdings changed')
        result['economic_bindings']['efs_pool_'+group]={'completion_sha256':digest(folder/'completion.json')}
    family=read(U/'project_primary_family/latest.json');folder=R/family['snapshot'];done=read(folder/'completion.json');comparisons=read(folder/'comparisons.json')
    require(digest(folder/'completion.json')==family['completion_sha256'] and len(done['expected_cases'])==4 and len(comparisons)==3,'Primary family scope changed')
    require(all(not x['conditional_positive_increment_familywise'] for x in comparisons),'Unsupported new primary claim')
    for f,h in done['outputs'].items():require(digest(folder/f)==h,'Primary family output changed')
    result['primary_family']={'available':3,'denominator':4,'completion_sha256':digest(folder/'completion.json'),'strict_Alpha_unavailable':True}
    return result

def cache_transaction(primary):
    from fidelity_archive_readiness_v5 import terminal_witnesses,closure_artifacts,current_source_gates,QUANTA_KEY,validate_returned_reservation,assess_snapshot
    from alpha_evolve.publication_llm import CohortOpenRouter
    cache=R/'runs/economic_fidelity/openrouter';out=primary/'cache_snapshot';out.mkdir(mode=0o700)
    with locked_snapshot([cache/'project_spend.lock',cache/'cohort_response_journal.lock']) as locks:
        raw=(cache/'project_spend.json').read_bytes();state=json.loads(raw);mapping=read(cache/'technical_recoveries.json');cost=CohortOpenRouter.totals(state,'archive_snapshot')[0]
        require(cost<1000,'Exclusive total authorization reached')
        closures=closure_artifacts(R);require(all(x['pass'] for x in closures),'Actual final closures missing')
        gates,orphan=current_source_gates(R);extra=additional_gates();witnesses=terminal_witnesses(R)
        allowed=set(witnesses)|{QUANTA_KEY};require(not any(v['status']=='reserved' and k not in allowed for k,v in state['calls'].items()),'Unclassified reservation blocks snapshot')
        with closing(sqlite3.connect('file:'+str(cache/'response_cache.sqlite3')+'?mode=ro',uri=True)) as source:
            source.execute('BEGIN')
            cache_hits={k for k in witnesses if source.execute('SELECT 1 FROM responses WHERE request_hash=?',(k,)).fetchone()}
            matches=[];journal_hits=set();offset=0;h=hashlib.sha256();needles=[k.encode() for k in allowed];before=stable_identity(cache/'cohort_responses.jsonl')
            with (cache/'cohort_responses.jsonl').open('rb') as a,(out/'cohort_responses.jsonl').open('xb') as b:
                for line in a:
                    h.update(line);b.write(line)
                    if any(x in line for x in needles):
                        body=json.loads(line);key=body.get('request_hash')
                        if key in witnesses:journal_hits.add(key)
                        if key==QUANTA_KEY:matches.append((offset,line))
                    offset+=len(line)
                b.flush();os.fsync(b.fileno())
            require(stable_identity(cache/'cohort_responses.jsonl')==before,'Journal changed under snapshot lock')
            row=source.execute('SELECT body FROM responses WHERE request_hash=?',(QUANTA_KEY,)).fetchone()
            returned=validate_returned_reservation(state['calls'],mapping,orphan,None if row is None else row[0],matches,sources_closed=True,fresh=True)
            assessment=assess_snapshot(state['calls'],witnesses,mapping,cache_hits,journal_hits,sources_closed=True,fresh=True,returned=returned)
            require(assessment['cache_snapshot_request_gate_pass'] and assessment['unclassified_reserved_count']==0,'Request eligibility failed')
            with closing(sqlite3.connect(out/'response_cache.sqlite3')) as destination:source.backup(destination)
            with closing(sqlite3.connect('file:'+str(out/'response_cache.sqlite3')+'?mode=ro',uri=True)) as duplicate:
                require(duplicate.execute('PRAGMA integrity_check').fetchone()[0]=='ok','SQLite snapshot corrupt')
                left=source.execute('SELECT request_hash,body FROM responses ORDER BY request_hash');right=duplicate.execute('SELECT request_hash,body FROM responses ORDER BY request_hash');count=0
                while True:
                    x,y=left.fetchone(),right.fetchone();require(x==y,'SQLite logical snapshot mismatch')
                    if x is None:break
                    count+=1
            source.rollback()
        for name,data in [('project_spend.json',raw),('technical_recoveries.json',(cache/'technical_recoveries.json').read_bytes())]:
            with (out/name).open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
        require((cache/'project_spend.json').read_bytes()==raw and read(cache/'technical_recoveries.json')==mapping,'Canonical state changed under lock')
        receipt={'status':'pass_own_locked_source_and_request_snapshot','recorded_at_utc':now(),'cost_including_all_uncertain_usd':cost,'ledger_sha256':hashlib.sha256(raw).hexdigest(),'journal_sha256':h.hexdigest(),'journal_bytes':offset,'sqlite_rows_identical':count,'closure_artifacts':closures,'source_gates':gates,'additional_fresh_gates':extra,'request_assessment':assessment,'outer_lock_reentries':len(locks['reentries']),'ledger_mutations':0,'new_model_calls':0,'native_source_model_account_analysis_reruns':0}
        save(S/'own_snapshot_gate.json',receipt)
    rows=[]
    for p in sorted(out.iterdir()):rows.append({'path':str(p),'logical_path':'runs/economic_fidelity/openrouter/'+p.name,'sha256':hash_current(p),'bytes':p.stat().st_size,'private':True,'mode':stat.S_IMODE(p.stat().st_mode),'mtime_ns':p.stat().st_mtime_ns})
    require(next(x for x in rows if x['logical_path'].endswith('cohort_responses.jsonl'))['sha256']==receipt['journal_sha256'],'Copied journal changed')
    return receipt,rows

def public_ok(path):
    if credential_name(str(path)):return False,'credential filename'
    if path.name=='llm_decisions.csv' or path.name.endswith('_selections.json'):return False,'holdings-level decisions retained only in private archive'
    if path.suffix.lower() not in {'.py','.sh','.md','.json','.csv','.txt','.toml','.yaml','.yml','.png','.pdf','.tex','.bib','.sbatch','.ipynb'}:return False,'not an allowlisted review format'
    if path.suffix=='.csv':
        with path.open() as f:fields=set(next(csv.reader(f),[]))
        if fields & {'permno','gvkey','cusip','selected_assets','holding_weight','adj_close','ticker_return'} or ('date' in fields and fields & {'instrument','stock_id','price','open','close','volume','symbol','ticker','asset','security_id'}):return False,'security-level table'
    if path.suffix=='.json':
        d=read(path)
        def bad(x):
            if isinstance(x,dict):
                if 'date' in x and set(x)&{'symbol','ticker','instrument','permno','gvkey','cusip','security_id'}:return True
                if any(k in x and isinstance(x[k],(list,dict)) and x[k] for k in ['messages','holdings','positions','selected_assets','prices','daily_prices','portfolio_weights','embedding','embeddings','response_body','request_body']):return True
                return any(bad(v) for v in x.values())
            if isinstance(x,list):return any(bad(v) for v in x)
            return False
        if bad(d):return False,'raw prompt or holdings-level structured payload'
    return True,'first-party code, metadata, aggregate results or verified presentation'

def collect(protocol,cache_rows):
    paths=set();links=[];omitted=[]
    for prefix in protocol['checkout_roots']:
        base=R/prefix
        for parent,dirs,files in os.walk(base,followlinks=False):
            dirs.sort();files.sort();folder=Path(parent)
            for name in list(dirs):
                p=folder/name
                if p==S or p==P/'packages' or name in {'.git','__pycache__','.pytest_cache','.venv','venv'}:dirs.remove(name);continue
                if p.is_symlink():raise ValueError('Directory symlink requires separate pinned inventory: '+str(p))
            for name in files:
                p=folder/name
                if credential_name(str(p)) or name.endswith(('.lock','.pyc')):omitted.append({'path':str(p.relative_to(R)),'reason':'credential, lock or bytecode; not archived'});continue
                if p.is_symlink():
                    target=p.resolve();require(target.is_file() and target.is_relative_to(R),'Unbound external/missing symlink target');links.append({'path':str(p.relative_to(R)),'original_link':os.readlink(p),'target':str(target.relative_to(R))});paths.add(target)
                else:paths.add(p)
    for name in protocol['extra_checkout_files']:paths.add(R/name)
    manifest=read(U/'source_review_evidence_manifest.json')
    for row in manifest['evidence']:
        p=R/row['path'];require(digest(p)==row['sha256'],'Current methods snapshot stale');paths.add(p)
    for row in read(P/'manuscript_v2_setup_20260922/historical_method_bindings.json')['bindings']:
        paths.add(R/row['recorded_method_copy'])
    # Explicit old execution/data archives preserve earlier evidence without rewriting it.
    external=[]
    for row in protocol['external_archives']:
        p=Path(row['path']);external.append({'path':str(p),'logical_path':row['logical_path'],'sha256':row.get('sha256'),'bytes':p.stat().st_size,'private':True,'mode':stat.S_IMODE(p.stat().st_mode),'mtime_ns':p.stat().st_mtime_ns})
    for p in S.iterdir():
        if p.is_file() and p.name not in {'package_started.json','package_submission_intent.json','package_submission_response.json','package_job.json'} and not p.name.endswith('.log'):
            paths.add(p)
    large={x['path']:x for x in (json.loads(line) for line in (S/'large_payload_hashes.jsonl').read_text().splitlines())}
    rows=[];withheld=[]
    for p in sorted(paths):
        rel=str(p.relative_to(R));before=stable_identity(p);old=large.get(rel)
        mutable=rel in protocol['mutable_reporting_paths']
        if old and not mutable:
            require((before[0],before[1],before[2],before[3])==(old['dev'],old['ino'],old['bytes'],old['mtime_ns']),'Pre-hashed payload changed: '+rel);h=old['sha256']
        else:h=hash_current(p)
        candidate=not rel.startswith('artifacts/') and not rel.startswith('runs/')
        allowed,reason=public_ok(p) if candidate else (False,'private evidence')
        if candidate and not allowed:withheld.append({'path':rel,'sha256':h,'bytes':before[2],'reason':reason})
        rows.append({'path':str(p),'logical_path':rel,'sha256':h,'bytes':before[2],'private':not allowed,'mode':stat.S_IMODE(p.stat().st_mode),'mtime_ns':before[3]})
    for row in external:
        h=hash_current(Path(row['path']),row['sha256']);row['sha256']=h;rows.append(row)
    rows+=cache_rows
    require(len({x['logical_path'] for x in rows})==len(rows),'Duplicate logical archive path')
    represented={x['logical_path'] for x in rows}
    require(all(x['target'] in represented for x in links),'A symlink target is not archived')
    public_names={x['logical_path'] for x in rows if not x['private']}
    private_names={x['logical_path'] for x in rows if x['private']}
    link_checks=[]
    from urllib.parse import unquote
    for row in rows:
        if row['private'] or not row['logical_path'].startswith('paper_runs/fidelity_completion_v2/') or not row['logical_path'].endswith('.md'):continue
        body=Path(row['path']).read_text()
        for link in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)',body):
            if link.startswith(('http://','https://','#','mailto:')):continue
            target=posixpath.normpath(posixpath.join(posixpath.dirname(row['logical_path']),unquote(link.split('#')[0])))
            if target in public_names:kind='included_public'
            elif target in private_names:kind='explicit_private_reference'
            elif any(n.startswith(target.rstrip('/')+'/') for n in public_names):kind='included_public_directory'
            else:raise ValueError('Missing or unclassified current-report archive link: '+target)
            link_checks.append({'source':row['logical_path'],'target':target,'classification':kind})
    save(S/'public_link_validation.json',{'status':'pass','links':link_checks})
    save(S/'package_inventory.json',{'recorded_at_utc':now(),'files':rows,'symlinks':links,'withheld_from_public':withheld,'omitted_nonpayload':omitted,'status':'frozen_selected_payloads_before_archiving'})
    return rows,links,withheld,omitted

def build_archive(path,rows,*,private,links,withheld,gate,protocol):
    require(not path.exists(),'Refuse archive overwrite');expected={};stored=set();index=[];logical_bytes=0
    with path.open('xb') as destination:
        with tarfile.open(fileobj=destination,mode='w:gz',compresslevel=3) as tar:
            for i,row in enumerate(rows,1):
                if not private and row['private']:continue
                h=row['sha256'];name='blobs/'+h if private else safe_member(row['logical_path']);p=Path(row['path'])
                if private and h in stored:hash_current(p,h)
                else:
                    add_payload(tar,name,p,h,0o600 if private else (0o755 if row['mode']&0o111 else 0o644));expected[name]={'sha256':h,'bytes':row['bytes']};stored.add(h)
                index.append({k:row[k] for k in ['logical_path','sha256','bytes','private','mode','mtime_ns']});logical_bytes+=row['bytes']
                if i%1000==0:print(json.dumps({'stage':'private' if private else 'public','logical_files_seen':i,'members':len(expected),'logical_bytes':logical_bytes}),flush=True)
            metadata={'schema':'fidelity-private-content-index-v1' if private else 'fidelity-public-review-index-v1','files':index,'symlinks':links if private else [],'withheld_from_public':withheld,'cost_snapshot_usd':gate['cost_including_all_uncertain_usd'],'own_snapshot_gate_sha256':digest(S/'own_snapshot_gate.json'),'protocol_sha256':digest(S/'package_protocol.json'),'original_reservations_unchanged':True,'independent_human_review':False,'full_paper_reproductions':0,'restoration':'Private blobs preserve every indexed path independently. Symlink text and target bytes are indexed. Never extract over the live checkout. Exact absolute native paths require deliberate restoration; this is not a pristine historical environment or a fresh full-paper execution.'}
            raw=(json.dumps(metadata,indent=2,sort_keys=True)+'\n').encode();add_bytes(tar,'PACKAGE_INDEX.json',raw,0o600 if private else 0o644);expected['PACKAGE_INDEX.json']={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
            readme=(S/'BUNDLE_README.md').read_bytes();add_bytes(tar,'BUNDLE_README.md',readme,0o600 if private else 0o644);expected['BUNDLE_README.md']={'sha256':hashlib.sha256(readme).hexdigest(),'bytes':len(readme)}
        destination.flush();os.fsync(destination.fileno())
    validation=verify_tar(path,expected);path.chmod(0o400)
    save(S/('private_archive_readback.json' if private else 'public_archive_readback.json'),{**validation,'path':str(path),'logical_files':len(index),'logical_bytes':logical_bytes,'withheld_public_files':len(withheld),'tar_sha256':validation['sha256'],'archive_bytes':path.stat().st_size})
    return validation

def main():
    os.umask(0o077);protocol=read(S/'package_protocol.json')
    require(not (S/'package_started.json').exists(),'Existing package attempt: inspect, never restart blindly')
    for row in protocol['bindings']:require(digest(Path(row['path']))==row['sha256'],'Frozen package dependency changed')
    hashes=read(S/'large_hash_completion.json');require(hashes['status']=='pass_read_only_large_payload_hashes_no_archive' and hashes['job']==protocol['hash_job'],'Actual payload hash job incomplete')
    require(digest(S/'large_payload_hashes.jsonl')==hashes['hash_rows_sha256'],'Hash manifest changed')
    for name in ['manuscript_completion_v2.json','final_equity_report_completion_v1.json']:completed_receipt(U/name)
    require(read(U/'manuscript_completion_v2.json')['final13_accounts_complete'],'Final manuscript missing accounts')
    save(S/'package_started.json',{'started_utc':now(),'job':os.environ.get('SLURM_JOB_ID'),'protocol_sha256':digest(S/'package_protocol.json')})
    # Refresh methods copies only after the read-only hashing job has finished.
    subprocess.run([sys.executable,str(R/'scripts/build_fidelity_source_review_manifest_v3.py')],cwd=R,check=True)
    socket.socket.connect=deny_network;socket.create_connection=deny_network
    primary=Path(protocol['primary_directory']);secondary=Path(protocol['second_directory']);primary.mkdir(mode=0o700,parents=False,exist_ok=False);secondary.mkdir(mode=0o700,parents=True,exist_ok=False)
    gate,cache=cache_transaction(primary);rows,links,withheld,omitted=collect(protocol,cache)
    public=primary/'fidelity_review_v2_20260922.tar.gz';private=primary/'fidelity_execution_v2_20260922.tar.gz'
    pub=build_archive(public,rows,private=False,links=links,withheld=withheld,gate=gate,protocol=protocol)
    full=build_archive(private,rows,private=True,links=links,withheld=withheld,gate=gate,protocol=protocol)
    copies=[]
    for p,result in [(public,pub),(private,full)]:copies.append(copy_durable(p,secondary/p.name,result['sha256']))
    require(digest(R/'runs/economic_fidelity/openrouter/project_spend.json')==gate['ledger_sha256'],'Canonical ledger changed after snapshot; diagnose before declaring final current closure')
    result={'status':'complete_verified_public_private_archives_and_durable_second_copies','recorded_at_utc':now(),'job':os.environ.get('SLURM_JOB_ID'),'archives':[{'path':str(p),'sha256':v['sha256'],'bytes':p.stat().st_size,'member_count':v['members'],'second_copy':c} for (p,v),c in zip([(public,pub),(private,full)],copies)],'own_snapshot_gate':str((S/'own_snapshot_gate.json').relative_to(R)),'own_snapshot_gate_sha256':digest(S/'own_snapshot_gate.json'),'payload_inventory_sha256':digest(S/'package_inventory.json'),'protocol_sha256':digest(S/'package_protocol.json'),'public_withheld_records':len(withheld),'omitted_credentials_locks_bytecode':len(omitted),'symlinks_indexed_with_target_bytes':len(links),'public_credentials_or_security_level_payloads':0,'new_model_calls':0,'scientific_jobs_rerun':0,'ledger_mutations':0,'independent_human_review':False,'full_paper_reproductions':0,'strict_Alpha_primary_still_unavailable':True,'primary_family_available':3,'primary_family_denominator':4,'project_cost_including_uncertain_usd':gate['cost_including_all_uncertain_usd'],'manuscript_pdf_sha256':read(U/'manuscript_completion_v2.json')['pdf_sha256']}
    save(S/'package_completion.json',result);save(U/'publication_bundle_manifest_v1.json',result);print('FIDELITY_ARCHIVES_AND_DURABLE_COPIES_COMPLETE',flush=True)
if __name__=='__main__':main()
