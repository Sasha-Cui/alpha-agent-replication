"""Read-only numerical/content/layout checks for the interim manuscript; no study execution."""
from pathlib import Path
from datetime import datetime,timezone
import json,csv,re,math,hashlib,sys
from PIL import Image,ImageStat
import pdfplumber
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'src'))
from alpha_evolve.openrouter_budget import sha256,atomic_json
S=R/'artifacts/fidelity_completion_v2/manuscript_v2_setup_20260922';O=R/'paper_runs/fidelity_completion_v2/manuscript_v2'
def check(value,message):
 if not value:raise ValueError(message)
def rows(name):
 with (O/'audit_tables'/name).open(newline='') as f:return list(csv.DictReader(f))
def equal(a,b):
 if isinstance(b,(list,dict)):return json.loads(a)==b
 if isinstance(b,bool):return a.lower()==str(b).lower()
 if b is None:return a==''
 if isinstance(b,(int,float)):return math.isclose(float(a),b,rel_tol=1e-12,abs_tol=1e-12)
 return a==str(b)
def compare(got,want,keys):
 check(len(got)==len(want),'CSV population mismatch')
 for a in got:
  matches=[b for b in want if all(equal(a[k],b.get(k)) for k in keys)]
  check(len(matches)==1,'CSV identity ambiguity')
  b=matches[0]
  for k,v in b.items():check(k in a and equal(a[k],v),'CSV field mismatch: '+k)
def norm(s):return re.sub(r'\s+',' ',s.replace('–','-').replace('—','-').replace('‑','-').replace('−','-').replace('’',"'").replace('“','"').replace('”','"')).strip()
def luminance(code):
 rgb=[int(code[i:i+2],16)/255 for i in (1,3,5)];v=[x/12.92 if x<=.04045 else ((x+.055)/1.055)**2.4 for x in rgb];return .2126*v[0]+.7152*v[1]+.0722*v[2]
def main():
 D=json.loads((S/'inputs.json').read_text());C=json.loads((O/'draft_contract.json').read_text());M=json.loads((O/'content_model.json').read_text());B=json.loads((O/'draft_build.json').read_text());I=json.loads((O/'input_manifest.json').read_text())
 check(sha256(S/'inputs.json')==I['private_input_bundle_sha256']==B['input_bundle_sha256']==M['source_input_sha256'],'Input bundle changed')
 for b in D['bindings']:check(sha256(R/b['copy'])==b['sha256'],'Copied input changed: '+b['path'])
 check(len(D['bindings'])==173 and len(D['paper_link_validation'])==69,'Input population')
 for b in D['historical_method_bindings']['bindings']:
  check(sha256(R/b['recorded_method_copy'])==b['recorded_sha256'],'Historical method identity')
 check(C['paper_count']==69 and C['new_full_paper_reproductions']==0 and C['legacy_primary_count']==6 and C['v2_primary_available']==3 and C['v2_primary_denominator']==4 and C['new_equity_replay_records']==3877,'Claim contract')
 for k in ('independent_human_review','archive_created','new_source_model_account_analysis_execution'):check(C[k] is False,'Forbidden claim: '+k)
 check(not C['final13_equity_accounts_missing'] and C['AMZN_retry_authorized'] and D['final_equity']['source_count']==13,'Final account status')
 check(sha256(R/'paper_runs/fidelity_completion_v2/accounts/validation.json')==D['final_equity']['validation_sha256'],'Final account hash')
 check(D['archive_request_preflight']['cache_snapshot_request_gate_pass'] and D['archive_request_preflight']['fresh_dual_store_check'] and D['archive_request_preflight']['unclassified_reserved_count']==0,'Request eligibility')
 check(D['budget']['project_committed_usd']<1000 and C['budget_snapshot']['hard_ceiling']==1000 and C['budget_snapshot']['hard_ceiling_exclusive'],'Budget authorization')
 compare(rows('final_equity_aggregate_accounts.csv'),D['aggregate_accounts'],['case','arm'])
 compare(rows('all208_equity_metrics.csv'),D['all_account_performance'],['case','symbol','arm','clock','cost_bps'])
 asset_input=next(b for b in D['bindings'] if b['path'].endswith('visual_tables/asset_comparisons.csv'))
 check(sha256(O/'audit_tables/all13_asset_comparisons.csv')==asset_input['sha256'],'All13 asset CSV exact')
 compare(rows('all_69_papers_full_audit.csv'),D['dispositions']['papers'],['id'])
 compare(rows('all_quanta_parameter_comparisons.csv'),D['parameter_comparisons'],['execution','baseline'])
 compare(rows('frozen_v1_six_primaries.csv'),D['legacy_primaries'],['case'])
 compare(rows('equity_replay_records.csv'),D['progress']['validated_new_replays'],['run'])
 # Primary rows may add display labels, but every canonical field must remain exact.
 compare(rows('v2_primary_available.csv'),D['primary_comparisons'],['project_case'])
 exploratory=rows('exploratory_opening_comparisons.csv')
 check(len(exploratory)==3,'Exploratory population')
 for a in exploratory:
  source=D['alpha_comparisons'] if a['label'].startswith('Observed Alpha') else D['parameter_comparisons']
  matches=[b for b in source if b['execution']=='opening_information' and (a['label'].startswith('Observed Alpha') or b['baseline']==a['baseline'])]
  check(len(matches)==1,'Exploratory identity')
  for k,v in matches[0].items():check(equal(a[k],v),'Exploratory field: '+k)
 prose_blocks='\n'.join(b['text'] for page in M['pages'] for b in page['blocks'] if b['kind'] in ['p','note'])
 for _,_,url in D['references']:check(url in prose_blocks,'Archived bibliography URL altered: '+url)
 check(not re.search(r'https?:\s+//',prose_blocks),'Whitespace inserted into URL scheme')
 model_tables=[b for p in M['pages'] for b in p['blocks'] if b['kind']=='table']
 table_by_audit={b.get('audit'):b for b in model_tables if b.get('audit') and b.get('audit')!='all_69_papers_full_audit.csv'}
 for name,data in [('v2_primary_available.csv',D['primary_comparisons']),('all_quanta_parameter_comparisons.csv',D['parameter_comparisons']),('frozen_v1_six_primaries.csv',D['legacy_primaries'])]:
  cells=' '.join(str(x) for row in table_by_audit[name]['rows'] for x in row)
  for b in data:
   for k in ['full_sample_annualized_effect','primary_ci_low','primary_ci_high']:check(f'{100*float(b[k]):+.3f}' in cells,'Printed numerical mismatch: '+name+'/'+k)
 equity_table=table_by_audit['final_equity_aggregate_accounts.csv']
 check(len(equity_table['rows'])==3,'Equity display population')
 for row,case in zip(equity_table['rows'],['finmem','tradingagents','finagent']):
  pair={a['arm']:a for a in D['aggregate_accounts'] if a['case']==case};x=pair['native']['ending_wealth'];y=pair['buy_hold_matched_clock']['ending_wealth']
  check(str(row[1])==str(pair['native']['observations']),'Equity displayed sessions')
  for cell,value,best in [(row[3],x,x>=y),(row[4],y,y>=x)]:
   check(str(cell).replace('**','')==f'{value:.6f}','Equity wealth rounding')
   check(str(cell).startswith('**')==best and str(cell).endswith('**')==best,'Bold within-row winner including ties')
 check(sum(float(a['records']) for a in rows('equity_replay_records.csv'))==3877,'Equity record headline')
 check(all(not p['full_original_paper_reproduced'] and not p['independent_human_review_complete'] for p in D['dispositions']['papers']),'Paper claim drift')
 figures=[]
 for p in sorted((O/'figures').glob('*.png')):
  with Image.open(p) as im:check(im.width>=1000 and im.height>=500 and max(ImageStat.Stat(im.convert('RGB')).stddev)>15,'Blank/low-quality figure');figures.append({'path':str(p.relative_to(R)),'sha256':sha256(p)})
 check(len(figures)==5,'Figure population')
 pairs=[('#172b4d','#ffffff'),('#172b4d','#eef4f8'),('#ffffff','#075985'),('#475569','#ffffff'),('#854d0e','#fef3c7')];contrast=[]
 for fg,bg in pairs:
  l=sorted([luminance(fg),luminance(bg)]);ratio=(l[1]+.05)/(l[0]+.05);check(ratio>=4.5,'Contrast');contrast.append({'foreground':fg,'background':bg,'ratio':ratio})
 pdf=O/'manuscript_v2.pdf';check(sha256(pdf)==B['pdf_sha256'] and sha256(O/'content_model.json')==B['content_model_sha256'],'Presentation changed since build')
 page_checks=[];all_text=[];title_text=[]
 with pdfplumber.open(pdf) as doc:
  check(len(doc.pages)==len(M['pages'])==22,'Unexpected overflow or missing PDF pages')
  for n,p in enumerate(doc.pages,1):
   txt=p.extract_text() or '';check('INTEGRATED V2' in txt and 'Computational closure complete; archives and human review separate' in txt,'Missing page scope label');check(len(txt)>800,'Empty page')
   check(all(43<=c['x0']<=c['x1']<=569 and 15<=c['top']<c['bottom']<=768 for c in p.chars),'Text outside printable region')
   check('\ufffd' not in txt and '\x00' not in txt,'Broken PDF glyph')
   page_checks.append({'page':n,'characters':len(txt),'header_footer_present':True,'text_within_bounds':True});all_text.append(norm(txt))
   if 'Appendix A.' in txt:title_text.append(norm(p.crop((109,120,534,700)).extract_text() or ''))
 total=' '.join(all_text);titles=' '.join(title_text)
 for p in D['dispositions']['papers']:check(p['id'] in total and norm(p['title']) in titles,'Missing PDF paper title: '+p['id'])
 for md in ['MANUSCRIPT.md','MANUSCRIPT_NO_IMAGES.md']:
  body=(O/md).read_text()
  for target in re.findall(r'\]\(([^)]+)\)',body):
   if not target.startswith(('http://','https://')):check((O/target).is_file(),'Missing Markdown link')
  check(not re.search(r'sk-or-v1-[A-Za-z0-9]{10,}',body),'Secret-like content')
 receipt={'status':'PASS_numeric_content_layout_pending_actual_assistant_visual_review','recorded_at_utc':datetime.now(timezone.utc).isoformat(),'input_files':len(D['bindings']),'paper_links':69,'pdf_pages':22,'canonical_comparison_fields_exact':True,'printed_primary_parameter_legacy_rounding_verified':True,'all208_equity_metrics_exact':True,'all13_asset_rows_exact':True,'equity_display_wealth_rounding_and_bold_winners_verified':True,'all69_full_titles_in_pdf':True,'archived_bibliography_URLs_exact':True,'equity_records':3877,'primary_available':3,'primary_denominator':4,'historical_methods':3,'contrast':contrast,'figures':figures,'page_checks':page_checks,'pdf_sha256':sha256(pdf),'builder_sha256':sha256(R/'scripts/build_fidelity_manuscript_v2.py'),'validator_sha256':sha256(Path(__file__)),'study_jobs_rerun':0,'model_calls':0,'financial_recalculations':0,'ledger_mutations':0,'final_publication_or_archive_readiness':False,'independent_human_review':False}
 atomic_json(O/'draft_validation.json',receipt);print(json.dumps({k:v for k,v in receipt.items() if k not in ['figures','page_checks','contrast']},indent=2))
if __name__=='__main__':main()
