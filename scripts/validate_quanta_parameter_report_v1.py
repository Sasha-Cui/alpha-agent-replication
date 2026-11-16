"""Numerical/link/figure checks for presentation; no financial study rerun."""
from pathlib import Path
import sys,re,json
import numpy as np
import pandas as pd
from PIL import Image
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'src'))
from alpha_evolve.openrouter_budget import sha256,atomic_json
O=R/'paper_runs/fidelity_completion_v2/quanta_parameter_report';A=O.parent/'quanta_paper_parameter_sensitivity'
def contrast(fg,bg):
 def lum(color):
  channels=[int(color[i:i+2],16)/255 for i in [1,3,5]];v=[x/12.92 if x<=.04045 else ((x+.055)/1.055)**2.4 for x in channels];return .2126*v[0]+.7152*v[1]+.0722*v[2]
 a,b=sorted([lum(fg),lum(bg)]);return (b+.05)/(a+.05)
def main():
 build=json.loads((O/'report_build.json').read_text());assert build['builder_sha256']==sha256(R/'scripts/build_quanta_parameter_report_v1.py')
 for name,h in build['inputs'].items():assert sha256(Path(name))==h
 visual=(O/'VISUAL_REPORT.md').read_text();plain=(O/'REPORT.md').read_text();assert '![' not in plain and '```mermaid' not in plain
 headings=['Comparison and inference','Opening-information wealth paths','Fixed comparison contract','Raw values and native preprocessing','Completed evidence and limits','Audit artifacts and reproduction']
 for title in headings:assert '## '+title in visual and '## '+title in plain
 for text in [visual,plain]:
  for link in re.findall(r'\]\(([^)]+)\)',text):assert (O/link).is_file(),link
  assert 'not simultaneous margin bounds' in text and 'not an isolated comparison' in text and 'not independent human source review' in text
  assert '12full-universe proof flags and7membership-filtered library columns have different scopes' in text
 images=re.findall(r'!\[[^\]]*\]\(([^)]+)\)\s*\n\s*(\|)',visual);assert len(images)==2
 figure_receipts=[]
 for name,_ in images:
  with Image.open(O/name) as im:
   a=np.asarray(im.convert('RGB'));assert im.width>=1500 and im.height>=700 and float(a.std())>10
   figure_receipts.append({'path':name,'sha256':sha256(O/name),'width':im.width,'height':im.height,'nonblank':True})
 ratios={color:contrast(color,'#ffffff') for color in ['#172b4d','#475569','#075985','#64748b']};assert min(ratios.values())>=4.5
 canonical=json.loads((A/'comparisons.json').read_text());csv=pd.read_csv(O/'visual_tables/comparisons_full_audit.csv');assert len(csv)==4
 for row in canonical:
  x=csv[(csv.execution==row['execution'])&(csv.baseline==row['baseline'])].iloc[0]
  for field in ['full_sample_annualized_effect','annualized_arithmetic_effect','primary_ci_low','primary_ci_high','group_t_p_two_sided']:assert abs(float(x[field])-row[field])<1e-14
  assert f"{100*row['full_sample_annualized_effect']:+.4f}" in visual and f"{row['group_t_p_two_sided']:.6f}" in visual
 perf=json.loads((A/'performance.json').read_text());csv=pd.read_csv(O/'visual_tables/performance_full_audit.csv');assert len(csv)==8
 for row in perf:
  x=csv[csv.run==row['run']].iloc[0]
  for key in ['ending_wealth','annualized_arithmetic_return','cagr','max_drawdown']:assert abs(float(x[key])-row[key])<1e-14
 raw=json.loads((O/'visual_tables/raw_library_diagnostics.json').read_text());assert raw['raw_library_infinite_cells']==32359 and raw['raw_library_infinite_columns']==7 and raw['raw_library_missing_cells']==1977960 and raw['full_universe_proof_raw_infinity_program_flags']==12
 processing=pd.read_csv(O/'visual_tables/processed_features_full_audit.csv');assert len(processing)==6 and (processing.infinite_values==0).all() and (processing.missing_values==0).all() and set(processing.features)=={146,300}
 contract=json.loads((O/'report_contract.json').read_text());assert contract['sessions']==963 and contract['group_lengths']==[241,241,241,240] and contract['baseline_refits']==0
 outputs={str(p.relative_to(O)):sha256(p) for p in O.rglob('*') if p.is_file() and p.name not in ['report_validation.json','visual_review.json','report_completion.json']}
 atomic_json(O/'report_validation.json',{'status':'numeric_links_image_integrity_and_palette_contrast_pass','figures':figure_receipts,'palette_contrast_vs_white':ratios,'canonical_comparison_rows':4,'performance_rows':8,'processed_feature_rows':6,'no_image_counterpart_pass':True,'figure_table_pairing_pass':True,'new_financial_execution':False,'independent_human_review':False,'assistant_visual_review':'pending separate actual image inspection','outputs':outputs,'validator_sha256':sha256(Path(__file__))})
 print('REPORT_NUMERIC_LINKS_FIGURES_CONTRAST_PASS_ASSISTANT_VISUAL_REVIEW_PENDING',flush=True)
if __name__=='__main__':main()
