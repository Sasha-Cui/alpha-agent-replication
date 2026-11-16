#!/usr/bin/env python3
"""Close release metadata and new supplements without rerunning scientific work."""
from pathlib import Path
from datetime import datetime,timezone
import copy,fcntl,hashlib,io,json,os,shutil,stat,subprocess,sys,tarfile,traceback
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'scripts'),str(R/'src')]
from fidelity_package_core_v2 import digest,copy_durable,scan_secret,credential_name
from alpha_evolve.publication_llm import CohortOpenRouter
U=R/'paper_runs/fidelity_completion_v2';F=R/'artifacts/fidelity_completion_v2'
COPY=F/'archive_copy_after_migration_v2_20260926';D=F/'release_closure_20260926_v1';S=F/'final_package_setup_20260922'
B=Path('/nfs/roberts/project/pi_jss233/zc362/_workspace/storage_operations/2026-09-24-alpha-evolve-migration');C=B/'cache_cleanup_after_migration_v1'
PUB=U/'release_closure_v1';PRIMARY=R/'archives/fidelity_completion_v2_closure_20260926';BACKUP=F/'packages/fidelity_completion_v2_closure_20260926'
LSHA='54c381b2fc56babb96ff8d35e5e38e319feee4029ee053a96001f4d1956664fb'
def now():return datetime.now(timezone.utc).isoformat()
def need(ok,msg):
 if not ok:raise RuntimeError(msg)
def read(p):return json.loads(Path(p).read_text())
def save(p,d):
 with Path(p).open('x') as f:json.dump(d,f,indent=2,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
def write(p,t):
 with Path(p).open('x') as f:f.write(t);f.flush();os.fsync(f.fileno())
def total():
 p=R/'runs/economic_fidelity/openrouter'
 with (p/'project_spend.lock').open('r+') as f:
  fcntl.flock(f,fcntl.LOCK_EX);raw=(p/'project_spend.json').read_bytes();need(hashlib.sha256(raw).hexdigest()==LSHA,'Ledger changed')
  amount,_=CohortOpenRouter.totals(json.loads(raw),'release_closure');need(amount<1000,'Budget limit exceeded')
 return amount
def archives_unchanged():
 for row in read(B/'migration_v4/protocol.json')['existing_archive_stats']:
  p=Path(row['path']);s=p.stat()
  need(not p.is_symlink() and s.st_ino==row['inode'] and s.st_size==row['size'] and stat.S_IMODE(s.st_mode)==row['mode'] and s.st_mtime_ns==row['mtime_ns'],'Original archive metadata changed')
def supplement(rows,target,public):
 expected={}
 for name,p in rows:
  p=Path(p);need(p.is_file() and not p.is_symlink(),'Input not regular')
  need(not Path(name).is_absolute() and '..' not in Path(name).parts and not credential_name(name) and name not in expected,'Unsafe/duplicate member')
  if public:scan_secret(p.read_bytes(),name)
  expected[name]={'sha256':digest(p),'bytes':p.stat().st_size}
 inventory=json.dumps({'scope':'Later storage/copy/release metadata; original scientific archives unchanged. Full intermediate migration inventories remain at referenced durable project paths.','public':public,'files':expected},indent=2,sort_keys=True).encode()+b'\n'
 with tarfile.open(target,'x:gz',compresslevel=6,format=tarfile.PAX_FORMAT) as tar:
  for name,p in rows:
   p=Path(p);record=expected[name];need(digest(p)==record['sha256'],'Input changed')
   info=tarfile.TarInfo(name);info.size=record['bytes'];info.mode=0o400;info.mtime=0
   with p.open('rb') as f:tar.addfile(info,f)
   need(digest(p)==record['sha256'],'Input changed during packaging')
  info=tarfile.TarInfo('SUPPLEMENT_INVENTORY.json');info.size=len(inventory);info.mode=0o400;info.mtime=0;tar.addfile(info,io.BytesIO(inventory))
 expected['SUPPLEMENT_INVENTORY.json']={'sha256':hashlib.sha256(inventory).hexdigest(),'bytes':len(inventory)}
 with target.open('rb') as f:os.fsync(f.fileno())
 seen=set()
 with tarfile.open(target,'r:gz') as tar:
  for info in tar:
   need(info.isfile() and info.name in expected and info.name not in seen,'Unexpected member')
   h=hashlib.sha256();f=tar.extractfile(info)
   for block in iter(lambda:f.read(4*1024*1024),b''):h.update(block)
   need(h.hexdigest()==expected[info.name]['sha256'] and info.size==expected[info.name]['bytes'],'Supplement readback failed');seen.add(info.name)
 need(seen==set(expected),'Missing supplement member');target.chmod(0o400);h=digest(target)
 second=copy_durable(target,BACKUP/target.name,h)
 return {'path':str(target),'sha256':h,'bytes':target.stat().st_size,'members':len(seen),'all_member_readbacks_pass':True,'second_copy':second['path'],'second_copy_sha256_verified':True,'different_inode':second['independent_inode'],'different_project_allocation':False}
def main():
 need(not (D/'started.json').exists(),'Existing finalization; preserve and diagnose')
 for p in [PUB,PRIMARY,BACKUP,U/'release_completion_v1.json']:need(not os.path.lexists(p),'Existing closure output')
 states=subprocess.check_output(['/opt/slurm/current/bin/sacct','-X','-n','-j','27480268,27527518,27549793','-o','JobIDRaw,State,ExitCode','-P'],text=True)
 for jid in ['27480268','27527518','27549793']:need(jid+'|COMPLETED|0:0' in states,'Required job not complete')
 receipt=read(COPY/'copy_completion.json');plan=read(COPY/'copy_protocol.json');clean=read(C/'cleanup_complete.json')
 need(receipt['status']=='complete_archives_with_verified_durable_file_copies' and receipt['copy_continuation_job']=='27549793','Copy receipt differs')
 need(digest(COPY/'copy_completion.json')==digest(U/'publication_bundle_manifest_v2.json'),'Copy manifests differ')
 for row in plan['bindings']:need(digest(row['path'])==row['sha256'],'Copy binding changed '+row['path'])
 need(read(B/'postmigration_verification_v1/validation.json')['status']=='pass_independent_postmigration_verification','Migration unverified')
 need(clean['status']=='complete_seven_authorized_installer_build_caches','Cleanup incomplete')
 for path in clean['deleted_paths']:
  p=Path(path);need(not os.path.lexists(p) and not os.path.lexists(p.with_name('.'+p.name+'.cache-cleanup-retired-20260925')),'Cache remains')
 need(digest(clean['provenance_archive'])==clean['provenance_archive_sha256'],'Provenance backup changed')
 checks=[]
 for row in receipt['archive_records']:
  p,q=Path(row['path']),Path(row['second_copy']);a,b=p.stat(),q.stat()
  need(p.is_file() and q.is_file() and not p.is_symlink() and not q.is_symlink(),'Archive type changed')
  need(a.st_size==b.st_size==row['bytes'] and not ((a.st_mode|b.st_mode)&0o222),'Archive size/mode changed')
  need((a.st_dev,a.st_ino)!=(b.st_dev,b.st_ino),'Same archive inode')
  need(row['second_copy_sha256_verified'] and row['different_inode'] and row['different_project_allocation'] is False,'Copy claims changed')
  oldread=read(S/(row['kind']+'_archive_readback.json'));need(oldread['status']=='pass' and oldread['sha256']==row['sha256'],'Original readback changed')
  checks.append({'kind':row['kind'],'source_inode':a.st_ino,'second_inode':b.st_ino,'bytes':a.st_size,'readonly':True,'completed_copy_job_SHA256_check_reused':row['sha256']})
 archives_unchanged();amount=total()
 old=read(U/'progress.json');need(old['validated_new_records']==3877 and old['full_original_paper_replications_established']==0 and old['strict_alpha_five_attempt_comparison_blocked'],'Scientific scope changed')
 save(D/'started.json',{'utc':now(),'helper_sha256':digest(__file__),'required_jobs':states,'scientific_execution':0})
 save(D/'copy_postcheck.json',{'utc':now(),'status':'pass','copy_receipt_sha256':digest(COPY/'copy_completion.json'),'file_checks':checks,'completed_original_member_readbacks_and_copy_SHA_checks_reused_not_reexecuted':True,'frozen_copy_bindings_verified':len(plan['bindings']),'ledger_sha256':LSHA,'project_committed_usd':amount})
 (D/'before_reporting').mkdir();(D/'staging').mkdir();PRIMARY.mkdir(mode=0o700);BACKUP.mkdir(mode=0o700)
 paths=[U/'STATUS.md',U/'progress.json',U/'SOURCE_REVIEW_PACKET.md',F/'HANDOFF.md',R/'docs/STORAGE_LAYOUT_20260925.md'];before={}
 for i,p in enumerate(paths):
  q=D/'before_reporting'/('%02d_'%i+p.name);shutil.copy2(p,q);need(digest(p)==digest(q) and p.stat().st_ino!=q.stat().st_ino,'Reporting backup failed');before[str(p)]={'sha256':digest(p),'preserved':str(q)};q.chmod(0o400)
 limits=['All69 papers retain separate evidence/gaps; zero full original-paper reproductions are certified.','Original strict Alpha20x5 and complete original four/54 families remain unavailable; observed-history/parameter sensitivities do not replace them.','Reported inconclusive-at-2pp results, pointwise uncertainty, historical model/data and timing limitations remain unchanged. No isolated-LLM, pristine-snapshot or untouched-holdout claim is added.','Independent human source review remains external and unasserted.','Primary archives and all second-file copies reside on JSS; separate-allocation/off-cluster fault isolation is not established.']
 core={'recorded_at_utc':now(),'status':'complete_authorized_feasible_work_with_recorded_limitations','validated_new_records':3877,'papers_with_separate_evidence_and_gaps':69,'full_original_paper_reproductions':0,'new_model_calls':0,'scientific_reruns':0,'ledger_mutations':0,'original_archive_rebuilds':0,'copy_job':'27549793','copy_receipt_sha256':digest(COPY/'copy_completion.json'),'migration_job':'27480268','migration_verification_sha256':digest(B/'postmigration_verification_v1/validation.json'),'cleanup_job':'27527518','cleanup_completion_sha256':digest(C/'cleanup_complete.json'),'cache_deleted_logical_bytes':clean['deleted_logical_bytes'],'cache_observed_filesystem_free_increase_bytes':clean['observed_filesystem_free_increase_bytes'],'shared_filesystem_delta_not_exclusive_attribution':True,'installer_provenance_files_preserved':10210,'installer_provenance_regular_bytes':158849263,'installer_provenance_archive_sha256':clean['provenance_archive_sha256'],'archive_records':receipt['archive_records'],'project_committed_usd_including_uncertainty':amount,'ledger_sha256':LSHA,'independent_human_review':False,'externally_submitted_or_published':False,'original_strict_Alpha_primary_unavailable':True,'original_v2_primary_available':3,'original_v2_primary_denominator':4,'limitations':limits}
 progress=copy.deepcopy(old);progress.update({'status':core['status'],'updated_at_utc':now(),'remaining':['Independent human source review remains external'],'remaining_authorized_feasible_actions':[],'release_completion':'paper_runs/fidelity_completion_v2/release_completion_v1.json','publication_bundle_manifest':'paper_runs/fidelity_completion_v2/publication_bundle_manifest_v2.json','external_and_scope_limitations':limits})
 release='''# Fidelity completion v2 — release closure

The authorized feasible execution, manuscript, archive and storage work is complete. The release is ready for external source review. All 69 papers retain separate evidence and gaps; zero full original-paper reproductions are certified. Independent human review remains external.

The sealed 22-page manuscript V2, five figures, thirteen audit CSVs and 173 input copies are unchanged. The headline remains 3,877 validated new equity records. Final 13-account evidence and all completed source/replay/proof/economic reports are preserved. Workflow, request, prefix, factor and file counts do not represent independent economic successes.

Both original archives passed the archive writer's own locked source/request snapshot and full member readbacks. Public: 1,355 members and 12,712,059 bytes. Private: 30,598 members and 109,301,231,152 bytes, indexing 122,956 logical paths and 369,597,797,858 logical bytes. The missing private second-file copy completed in job 27549793. Source/destination SHA-256, separate inode, read-only mode, stable primary identity and unchanged ledger checks passed. Both primary archives and second-file copies reside on JSS; separate-allocation and off-cluster fault isolation are not established.

Migration 27480268 and independent postmigration verification passed. Cleanup 27527518 removed only the seven approved installer/build caches after verifying their bytes and preserving/readback-checking 10,210 provenance files. Research histories, runtime installations, providers, ledger/response caches and backups remain. The canonical checkout is /nfs/roberts/project/pi_jss233/zc362/alpha_evolve; old BTK project aliases remain, and old scratch paths have no compatibility aliases.

Original strict Alpha20x5 and the complete original four/54 families remain unavailable. Observed-history and Quanta parameter sensitivities retain separate scopes. Economic comparisons keep their reported inconclusive-at-2pp findings, pointwise uncertainty and historical model/data/timing limitations. No scientific work or original archive was rerun or rebuilt for storage closure. All historical and uncertain charges remain unchanged: $371.06592557, below the exclusive $1,000 authorization.

This release does not assert journal submission, publication to an external service, or human source-review attestation. The original scientific archives and 1,532-file methods snapshot remain sealed. Public/private closure supplements preserve later storage/copy/release metadata, executed helpers and installer provenance. Full intermediate migration inventories and receipts remain at their referenced durable project audit paths. The detached release_completion_v1.json records supplement hashes and verified second-file copies.
'''
 status='''# Fidelity completion v2 — authorized feasible work complete

Scientific execution, final accounts/reports, the sealed manuscript, archive readbacks, verified second-file copies and release metadata are complete within the recorded scopes. All 69 papers retain separate evidence and gaps; zero full original-paper reproductions are certified. Independent human source review remains external.

- [Release closure and limitations](release_closure_v1/RELEASE.md)
- [Verified archives and second-file copies](publication_bundle_manifest_v2.json)
- [Release and closure-supplement manifest](release_completion_v1.json)
- [Sealed manuscript V2](manuscript_v2/manuscript_v2.pdf), [text](manuscript_v2/MANUSCRIPT.md), and [numeric/assistant visual QA](manuscript_completion_v2.json)
- [All 69 evidence records](paper_evidence_index.json) and [separate dispositions/gaps](paper_dispositions.json)
- [Final equity accounts](final_equity_accounts_completion_v3.json) and [equity report](final_equity_report_v1/VISUAL_REPORT.md)
- [Quanta parameter completion](quanta_parameter_economic_completion.json) and [report](quanta_parameter_report/VISUAL_REPORT.md)
- [EFS economic completion](efs_economic_completion.json)

The validated-new-equity headline remains 3,877. The main 13-account population includes 538 historical FinMem records; the separate 61-record news sensitivity retains its own scope. Counts of requests, prefixes, factors, files and workflow events are not independent scientific successes. Completed case reports and historical manuscript versions remain preserved.

Original strict Alpha20x5 and the complete original four/54 families remain unavailable. Early aborts and all failed/unattempted work are retained. Observed-history and parameter sensitivities do not fill the missing primary. Economic claims, pointwise intervals and inconclusive-at-2pp findings are unchanged. No isolated-LLM, JKP substitution, pristine historical-snapshot or untouched-holdout claim is added.

All historical and uncertain charges remain: $371.06592557, below the exclusive $1,000 authorization. No model calls, scientific reruns, ledger mutations or original archive rebuilds occurred during storage/release closure. Both primary archives and their separate-inode copies are on JSS; off-cluster or separate-allocation fault isolation is not established.

Prior current-status documents were independently preserved in the private closure audit. The scientific methods snapshot remains unchanged; closure supplements cover later storage/copy/release records.
'''
 packet=(U/'SOURCE_REVIEW_PACKET.md').read_text();needle='This is an interim methods packet, updated September 18, 2026.';need(packet.count(needle)==1,'Unexpected methods introduction')
 packet=packet.replace(needle,'This methods packet includes the September 26, 2026 release closure. Dated scientific descriptions and evidence below retain their original scope.')
 needle='A final immutable bundle remains outstanding while source\nruns are active.';need(packet.count(needle)==1,'Unexpected archive paragraph')
 packet=packet.replace(needle,'Completed scientific bundles and verified second-file copies are indexed in [publication_bundle_manifest_v2.json](publication_bundle_manifest_v2.json). Later storage/copy/release metadata is in the [closure supplements](release_completion_v1.json). Both copies reside on the same JSS allocation.')
 packet+='\\n\\n## Final release closure — September 26, 2026\\n\\nMigration, independent verification, approved seven-cache cleanup with preserved provenance, and the missing private archive copy are complete. Sealed scientific archives, the 22-page V2 manuscript and the 1,532-file September22T220817.612262_0000 methods snapshot remain unchanged. See [release closure](release_closure_v1/RELEASE.md). All69 separate gaps, original charges/failures, unavailable strict Alpha/four/54 scopes and external human review remain unchanged.\\n'
 packet=packet.replace('\\n','\n')
 layout=(R/'docs/STORAGE_LAYOUT_20260925.md').read_text();tick=chr(96)
 needle='Cleanup job 27527518 is submitted; its actual completion is recorded separately under '+tick+'cache_cleanup_after_migration_v1'+tick+'.';need(layout.count(needle)==1,'Unexpected cleanup status')
 layout=layout.replace(needle,'Cleanup job 27527518 completed successfully, removing 12,584,898,540 logical cache bytes after preserving and verifying 10,210 provenance files. Exact manifests and storage measurements remain under '+tick+'cache_cleanup_after_migration_v1'+tick+'.')
 layout=layout.replace('The private second copy and final publication metadata are still pending.','Private copy job 27549793 and final release closure are complete. The current manifest is paper_runs/fidelity_completion_v2/release_completion_v1.json.')
 handoff=(F/'HANDOFF.md').read_text()+'''
\n## September26 — authorized feasible storage/publication closure COMPLETE

Migration27480268 and independent verificationPASS. Cleanup27527518 COMPLETED2h13m21/exit0: exact7cache roots removed,12584898540logicalbytes/12618800128uniqueallocatedfilebytes; observedsharedfilesystemfreeincrease12585009152bytes isnotexclusiveattribution.10210provenancefiles158849263regularbytes preserved/readbackverified in38375070byte cache_provenance_v1.tar.gz SHA602acd5f324142d44989a2ac6d79d943ea9a3ef45b1114eca7cdb98f003e97ec. IndependentpostcheckPASS;5versionwrappersPASS. Research/runtimeinstalls/providers/backups/ledgercaches preserved. Neverreruncleanup.

Privatecopy27549793 COMPLETED8m03/exit0 at2026-09-26T01:04:04UTC. Frozen finish_fidelity_archive_copy_v2.py uses unchangedcoreV2.copy_durable; protocolSHA4ab012accc7ef3b6fc8fb9d3b9b47a99f32e26f6c762ac71bcf4f09d52bfd343. Private109301231152bytes source/copySHA2b8b574a939d46d55ee6497d69c29cffac6991b0dd61d7e99ab899148cf7aa27; separateinode/readonlymode/sourceidentity/unchangedledgerPASS. Public12712059byte original/backup preserved. BOTHpublic/private different_project_allocation=false aftermigration. Nooffclusterfaultisolationclaim. copy_completion.json and publicpublication_bundle_manifest_v2.json match. Original27159153capacityfailure andunexecutedcopyV1 preserved. Neverreruncopy/package/hash orscientificjobs; no originalarchive/member/source-gate/cache-snapshot reruns.

CurrentSTATUS/progress/SOURCE_REVIEW_PACKET/storage-layout/HANDOFF closed honestly; previousversions preserved inrelease_closure_20260926_v1/before_reporting. Publicrelease_completion_v1.json andpublic/privateimmutableclosure supplements recordnewstorage/copy/release metadata, exactexecutedhelpers/protocols, provenancereadbacks andverifiedseparate-filecopies onJSS. Originalscientificarchives,1532methods snapshot,22-pageV2PDF andearliercase reports remainsealed. Finalvalidation: artifacts/fidelity_completion_v2/release_closure_20260926_v1/validation.json. Preserve releasedartifacts; laterchangesnewversion.

All69separategaps,0full-paperreproductions,strictAlpha20x5/originalfour/54unavailability,rawinfinityflags,failed/unattemptedwork andinconclusiveeconomicclaims unchanged.3877validatednewrecords; ledgerSHA54c381b2fc56babb96ff8d35e5e38e319feee4029ee053a96001f4d1956664fb/$371.06592557 unchanged; allhistorical/uncertaincharges retained. OriginalQuanta.0556885 stillRESERVED; no refund/reprice/retry/settlement. Humanreviewexternal; no journal/external-service publication asserted. Allfeasibleauthorizedwork closed; stopcompletionautomation aftercheckingfinalreceipts. Existingstrictheld/dependentjobs untouched.
'''
 staged={}
 for p,body in [(U/'STATUS.md',status),(U/'SOURCE_REVIEW_PACKET.md',packet),(F/'HANDOFF.md',handoff),(R/'docs/STORAGE_LAYOUT_20260925.md',layout)]:
  q=D/'staging'/('%02d_'%len(staged)+p.name);write(q,body);staged[str(p)]=q
 q=D/'staging/progress.json';save(q,progress);staged[str(U/'progress.json')]=q
 write(D/'staging/RELEASE.md',release);save(D/'staging/release_status.json',core)
 public=[('release/RELEASE.md',D/'staging/RELEASE.md'),('release/release_status.json',D/'staging/release_status.json'),('release/STATUS.md',staged[str(U/'STATUS.md')]),('release/progress.json',q),('release/SOURCE_REVIEW_PACKET.md',staged[str(U/'SOURCE_REVIEW_PACKET.md')]),('release/STORAGE_LAYOUT_20260925.md',staged[str(R/'docs/STORAGE_LAYOUT_20260925.md')]),('release/publication_bundle_manifest_v2.json',U/'publication_bundle_manifest_v2.json'),('methods/finish_fidelity_archive_copy_v2.py',R/'scripts/finish_fidelity_archive_copy_v2.py'),('methods/finalize_fidelity_release_v1.py',Path(__file__))]
 private=list(public)+[('private/HANDOFF.md',staged[str(F/'HANDOFF.md')]),('private/copy_postcheck.json',D/'copy_postcheck.json'),('private/cache_provenance_v1.tar.gz',Path(clean['provenance_archive']))]
 for p in sorted(COPY.rglob('*')):
  if p.is_file() and not p.is_symlink():private.append(('private/copy/'+str(p.relative_to(COPY)),p))
 groups={'migration_cutover_v7':['protocol.json','continue_cutover.py','migration_complete.json','preflight_complete.json','events.jsonl'],'migration_v4':['protocol.json','migrate.py','all_copies_verified.json','symlink_relocations.json'],'postmigration_verification_v1':['verify.py','validation.json','runtime_startup_checks.json','verified_symlinks.json'],'cache_cleanup_after_migration_v1':['authorization.json','cleanup.py','cleanup_protocol.json','inspection.json','cleanup_complete.json','postcheck_20260926.json','provenance_archive_readback.json','events.jsonl'],'migration_v6_symlink_metadata_20260925':['audit.json','repair.py','repair_complete.json']}
 for sub,names in groups.items():
  for name in names:private.append(('private/storage/'+sub+'/'+name,B/sub/name))
 for p in sorted((D/'before_reporting').iterdir()):private.append(('private/reporting_before/'+p.name,p))
 pa=supplement(public,PRIMARY/'fidelity_release_closure_public_20260926.tar.gz',True)
 print(json.dumps({'public_supplement_verified':True,'members':pa['members']}),flush=True)
 qa=supplement(private,PRIMARY/'fidelity_release_closure_private_20260926.tar.gz',False)
 save(D/'supplement_readbacks.json',{'utc':now(),'public':pa,'private':qa})
 for path,stage in staged.items():
  need(digest(path)==before[path]['sha256'],'Concurrent reporting edit '+path);Path(path).write_bytes(stage.read_bytes())
 PUB.mkdir(mode=0o755)
 for name in ['RELEASE.md','release_status.json']:shutil.copy2(D/'staging'/name,PUB/name);need(digest(PUB/name)==digest(D/'staging'/name),'Release file mismatch');(PUB/name).chmod(0o400)
 final={**core,'closed_at_utc':now(),'closure_supplements':{'public':pa,'private':qa},'closure_helper_sha256':digest(__file__),'original_scientific_archives_unchanged':True,'current_reporting_preserved_and_updated':True,'detached_manifest_note':'Final manifest is detached from supplement archives to avoid self-referential hashes.'}
 save(U/'release_completion_v1.json',final);(U/'release_completion_v1.json').chmod(0o400);shutil.copy2(U/'release_completion_v1.json',D/'release_completion_v1.copy.json')
 need(digest(U/'release_completion_v1.json')==digest(D/'release_completion_v1.copy.json') and (U/'release_completion_v1.json').stat().st_ino!=(D/'release_completion_v1.copy.json').stat().st_ino,'Detached manifest backup failed');(D/'release_completion_v1.copy.json').chmod(0o400)
 archives_unchanged();need(total()==amount,'Final budget changed')
 current=read(U/'progress.json')
 for key in old:
  if key not in {'status','updated_at_utc','remaining'}:need(current[key]==old[key],'Scientific progress field changed '+key)
 for path,h in [('manuscript_v2/manuscript_v2.pdf','2c156f08bceb13b9b32395d20e501b3461ddea4dc32ccdeaca8c70981601172c'),('accounts/validation.json','2465ad36c24293d214d3ce3f1a61e766a4dec9743d5f6f39e0b3a28e022be6a3')]:need(digest(U/path)==h,'Sealed scientific artifact changed')
 for p in [COPY/'copy_completion.json',U/'publication_bundle_manifest_v2.json',C/'cleanup_complete.json',C/'postcheck_20260926.json',D/'supplement_readbacks.json']:p.chmod(0o400)
 result={'utc':now(),'status':'pass_final_authorized_release_closure','final_release_manifest_sha256':digest(U/'release_completion_v1.json'),'final_release_manifest':str(U/'release_completion_v1.json'),'scientific_progress_fields_unchanged':True,'before_reporting':before,'updated_reporting_hashes':{p:digest(p) for p in staged},'original_archives_and_manuscript_unchanged':True,'public_supplement_privacy_scan_pass':True,'public_supplement_members':pa['members'],'private_supplement_members':qa['members'],'all_new_supplement_members_readback_SHA256_verified':True,'supplements_have_verified_different_inode_second_file_copies':True,'same_JSS_allocation_disclosed':True,'ledger_sha256':LSHA,'project_committed_usd_including_uncertainty':amount,'authorized_feasible_actions_remaining':[],'independent_human_review':False,'original_strict_Alpha_primary_unavailable':True,'scientific_or_API_execution':0,'automation_may_stop':True}
 save(D/'validation.json',result);(D/'validation.json').chmod(0o400);Path(__file__).chmod(0o400)
 print(json.dumps({'status':result['status'],'public_supplement_bytes':pa['bytes'],'private_supplement_bytes':qa['bytes'],'public_members':pa['members'],'private_members':qa['members'],'project_committed_usd':amount,'automation_may_stop':True}),flush=True)
if __name__=='__main__':
 try:main()
 except Exception:
  if not (D/'failure.json').exists():save(D/'failure.json',{'utc':now(),'traceback':traceback.format_exc(),'preserve_partial_outputs_do_not_blindly_rerun':True})
  raise

