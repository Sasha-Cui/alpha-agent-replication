"""Check canonical numbers, disclosure, winner markup, links and explicit figure palette."""
from pathlib import Path
from datetime import datetime,timezone
import json,sys,re,math
import pandas as pd
from PIL import Image,ImageStat
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'src'))
from alpha_evolve.openrouter_budget import sha256,atomic_json
O=R/'paper_runs/fidelity_completion_v2/final_equity_report_v1';A=O.parent/'accounts'
def lum(c):
 rgb=[int(c[x:x+2],16)/255 for x in [1,3,5]];v=[a/12.92 if a<=.04045 else ((a+.055)/1.055)**2.4 for a in rgb];return .2126*v[0]+.7152*v[1]+.0722*v[2]
def main():
 c=json.loads((O/'report_contract.json').read_text());b=json.loads((O/'report_build.json').read_text());assert sha256(R/'scripts/build_final_equity_report_v1.py')==b['builder_sha256']
 for row in c['source_bindings']:assert sha256(R/row['path'] if 'path' in row else R/row['source'])==row['sha256']
 canonical=json.loads((A/'aggregate_performance.json').read_text());pairs=pd.read_csv(O/'visual_tables/aggregate_comparisons.csv');assets=pd.read_csv(O/'visual_tables/asset_comparisons.csv');perf=pd.read_csv(O/'visual_tables/all_208_account_paths_metrics.csv');assert len(pairs)==3 and len(assets)==13 and len(perf)==208
 for x in pairs.to_dict('records'):
  native=next(y for y in canonical if y['case']==x['case'] and y['arm']=='native');base=next(y for y in canonical if y['case']==x['case'] and y['arm']=='buy_hold_matched_clock')
  for field,val in [('native_ending_wealth',native['ending_wealth']),('matched_buy_hold_ending_wealth',base['ending_wealth']),('terminal_wealth_difference',native['ending_wealth']-base['ending_wealth']),('annualized_arithmetic_return_difference',native['annualized_arithmetic_return']-base['annualized_arithmetic_return'])]:assert math.isclose(x[field],val,rel_tol=1e-12,abs_tol=1e-12)
 full=json.loads((A/'performance.json').read_text());recs=perf.to_dict('records')
 for x in full:
  row=next(y for y in recs if all(y[k]==x[k] for k in ['case','symbol','arm','clock','cost_bps']))
  for k,v in x.items():
   if v is None:assert pd.isna(row[k])
   elif isinstance(v,(int,float)):assert math.isclose(row[k],v,rel_tol=1e-12,abs_tol=1e-12)
   else:assert row[k]==v
 visual=(O/'VISUAL_REPORT.md').read_text();plain=(O/'REPORT.md').read_text();assert '![' not in plain
 lines=visual.splitlines();images=[]
 for i,line in enumerate(lines):
  if line.startswith('!['):assert lines[i+1].startswith('| ')
 for target in re.findall(r'\]\(([^)]+)\)',visual):assert (O/target).is_file()
 for line in lines:
  if not any(line.startswith('| '+name+' / ') for name in ['FinMem','TradingAgents','FinAgent']):continue
  cells=[x.strip() for x in line.split('|')][1:-1];values=[float(x.replace('**','')) for x in cells[1:3]]
  for v,cell in zip(values,cells[1:3]):assert cell.startswith('**')==(v>=max(values)-1e-6)
 for phrase in ['higher wealth is better','3,877','4,354','2 pp','independent human review','not significance','259']:
  assert phrase in visual or phrase in json.dumps(c)
 for p in sorted((O/'visual_figures').glob('*.png')):
  with Image.open(p) as im:assert im.width>1000 and im.height>600 and max(ImageStat.Stat(im.convert('RGB')).stddev)>10
  images.append({'path':str(p.relative_to(R)),'sha256':sha256(p)})
 assert len(images)==2
 contrasts={}
 for name in ['ink','blue','orange','grey']:
  a,z=sorted([lum(c['palette'][name]),lum(c['palette']['background'])]);ratio=(z+.05)/(a+.05);assert ratio>=4.5;contrasts[name]=ratio
 result={'status':'pass_numeric_links_images_contrast_and_winner_markup_pending_visual_review','recorded_at_utc':datetime.now(timezone.utc).isoformat(),'aggregate_rows':3,'assets':13,'all_account_metric_rows_exact':208,'higher_wealth_winners_including_ties_bold':True,'figures':images,'contrast_ratios':contrasts,'source_bindings_unchanged':True,'model_calls':0,'source_or_account_engine_reruns':0,'independent_human_review':False,'validator_sha256':sha256(Path(__file__)),'builder_sha256':b['builder_sha256']};atomic_json(O/'report_validation.json',result);print(json.dumps(result,indent=2))
if __name__=='__main__':main()
