"""Compile an explicitly interim manuscript from frozen completed evidence only."""
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter
import sys,json,csv,re,html,shutil
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Image,Table,TableStyle,PageBreak,KeepTogether
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'src'))
from alpha_evolve.openrouter_budget import sha256,atomic_json
U=R/'paper_runs/fidelity_completion_v2';S=R/'artifacts/fidelity_completion_v2/manuscript_v2_setup_20260922';O=U/'manuscript_v2'
INK='#172b4d';BLUE='#075985';GREY='#475569';PALE='#eef4f8';WHITE='#ffffff';GRID='#cbd5e1';AMBER='#854d0e'
CATEGORY=[('missing_artifacts_or_underidentified_native_policy','A','Missing artifacts / underidentified policy'),('source_component_evaluated_full_mechanism_unreplicated','B','Source component; full mechanism unreplicated'),('native_economic_fidelity_extension_or_preserved_v1_case','C','Native extension or preserved v1 case'),('outside_common_monthly_us_jkp_transfer_scope','D','Outside common monthly U.S./JKP transfer'),('recovered_source_observed_history_evaluated_strict_scope_unavailable','E','Observed history; strict scope unavailable')]
def safe(x):
 s=str(x)
 for a,b in [('–','-'),('—','-'),('‑','-'),('−','-'),('’',"'"),('“','"'),('”','"')]:s=s.replace(a,b)
 return s

def prose(value):
 s=safe(value)
 protected=[]
 pattern=r'https?://\S+|[\w./-]*_[\w./-]+|\d{4}-\d{2}-\d{2}T[0-9:.+]+|\d{4}-\d{2}-\d{2}|(?:GPT-\d(?:\.\d)?|DeepSeek-V3|Alpha158|Source4|CSI300|CSI500|JKP132|M\d{3}|v[123]|V[123])'
 def hold(m):
  protected.append(m.group());return chr(0xE000+len(protected)-1)
 s=re.sub(pattern,hold,s)
 s=re.sub(r'([A-Za-z]{2,})(?=\d)',r'\1 ',s)
 s=re.sub(r'(\d)(?=[A-Za-z]{2,})',r'\1 ',s)
 s=re.sub(r'([\uE000-\uEFFF])(?=[A-Za-z0-9])',r'\1 ',s)
 s=re.sub(r'([A-Za-z0-9])(?=[\uE000-\uEFFF])',r'\1 ',s)
 for i,token in enumerate(protected):s=s.replace(chr(0xE000+i),token)
 for a,b in [('FinMemTSLAcohort','FinMem TSLA cohort'),('BUYon','BUY on'),('AppendixA.','Appendix A.'),('AppendixBconflicts','Appendix B conflicts'),('reasoningnone','reasoning none'),('rawp','raw p'),('observed-history sensitivity retains20','observed-history sensitivity retains 20'),('ppmargin','pp margin'),('pwhere','p where'),('%intervals','% intervals'),('pp/year',' pp/year'),('pp for',' pp for'),('bp/year',' bp/year'),('p=1in','p=1 in'),('36x2x134','36 x 2 x 134'),('2pp','2 pp'),('54-family','54-family')]:s=s.replace(a,b)
 s=re.sub(r'(?<=\d)pp\b',' pp',s)
 s=re.sub(r'(?<=\d)bp\b',' bp',s)
 s=re.sub(r',(?!\d)(?=[A-Za-z])',', ',s)
 s=re.sub(r'(?<=\d)(and|with|without)(?=\$|[A-Z])',r' \1 ',s)
 s=re.sub(r'(?<=[A-Za-z%\]])([,;:])(?=\S)',r'\1 ',s)
 s=re.sub(r'(?<=[A-Za-z])(?=\$)',' ',s)
 for a,b in [('OHLCVfields','OHLCV fields'),('signalJan','signal Jan'),('fillJan','fill Jan'),(']pp','] pp'),('] pp_margin',']pp_margin'),('RESERVEDat','RESERVED at'),('U.S./JKPtransfer','U.S./JKP transfer'),('BUY on all 61steps','BUY on all 61 steps'),('inconclusive_at_2 pp_margin','inconclusive at the 2 pp margin'),('99%[','99% ['),('source 4','Source4'),('alpha 158','Alpha158')]:s=s.replace(a,b)
 for a,b in [('manual AMZNgate','manual AMZN gate'),('FinMemCOIN','FinMem COIN'),('JSONnull','JSON null'),('CSVblank','CSV blank'),('returnedQuanta','returned Quanta'),('RESERVEDstatus/fullcharge','RESERVED status and full charge'),('unchangedV 5read-only','unchanged V5 read-only'),('unchanged V5 read-only','unchanged V5 read-only'),('%versus','% versus'),('this draft','this manuscript'),('This draft','This manuscript'),('Completed draft artifacts','Completed manuscript artifacts')]:s=s.replace(a,b)
 # A prose-spacing pass must not turn valid archived URLs into 'https: //'.
 s=re.sub(r'(https?):\s*//',r'\1://',s)
 return re.sub(r' {2,}',' ',s)

def mdtable(headers,rows):
 def cell(x):return safe(x).replace('|','/').replace('\n',' ')
 return '\n'.join(['| '+' | '.join(map(cell,headers))+' |','| '+' | '.join(['---']*len(headers))+' |',*['| '+' | '.join(map(cell,row))+' |' for row in rows]])
def pp(x):return f'{100*float(x):+.3f}'
def ci(r):return '['+pp(r['primary_ci_low'])+', '+pp(r['primary_ci_high'])+']'
def audit_csv(rows,path):
 pd.DataFrame([{k:json.dumps(v,sort_keys=True) if isinstance(v,(dict,list)) else v for k,v in r.items()} for r in rows]).to_csv(path,index=False)
def forest(rows,path,title,subtitle):
 fig,ax=plt.subplots(figsize=(10.4,3.9));fig.subplots_adjust(left=.38,right=.975,bottom=.22,top=.79)
 ax.set_facecolor(WHITE);ax.axvspan(-2,2,color='#e0f2fe');ax.axvline(0,color=GREY,lw=1)
 for i,row in enumerate(rows):
  mean=100*row['annualized_arithmetic_effect'];lo=100*row['primary_ci_low'];hi=100*row['primary_ci_high'];ax.errorbar(mean,i,xerr=[[mean-lo],[hi-mean]],fmt='o',color=BLUE,capsize=4,lw=1.8,markersize=6)
 ax.set_yticks(range(len(rows)),[x['display'] for x in rows]);ax.invert_yaxis();ax.set_xlabel('Annualized within-case increment (pp/year)',color=INK);ax.grid(axis='x',color=GRID,alpha=.65);ax.set_axisbelow(True)
 for name in ['top','right','left']:ax.spines[name].set_visible(False)
 ax.spines['bottom'].set_color(GRID);ax.tick_params(colors=INK)
 fig.suptitle(title,x=.025,ha='left',y=.98,color=INK,fontsize=13,fontweight='bold');fig.text(.025,.88,subtitle,color=GREY,fontsize=9.7)
 fig.savefig(path,dpi=170,facecolor=WHITE);plt.close(fig)
def main():
 if (O/'draft_completion.json').exists():raise ValueError('Preserve completed interim draft; create a new version for revision')
 D=json.loads((S/'inputs.json').read_text());manifest=json.loads((O/'input_manifest.json').read_text());assert sha256(S/'inputs.json')==manifest['private_input_bundle_sha256']
 for row in D['bindings']:assert sha256(R/row['copy'])==row['sha256']
 assert not D['final_equity_accounts_missing'] and D['AMZN_retry_authorized'] and not D['human_review']
 assert D['final_equity']['source_count']==13 and D['progress']['validated_new_records']==3877
 F=O/'figures';T=O/'audit_tables';F.mkdir(exist_ok=True);T.mkdir(exist_ok=True)
 source_by_path={b['path']:R/b['copy'] for b in D['bindings']}
 for name in ['aggregate_wealth','asset_wealth_gaps']:
  src=source_by_path['paper_runs/fidelity_completion_v2/final_equity_report_v1/visual_figures/'+name+'.png'];shutil.copyfile(src,F/(name+'.png'))
 audit_csv(D['aggregate_accounts'],T/'final_equity_aggregate_accounts.csv');audit_csv(D['all_account_performance'],T/'all208_equity_metrics.csv')
 shutil.copyfile(source_by_path['paper_runs/fidelity_completion_v2/final_equity_report_v1/visual_tables/asset_comparisons.csv'],T/'all13_asset_comparisons.csv')
 plt.rcParams.update({'figure.facecolor':WHITE,'axes.facecolor':WHITE,'savefig.facecolor':WHITE,'text.color':INK,'axes.labelcolor':INK,'xtick.color':INK,'ytick.color':INK,'axes.edgecolor':GRID,'font.family':'DejaVu Sans','font.size':10,'legend.facecolor':WHITE,'legend.edgecolor':GRID,'legend.labelcolor':INK})
 categories=[{'code':code,'disposition':key,'label':label,'papers':D['dispositions']['counts'][key]} for key,code,label in CATEGORY]
 fig,ax=plt.subplots(figsize=(10.4,3.5));fig.subplots_adjust(left=.45,right=.94,top=.78,bottom=.18);ax.barh(range(5),[r['papers'] for r in categories],color=BLUE,height=.55);ax.set_yticks(range(5),[r['label'] for r in categories]);ax.invert_yaxis();ax.set_xlim(0,47);ax.set_xlabel('Papers in the preserved disposition category',color=INK)
 for i,r in enumerate(categories):ax.text(r['papers']+.7,i,str(r['papers']),color=INK,va='center')
 for name in ['top','right','left']:ax.spines[name].set_visible(False)
 ax.spines['bottom'].set_color(GRID);ax.tick_params(colors=INK);fig.suptitle('69 separate paper records; no full-paper reproduction established',x=.025,ha='left',y=.97,color=INK,fontsize=13,fontweight='bold');fig.savefig(F/'evidence_scope.png',dpi=170,facecolor=WHITE);plt.close(fig)
 pri=[]
 for r in D['primary_comparisons']:
  if r['case']=='quantaalpha':label='Released Quanta / CSI300 / 963 sessions';kind='252 x mean daily difference';display='Quanta / CSI300 / N=963 days'
  elif r.get('backend')=='gpt41':label='EFS GPT-4.1 / U.S.50 / 72 months';kind='12 x mean compounded-month difference';display='EFS GPT-4.1 / U.S.50 / N=72 months'
  else:label='EFS DeepSeek / U.S.50 / 72 months';kind='12 x mean compounded-month difference';display='EFS DeepSeek / U.S.50 / N=72 months'
  pri.append({**r,'label':label,'estimand':kind,'display':display})
 pri=sorted(pri,key=lambda x:0 if x['case']=='quantaalpha' else 1 if x.get('backend')=='gpt41' else 2)
 assert len(pri)==3 and len(D['primary_family_completion']['expected_cases'])==4
 forest(pri,F/'primary_available.png','Three available v2 primary contrasts; the denominator remains four','Four-group estimates and pointwise 99% intervals. Markets and sampling units differ; this is not a strategy ranking.')
 alpha=next(x for x in D['alpha_comparisons'] if x['execution']=='opening_information')
 qp=[x for x in D['parameter_comparisons'] if x['execution']=='opening_information']
 sensitivities=[{**alpha,'display':'Observed Alpha / CSI500 / N=238 days','label':'Observed Alpha / opening / Alpha158'}]+[{**x,'display':'Quanta parameters / '+x['baseline']+' / N=963 days','label':'Quanta parameters / opening / '+x['baseline']} for x in qp]
 forest(sensitivities,F/'exploratory_effects.png','Exploratory sensitivities do not fill the missing primary contrast','Pointwise 99% intervals and a +/-2 pp margin band; all rows remain outside the original primary family.')
 audit_csv(categories,T/'paper_disposition_counts.csv');audit_csv(D['dispositions']['papers'],T/'all_69_papers_full_audit.csv');audit_csv(D['paper_link_validation'],T/'paper_evidence_links.csv');audit_csv(pri,T/'v2_primary_available.csv');audit_csv(sensitivities,T/'exploratory_opening_comparisons.csv');audit_csv(D['parameter_comparisons'],T/'all_quanta_parameter_comparisons.csv');audit_csv(D['legacy_primaries'],T/'frozen_v1_six_primaries.csv');audit_csv(D['progress']['validated_new_replays'],T/'equity_replay_records.csv');audit_csv(D['historical_method_bindings']['bindings'],T/'historical_method_versions.csv')
 budget_names={'fidelity_v2_finagent_source_settings':('FinAgent',160),'fidelity_v2_finmem_paper_assets':('FinMem',55),'fidelity_v2_tradingagents_source_roles':('TradingAgents original',20),'fidelity_v2_quantaalpha_fresh_search':('Quanta shared variants',75),'fidelity_v2_efs_trials':('EFS',35),'fidelity_v2_alphaagent_source_search':('Alpha shared routes',20),'fidelity_v2_input_summaries':('Input summaries',5),'fidelity_v2_tradingagents_alphabet_news_repair':('TA news repair',5)}
 costs=[{'study_id':k,'label':budget_names[k][0],'committed_usd':v,'cap_usd':budget_names[k][1]} for k,v in D['budget']['study_committed_usd'].items()];audit_csv(costs,T/'committed_budget.csv')
 # The content model drives both Markdown and PDF; canonical studies are never regenerated.
 pages=[]
 def page(title,blocks):pages.append({'title':prose(title),'blocks':blocks})
 def p(text):return {'kind':'p','text':prose(text)}
 def note(text):return {'kind':'note','text':prose(text)}
 def table(headers,rows,widths=None,audit=None):
  display_rows=rows if rows and re.fullmatch(r'M[0-9]{3}',str(rows[0][0])) else [[prose(c) if isinstance(c,str) else c for c in row] for row in rows]
  return {'kind':'table','headers':[prose(c) for c in headers],'rows':display_rows,'widths':widths,'audit':audit}
 def fig(name,caption):return {'kind':'figure','path':'figures/'+name,'caption':prose(caption)}
 primary_rows=[[x['label'],pp(x['full_sample_annualized_effect']),ci(x),f"{x['group_t_p_two_sided']:.4f}",f"{x['project_adjusted_p']:.4f}"] for x in pri]
 exploratory_rows=[[x['label'],str(x['observations']),pp(x['full_sample_annualized_effect']),ci(x),f"{x['group_t_p_two_sided']:.4f}"] for x in sensitivities]
 qheadline=next(x for x in qp if x['baseline']=='alpha158');qsource=next(x for x in qp if x['baseline']=='source4');qs=D['progress']['quanta_secondary_task_result'];am=D['progress']['alpha_observed_materialized_library'];qc=D['quanta_parameter_completion']
 page('Economic fidelity and bounded evidence for LLM investment strategies',[
  note('INTEGRATED MANUSCRIPT V2 - all authorized computational work and final13-equity accounting are complete. Final archive packaging and external human review are separate outstanding steps.'),
  p('This manuscript integrates a preserved 69-paper evidence audit with completed native or explicitly adapted experiments. It separates four questions: whether source mechanisms can be executed, whether the observed histories and financial accounts can be reproduced, whether an incremental return is identified under matched conditions, and whether the original paper has been reproduced. The current evidence supports many computational and accounting checks, but establishes zero full-original-paper replications.'),
  p(f"The available v2 primary family contains three of four prespecified contrasts: released-default Quanta and two EFS pools. Their pointwise 99% intervals remain wide and all adjusted positive-increment flags are false; strict Alpha remains unavailable. Separately, the all20 observed-history Alpha sensitivity has a full-sample opening increment of {pp(alpha['full_sample_annualized_effect'])} pp/year, while the Quanta parameter sensitivity over Alpha158 is {pp(qheadline['full_sample_annualized_effect'])} pp/year. Both remain inconclusive at the 2 pp annual margin and neither replaces a missing primary."),
  p('The expanded equity work has3,877newly validated replay records. All13main equity sources and full replays passed, and final accounts independently reconcile within5.6e-16. At10bp next-close execution, FinMem and TradingAgents finish above their own matched buy-and-hold controls, while FinAgent finishes below. These are descriptive within-study results with different dates, not a cross-study ranking or significance result. One sealed prospective observation was settled without a new model call; a single outcome provides no significance evidence.'),
  table(['Evidence layer','Current status'],[['69-paper register','Separate titles, dispositions and gap references retained'],['Completed factor case studies','EFS, released Quanta, observed Alpha and Quanta parameters preserved'],['Expanded equity accounts','All13 final source/replay/admission/account gates pass'],['Independent human review','External and not asserted'],['Publication packages','Final immutable bundles and durable second copies not complete']],[150,374]),
  p('All figures and tables are presentations of existing completed artifacts. The earlier20-page interim draft is preserved unchanged. No source, factor, model, account, replay or financial analysis job was rerun to assemble the manuscript.')])
 page('1. Evidence coverage is not a reproduction count',[
  fig('evidence_scope.png','Figure 1. Preserved review dispositions, not counts of successful strategies.'),
  table(['Code','Disposition','Papers'],[[r['code'],r['label'],r['papers']] for r in categories],[40,434,50],'paper_disposition_counts.csv'),
  p('All 69 identifiers and full titles appear in Appendix A and the full audit CSV. Each retains a separate gap description and a verified metadata link. A source-component result or common-transfer surrogate is not relabelled as a complete native mechanism. A missing artifact is not evidence that recovery is impossible forever; it is a bounded statement about the preserved audit.'),
  p('Seven papers are outside the common monthly U.S./JKP transfer scope because their native task does not map without replacing its mechanism. This does not establish failure in their intended market or task. The six native-extension/preserved-v1 records and the separate observed-history record likewise do not establish full-paper reproduction.'),
  p('The paper register itself is unchanged by this manuscript. No new author contact, upstream availability search or human attestation is represented by the drafting pass.')])
 page('2. Design, data boundaries and execution clocks',[
  p('The design preserves all declared source attempts, failed histories, exact responses and source-used programs. It restores recoverable mechanisms and settings before evaluating an economic contrast. Historical model snapshots, alternative-data vintages and some paper run designs remain unavailable, so current-model or adapted executions are identified as such. No best-return trajectory is promoted into a primary family.'),
  table(['Component','Formation/source boundary','Evaluation / interpretation'],[['Alpha observed history','Five OHLCV fields physically bounded through2025-01-02; first100source-ordered debug subset through2024-12-30','First signalJan3/fillJan6,2025;238later sessions, CSI500'],['Quanta searches','Six fields through2022-01-05; original100-stock2018-19debug; paper source train2016-19/valid2020/feedback2021','First signalJan6/fillJan7,2022;963later sessions, CSI300'],['EFS pools','Frozen paper-guided U.S.50 implementation; author implementation not recovered','1,510daily observations compounded into72months'],['Equity agents','Preserved dated inputs and exact native histories; one trajectory per asset','Final13accounts complete; study windows differ, one trajectory per asset']],[95,225,204]),
  p('Evaluation HDFs were not supplied to generation. Full-universe program proofs remove actual future rows at fixed historical cutoffs; a debug-only truncation is insufficient. These tests check dependence of the saved programs on future rows, not historical model contamination or every possible form of leakage.'),
  p('Native Qlib opening eligibility uses same-day closing-change and missingness information. The declared opening-information proxy instead requires finite positive current open and prior close with the same9.5% threshold, while preserving saved predictions, labels, fees, lots and dates. The2019 audit found433buy and181sell discrepancies on72,964stock-days. Board-specific limits, auction/liquidity mechanics and adjustment-vintage fidelity remain gaps.'),
  p('The word symbol in Quanta symbol-length limits concerns expression complexity, not the stock-universe size. Every return comparison retains its own market, sample and recorded economic settings; pooled rankings across these cases would not be identified by this design.')])
 page('3. Available v2 primary evidence',[
  fig('primary_available.png','Figure 2. Available contrasts in their own markets and sampling units. The missing strict Alpha row is not replaced.'),
  table(['Within-case contrast','Full mean pp/y','99% group interval','Raw p','4p upper'],primary_rows,[220,64,115,60,65],'v2_primary_available.csv'),
  note('THREE OF FOUR PRIMARY CONTRASTS AVAILABLE. The strict Alpha comparison is absent; the multiplicity denominator stays four. Do not apply Holm to only the three available cases.'),
  p('For released Quanta, the opening Alpha158 full-sample mean increment is+2.095706pp/year, with grouped99% interval[-4.021037,+8.217106]pp. Its local two-case conservative p bound is0.277934, but the project four-case bound is0.555869. The EFS four-case bounds are1.0. All positive family flags remain false and all three available comparisons are inconclusive at the2ppmargin.'),
  p('EFS increments use12times the mean difference of compounded monthly returns. Quanta uses252times the mean daily net-return difference. The plotted points are equal-weight group means; the table uses the full-sample mean and labels the group interval separately. The rows are not interchangeable estimates of a common strategy population.')])
 page('4. EFS: matched pools and limits on attribution',[
  p('All EFS sources, replays, matched grammar and both LLM pools, paired analysis and the partial primary-family collector are complete. Three trajectories are retained in each pool; the matched grammar uses fixed seeds101/102/103. The comparison is a frozen paper-guided U.S.50 implementation. Attributable author implementation was not recovered, so neither author-code equivalence nor full-paper reproduction is claimed.'),
  table(['Pool','Trajectories','Recorded functions','Primary contrast'],[['Matched grammar',3,1104,'Common reference'],['GPT-4.1',3,1820,'+4.128067pp/y;99%[-17.461784,+25.717918]'],['DeepSeek-V3',3,2198,'+2.728569pp/y;99%[-58.209449,+63.666587]']],[115,76,99,234]),
  p('Twenty-four cost/mode paths cover1,510days and72months. Independent re-accounting has maximum difference9.35e-16. The10bp path remains primary. At zero cost, the descriptive increments are approximately+1.504pp/year for GPT and-0.221pp for DeepSeek. Relative gaps increase as fees rise while each pool\'s absolute wealth falls; that pattern is not evidence that fees create alpha.'),
  p('Unrestricted134-parameter JKP regression is refused on72monthly observations. The six-factor and expanding36-month ridge10/PCA5 contemporaneous reconstructions are diagnostics, not forecasts or unrestricted-alpha tests. A common JKP-only allocator baseline is verified; the36x2x134weight diagnostics have certainty-equivalent changes of-3.364bp/year for GPT and-6.864bp for DeepSeek, with zero change for grammar.'),
  p('Missing factor turnover, financing and allocation costs preclude net-fund or efficient-frontier claims. The monthly N=72calibration has some subnominal cells across2,000replications and18settings. Daily N=238or963calibration cannot be borrowed to certify monthly coverage.'),
  p('Evidence: efs_economic_completion.json and efs_pooled_analysis/completion.json. Their completed rows are preserved, including historical local status labels; the current collector, not a rewrite of those rows, records the available3/4project family.')])
 page('5. Quanta: released search and parameter sensitivity',[
  p(f"Released-default Quanta preserves source/full replay, seven source tasks, sixteen consumed-program proofs, pooled native/opening accounts and all seven task libraries. Under opening eligibility, {qs['negative_full_sample_mean_tasks']}/7task Alpha158 increments are negative; their median is {100*qs['median_full_sample_annualized_increment']:+.6f}pp/year. All14opening secondary comparisons have conservative54-family p bounds of1.0. No selected task replaces the pooled comparison."),
  p('The separate parameter sensitivity changes the active symbol-length threshold300to250, duplication8to5, enables consistency checks and requests three factors, with ten directions/ten crossovers and five total phases under AppendixA.4; AppendixBconflicts. The old factor YAML was inactive. Current GPT-5.2/OpenAI,max3000,reasoningnone and recorded ordinal seeds are not historical-model equivalence. Several settings and histories differ jointly, so this is not an isolated parameter effect.'),
  table(['Execution / baseline','Full mean pp/y','99% group interval','Raw p'],[[('Opening' if x['execution']=='opening_information' else 'Native')+' / '+x['baseline'],pp(x['full_sample_annualized_effect']),ci(x),f"{x['group_t_p_two_sided']:.4f}"] for x in D['parameter_comparisons']],[160,86,182,96],'all_quanta_parameter_comparisons.csv'),
  p(f"All142source-used hashes become142expression columns in an801,001-row fixed library. Four native/opening accounts pass963sessions each. Two augmented fits and two saved-prediction opening replays reuse four common baseline paths without refitting. The opening Alpha158 increment is{pp(qheadline['full_sample_annualized_effect'])}pp/year; all four comparisons remain inconclusive at2pp. Opening terminal wealth is1.28390444versus1.11534581for Alpha158, and1.16705330versus1.01359912for Source4."),
  p('Both the complete original and interrupted partial histories, separate LOOP/POOL identities, current inputs and all saved source-period backtests are preserved. The source contains3,644chat,589embedding and680quality records; these are workflow counts, not independent successes. Source reconstruction uses seeded control flow, not a comparison with unavailable original RAM. All source, proof and economic jobs are complete and are not rerun by this draft.')])
 page('6. Observed Alpha history: useful evidence with a strict-scope failure',[
  fig('exploratory_effects.png','Figure 3. Supplemental opening comparisons. None is a substitute for the unavailable strict Alpha primary.'),
  table(['Exploratory comparison','N days','Full mean pp/y','99% group interval','Raw p'],exploratory_rows,[190,48,75,141,70],'exploratory_opening_comparisons.csv'),
  p('The all20observed-history sensitivity retains20outcomes,96actual attempts,4unattempted rounds and86histories. Trials12/14ended after three attempts; trials08/15failed on their final fifth attempt. No missing round, replacement response, successful-trial subset or retry is imputed. Final-round recognition requires five actual attempts; an early abort does not qualify.'),
  p('The strict20-by5source gate therefore remains unmet, its pooled primary stays held, and its original downstream four-primary/54-secondary families remain unavailable. The separate observed library has159uses,157program hashes and146expression columns; eleven exact-expression duplicates are numerically identical. The exploratory opening full-sample increment is-13.557404pp/year, with99% group interval[-46.893161,+19.782131]pp and rawp0.098061. This is inconclusive, not a significant-loss or LLM-specific claim.')])
 page('7. Raw values and processed model inputs',[
  p('Preserving the executed inputs includes preserving nonfinite raw values and missingness. Finite processed inputs do not justify deleting raw infinity flags, changing a program or describing the source as uniformly finite. The following populations refer to distinct matrices and cannot be added.'),
  table(['Library','Raw matrix','Raw infinity','Raw missing','Distinct scope'],[['Observed Alpha',f"{am['matrix_rows']:,} x {am['matrix_columns']}",f"{am['raw_infinite_cells_in_unique_matrix']}cells /2programs",f"{am['matrix_nan_cells']:,}",'Observed-history fixed library'],['Quanta parameters',f"{qc['matrix_rows']:,} x {qc['distinct_expressions']}",f"{qc['raw_library_infinite_cells']:,}cells /{qc['raw_library_infinite_columns']}columns",f"{qc['raw_library_missing_cells']:,}",'CSI300 membership-filtered fixed matrix']],[97,113,112,91,111]),
  p('Quanta has12whole-universe proof program flags but only7infinite columns in the membership-filtered library. These are different universes and overlapping check scopes, not a contradiction and not a summed count of unique cells. All142programs remain present. Full-panel/four-cutoff checks compare actual future-row truncations and the exact native feature matrices.'),
  table(['Processed inputs','Features','Infinity','Other retained diagnostics'],[['Observed Alpha baseline / augmented','158 /304','0','Two constant-or-missing columns per segment; train/valid/test missing cells2,206,039/372,206/394,459'],['Quanta Source4 / Alpha158 augmented','146 /300','0','No missing or constant/missing columns in train/valid/test; rows282,088/72,754/289,011']],[130,75,60,259]),
  p('The Quanta proof checker originally rejected preserved original model matrices for being outside the continuation folder, despite all50hashes matching. The corrected version permits only exact source-admitted original/new workspace/path/hash/column bindings before factor execution. It preserves all numerical and real future-row-removal checks. Failed attempts and the previous checker remain archived; completed proofs were reused rather than repeated.'),
  p('No library/program/record counts are added to the equity replay headline. An exact replay or a causal-prefix diagnostic establishes a narrow computational property, not economic value, pristine historical model inputs or full-paper fidelity.')])
 page('8. Expanded equities: exact histories and completed accounts',[
  p('The newly validated replay-record headline is3,877: 1,648from four FinMem additions,183from three original TradingAgents assets,61from the separate Alphabet-news repair, and1,985from all five FinAgent continuations. These are workflow records, not independent observations or repeated paper trials. The main13-source population is4,354: it includes the original538-record FinMem TSLA source and excludes the separate61-record news sensitivity.'),
  table(['Source cohort','New exact records','Recorded scope'],[['FinMem additions',1648,'Four412-record replays;259training and1test Guard failures retained'],['TradingAgents original assets',183,'AAPL/AMZN/GOOGL,61each; one trajectory per asset'],['Separate TA news repair',61,'Outside the final13main-cohort aggregate'],['FinAgent all five assets',1985,'Five397-record sources/full replays;250training+147native_causal each']],[164,88,272],'equity_replay_records.csv'),
  p('AMZN originally stopped on an embedding HTTP500 after220training records. One explicit user-approved exact retry succeeded; the original0.00012324USD charge remains retained and the returned retry cost0.00002132USD. All220HTTP500,49NFS and134transport prefixes matched before the first new source request. These overlapping histories are not added together. Source27062473 and full replay27062474 then completed397records with zero differences.'),
  p('Final accounting job27116634 completed with all13checks passing and maximum independent accounting error5.551115123125783e-16. The exact manual AMZN gate and all13currentV3source admissions ran before submission and again at runtime. The unchangedV3builder used no partial fallback or overwrite. Original failed/cancelled jobs, every completed history and all financial expressions remain preserved.'),
  p('GOOGL retains every inner response character under its single four-tag markup alias; TSLA retains the literal long_term_reasonig alias. Seven returned embedding responses were reconciled while fully charging their original reservations; provider usage is recorded separately, not equated with billing.'),
  note('Completed computational and accounting checks do not establish an isolated LLM effect, full-paper reproduction, significance, pristine historical snapshots or independent human review.')])
 eq_lookup={(x['case'],x['arm']):x for x in D['aggregate_accounts']}
 labels={'finmem':'FinMem','tradingagents':'TradingAgents','finagent':'FinAgent'}
 eq_rows=[]
 for case in ['finmem','tradingagents','finagent']:
  a,b=eq_lookup[(case,'native')],eq_lookup[(case,'buy_hold_matched_clock')];x,y=a['ending_wealth'],b['ending_wealth'];sx,sy=f'{x:.6f}',f'{y:.6f}'
  if x>=y:sx='**'+sx+'**'
  if y>=x:sy='**'+sy+'**'
  eq_rows.append([labels[case],a['observations'],a['start'][:10]+' to '+a['end'][:10],sx,sy])
 page('8a. Aggregate wealth within each study window',[
  fig('aggregate_wealth.png','Figure 4. Equal initial capital in independent accounts; no daily cross-account rebalancing. Common wealth scale, separate dates.'),
  table(['Study','Sessions','Valuation window','Native wealth','Control wealth'],eq_rows,[78,54,172,110,110],'final_equity_aggregate_accounts.csv'),
  p('Wealth is per initial$1under10bp next-close execution. Higher terminal wealth is better within each row; every within-row maximum including ties is bold. Matched controls use the same study dates and execution clock. These are descriptive account paths, not repeated-trial estimates or new significance tests. Different windows prevent cross-study ranking.'),
  p('FinMem has higher terminal wealth than its control but a lower annualized arithmetic mean return:23.162838%versus26.582062%. Both metrics remain exactly as saved; path-dependent compounding and volatility can change their ordering. The252-session geometric annualization fields are not calendar-year CAGR.'),
  p('The full audit retains208arm/clock/fee metric rows across13assets, two arms, two clocks and four fee levels. Eight FinMemCOIN zero-volatility native paths have undefined Sharpe; JSONnull and CSVblank are preserved. They are not silently replaced by zero.'),
  note('The expanded-equity descriptive accounts do not enter the original v2four-case or54-secondary families and do not replace any frozen v1primary contrast.')])
 assets=list(csv.DictReader((T/'all13_asset_comparisons.csv').open()))
 # Counts are descriptive path directions, never binomial evidence of independent trials.
 direction_rows=[]
 for case in ['finmem','tradingagents','finagent']:
  rows=[a for a in assets if a['case']==case];gaps=[float(a['native_ending_wealth'])-float(a['matched_buy_hold_ending_wealth']) for a in rows]
  direction_rows.append([labels[case],sum(x>1e-12 for x in gaps),sum(abs(x)<=1e-12 for x in gaps),sum(x< -1e-12 for x in gaps)])
 page('8b. Every asset-level outcome remains visible',[
  fig('asset_wealth_gaps.png','Figure 5. All13within-asset wealth gaps, retained in study/source order. Positive values favor the native path; no performance sorting.'),
  table(['Study','Native above','Numerical tie','Native below'],direction_rows,[172,117,117,118],'all13_asset_comparisons.csv'),
  p('Direction counts summarize the fixed10bp next-close paths; they are not independent Bernoulli trials or a significance test. Assets share one market history, and different study windows remain separate. Full native/control terminal values for every asset are retained in the linked audit CSV.'),
  p('For the separate TradingAgents Alphabet-news repair, the corpus expanded from88to10,117items while373prices stayed unchanged. All61reports changed, but both policies chose BUYon all61steps and all eight clock/fee paths match. This gives no additional realized return in that trajectory, not a general news-never-helps conclusion. The failed duplicated-feed variant is preserved separately.')])
 page('9. Inference, multiplicity and what remains unidentified',[
  p('The economic margin is2percentage points/year. Four contiguous-group estimates provide t-based pointwise99%intervals under stated approximate group-independence and normality assumptions. Full-sample and equal-weight group means differ when block lengths differ. A point estimate above the margin is not evidence that the margin is exceeded; a nonsignificant p-value is not evidence of zero alpha or equivalence.'),
  table(['Family','Membership rule','Current treatment'],[['Frozen v1six','Six recorded historical primary contrasts','Complete original family; all six inconclusive'],['Native local two','Released Quanta and strict Alpha','Quanta available; conservative2pwhere partial'],['Current v2four','Strict Alpha, released Quanta, two EFS contrasts','Three available; denominator4,conservative4p; no Holm3'],['Secondary54','Seven Quanta tasks plus strict Alpha trial panel','Quanta case complete; missing Alpha does not reduce denominator'],['Observed Alpha / Quanta parameters','Separately declared exploratory sensitivities','Raw descriptive p-values; no primary-family substitution']],[100,213,211]),
  p('The intervals are not simultaneous bounds on the economic margin. Degenerate sampling variation receives p=1in the guarded inference path. Tasks and assets share market histories; source records, generated factors and model fits do not create independent financial replications. Model-seed and historical-model/data uncertainty are not estimated by a conditional return-path interval.'),
  p('The original short-sample bootstrap undercoverage remains a diagnostic, not a reason to select a better-looking inference method after viewing the returns. Calibration is tied to its sample length and simulated processes. Monthly72-observation EFS coverage cannot be certified by native238/963-session calibration.'),
  p('The original sealed prospective forecast was settled without a new model call or altered commitment. Its single outcome is retained in the evidence chain. One observation cannot establish significance or prospective investment value; the historical analysis is not converted into an untouched holdout claim.')])
 page('10. Frozen v1 results remain a separate historical layer',[
  p('The completed six-case study is retained as originally recorded. Its controls, sample windows and adapters are not relabelled as the newer experiments, and the new sensitivities do not replace its rows. Direct between-version performance differences are not isolated causal effects because mechanisms, inputs or comparison scope can differ.'),
  table(['Case','N / annualizer','Full mean pp/y','Pointwise99% interval','Holm6 p'],[[x['case'],x['observations']+' / '+x['frequency'],pp(x['full_sample_annualized_effect']),ci(x),f"{float(x['holm_p_primary_family']):.4f}"] for x in D['legacy_primaries']],[94,81,87,181,81],'frozen_v1_six_primaries.csv'),
  p('All six recorded verdicts are inconclusive_at_2pp_margin. The monthly EFS/GuruAgents/Quanta rows and daily equity rows retain their own annualization and sample lengths. Their very different interval widths must not be hidden by calling all rows an interchangeable benchmark.'),
  p('The frozen v1analysis status still contains its then-current prospective label. This draft cites the subsequently settled outcome record separately rather than rewriting that historical status. Its source commitments, EFS semantic seals and earlier report/manuscript remain untouched.'),
  p('Likewise, three method references in the completed released-Quanta secondary analysis point to earlier helper versions. Exact copies matching all three recorded hashes were recovered from the September17methods snapshot. This draft binds those executed versions; current helper files and completed economic results were not changed and the analysis was not rerun.')])
 page('11. Cost exposure, integrity and release conditions',[
  p(f"The locked project commitment at{D['budget']['recorded_at_utc']}is${D['budget']['project_committed_usd']:.8f}, including historical spending and uncertain reservations. The current user authorization is strictly below$1,000in total. Completed live jobs retained their lower$450project and$160FinAgent runtime caps. The following are shared study commitments, not necessarily incremental costs of the displayed sensitivity."),
  table(['Shared study','Committed USD','Cap USD'],[[x['label'],f"{x['committed_usd']:.8f}",x['cap_usd']] for x in costs],[255,159,110],'committed_budget.csv'),
  p('The four witnessed Alpha missing-response reservations total$0.116085and remain charged. The original Quanta returned-response reservation remains exactly RESERVEDat$0.0556885; its journal body is preserved and its full charge retained. AMZN retains its original$0.00012324missing-response charge after the single user-approved retry, which separately cost$0.00002132. The recovery changes no other request. These amounts are already included in commitments; they are not added again, refunded or classified as failures merely by age.'),
  p('The unchanged V5 read-only request preflight passed actual final13equity and Quanta closure gates plus fresh ledger/journal locks and a complete journal/SQLite check. It found zero unclassified reservations. Only an in-memory projection classifies the exact returnedQuanta reservation; its original RESERVEDstatus/fullcharge are unchanged. A final packager must repeat current source/account/request checks inside its own consistent snapshot transaction and separately verify public/private content, privacy and durable second copies.'),
  note('This integrated manuscript is not an archive certificate. Immutable public/private bundles and independent durable-copy verification remain open; independent human source review is external. No completed source/replay/model/account/analysis needs a rerun. No additional AMZN retry is authorized.')])
 page('12. Conclusions and reproducibility contract',[
  p('The strongest supported conclusion is conditional and bounded: the completed studies provide auditable source histories, replay checks, native accounting and explicitly labelled economic comparisons. They do not establish a universal absence of alpha, full reconstruction of every paper, an isolated LLM-specific advantage or a pristine historical experiment.'),
  p('The current primary-family evidence remains incomplete and inconclusive. The separate observed-history and parameter sensitivities are complete within their declared scopes, with failures, unattempted rounds, raw nonfinite values and input adaptations retained. Their completion is a computational achievement, not permission to replace a missing strict primary.'),
  p(f"This manuscript is assembled without rerunning completed studies. Its{len(D['bindings'])}input files and69paper metadata links are hash-verified; historical method versions are resolved to exact archived bytes when a completed receipt points to an older helper. The source register, all canonical results and the old v1manuscript are unchanged. Full audit tables retain exact figures, identifiers, source links, scope fields and unabridged gap metadata."),
  table(['Artifact','Role'],[['input_manifest.json','Source paths/hashes; private immutable input-copy reference'],['audit_tables/all_69_papers_full_audit.csv','Every title, disposition, original status and full gap metadata'],['audit_tables/v2_primary_available.csv','Three available rows; denominator remains four'],['audit_tables/exploratory_opening_comparisons.csv','Observed Alpha and Quanta parameter opening sensitivities'],['audit_tables/historical_method_versions.csv','Recorded source hash versus exact archived executed copy'],['manuscript_v2.pdf / MANUSCRIPT.md','Integrated v2PDF and text generated from the same content model']],[235,289]),
  p('Reproduce this presentation from the verified input bundle using scripts/build_fidelity_manuscript_v2.py and scripts/validate_fidelity_manuscript_v2.py under the immutable central kt-python runtime. These builders do not submit Slurm jobs, call a model, re-account a portfolio or run a source/proof. Completed draft artifacts are preserved; a later manuscript revision receives a new version.'),
  p('Human review and final release checks are not simulated by machine or assistant QA. Before a stronger claim is written, its missing inputs, scope restrictions and actual economic evidence must be resolved explicitly rather than hidden by a more fluent summary.')])
 # Bibliography metadata is inherited from the frozen v1source; it is not an upstream literature re-search.
 refs=[]
 for key,title,url in D['references']:refs.append(p('['+key+'] '+title+' '+url))
 page('Selected archived references',refs+[p('References identify source papers and inference methods used by the preserved study. Versioned source audits and the complete69-paper index carry the implementation and availability evidence. A citation does not establish that an original historical model, dataset or full author pipeline was reproduced.')])
 bycat={key:code for key,code,_ in CATEGORY};papers=sorted(D['dispositions']['papers'],key=lambda x:x['id'])
 for start in range(0,69,12):
  chunk=papers[start:start+12]
  page('Appendix A. Complete paper index ('+str(start+1)+'-'+str(start+len(chunk))+' of69)',[
   p('Disposition codes: A=missing artifacts/underidentified policy; B=source component, full mechanism unreplicated; C=native extension/preservedv1case; D=outside common monthly U.S./JKPtransfer; E=observed history with strict scope unavailable. Every row retains its own complete gap record in the audit CSV.'),
   table(['Paper ID','Full title','Code'],[[r['id'],r['title'],bycat[r['review_disposition']]] for r in chunk],[60,424,40],'all_69_papers_full_audit.csv'),
   p('No row is labelled full-original-paper reproduced. This index preserves the original69dispositions; it does not turn missing artifacts or scope incompatibility into negative evidence about the paper\'s native task.')])
 atomic_json(O/'content_model.json',{'status':'integrated_v2_all13_accounts_complete_archive_human_review_separate','pages':pages,'source_input_sha256':sha256(S/'inputs.json'),'new_study_execution':False})
 sections=['# '+pages[0]['title'],'','**INTEGRATED MANUSCRIPT V2 - computational work complete; archives and external human review separate.**']
 for pi,section in enumerate(pages):
  sections += ['','## '+section['title']]
  for block in section['blocks']:
   if block['kind'] in ['p','note']:sections += ['',('**'+block['text']+'**') if block['kind']=='note' else block['text']]
   elif block['kind']=='figure':sections += ['',f"![{block['caption']}]({block['path']})",'',block['caption']]
   else:
    sections += ['',mdtable(block['headers'],block['rows'])]
    if block.get('audit'):sections += ['',f"[Full audit CSV](audit_tables/{block['audit']})"]
 (O/'MANUSCRIPT.md').write_text('\n'.join(sections)+'\n')
 (O/'MANUSCRIPT_NO_IMAGES.md').write_text('\n'.join(x for x in sections if not x.startswith('!['))+'\n')
 # Explicit styles prevent inherited light-on-light text in every PDF text/table element.
 regular=font_manager.findfont('DejaVu Sans');bold=font_manager.findfont(font_manager.FontProperties(family='DejaVu Sans',weight='bold'));italic=font_manager.findfont(font_manager.FontProperties(family='DejaVu Sans',style='oblique'))
 for name,path in [('DraftSans',regular),('DraftBold',bold),('DraftItalic',italic)]:pdfmetrics.registerFont(TTFont(name,path))
 pdfmetrics.registerFontFamily('DraftSans',normal='DraftSans',bold='DraftBold',italic='DraftItalic',boldItalic='DraftBold')
 styles={'body':ParagraphStyle('Body',fontName='DraftSans',fontSize=9.2,leading=13.1,textColor=colors.HexColor(INK),spaceAfter=8), 'heading':ParagraphStyle('Heading',fontName='DraftBold',fontSize=17,leading=21,textColor=colors.HexColor(BLUE),spaceAfter=13), 'title':ParagraphStyle('Title',fontName='DraftBold',fontSize=23,leading=28,textColor=colors.HexColor(BLUE),spaceAfter=16), 'cell':ParagraphStyle('Cell',fontName='DraftSans',fontSize=8.1,leading=10.7,textColor=colors.HexColor(INK)), 'thead':ParagraphStyle('THead',fontName='DraftBold',fontSize=8.2,leading=10.8,textColor=colors.HexColor(WHITE)), 'caption':ParagraphStyle('Caption',fontName='DraftSans',fontSize=8.1,leading=11,textColor=colors.HexColor(GREY),spaceAfter=8), 'note':ParagraphStyle('Note',fontName='DraftBold',fontSize=9.2,leading=13,textColor=colors.HexColor(AMBER),backColor=colors.HexColor('#fef3c7'),borderPadding=7,spaceBefore=3,spaceAfter=11)}
 def para(text,style='body'):
  content=html.escape(safe(text));content=re.sub(r'\*\*(.*?)\*\*',r'<b>\1</b>',content)
  return Paragraph(content,styles[style])
 story=[]
 for page_index,section in enumerate(pages):
  if page_index:story.append(PageBreak())
  story.append(para(section['title'],'title' if page_index==0 else 'heading'))
  for block in section['blocks']:
   if block['kind'] in ['p','note']:story.append(para(block['text'],'note' if block['kind']=='note' else 'body'))
   elif block['kind']=='figure':
    img=Image(str(O/block['path']));ratio=img.imageHeight/img.imageWidth;img.drawWidth=524;img.drawHeight=524*ratio;story += [img,Spacer(1,5),para(block['caption'],'caption')]
   else:
    cells=[[para(h,'thead') for h in block['headers']]]+[[para(c,'cell') for c in row] for row in block['rows']]
    widths=block.get('widths') or [524/len(block['headers'])]*len(block['headers']);tbl=Table(cells,colWidths=widths,repeatRows=1,hAlign='LEFT');tbl.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor(BLUE)),('TEXTCOLOR',(0,0),(-1,0),colors.HexColor(WHITE)),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.HexColor(WHITE),colors.HexColor(PALE)]),('TEXTCOLOR',(0,1),(-1,-1),colors.HexColor(INK)),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),('LINEBELOW',(0,0),(-1,0),.5,colors.HexColor(GRID)),('LINEBELOW',(0,-1),(-1,-1),.3,colors.HexColor(GRID))]));story += [tbl,Spacer(1,7)]
    if block.get('audit'):story.append(para('Audit: '+block['audit'],'caption'))
 def decorate(canvas,doc):
  canvas.saveState();canvas.setFillColor(colors.HexColor(WHITE));canvas.rect(0,0,612,792,fill=1,stroke=0);canvas.setFillColor(colors.HexColor(GREY));canvas.setFont('DraftSans',7.6);canvas.drawString(44,768,'ECONOMIC FIDELITY | INTEGRATED V2 | '+D['recorded_at_utc'][:10]);canvas.setStrokeColor(colors.HexColor(GRID));canvas.line(44,42,568,42);canvas.setFillColor(colors.HexColor(GREY));canvas.drawString(44,29,'Computational closure complete; archives and human review separate');canvas.drawRightString(568,29,'Page '+str(doc.page));canvas.restoreState()
 pdf=O/'manuscript_v2.pdf';doc=SimpleDocTemplate(str(pdf),pagesize=(612,792),leftMargin=44,rightMargin=44,topMargin=49,bottomMargin=55,title='Economic fidelity - integrated manuscript v2',author='Research evidence compilation');doc.build(story,onFirstPage=decorate,onLaterPages=decorate)
 atomic_json(O/'draft_contract.json',{'status':'integrated_v2_computational_closure_not_archive_certificate','paper_count':69,'new_full_paper_reproductions':0,'legacy_primary_count':6,'v2_primary_available':3,'v2_primary_denominator':4,'new_equity_replay_records':3877,'final13_equity_accounts_missing':False,'AMZN_retry_authorized':True,'source_case_economics_preserved':True,'independent_human_review':False,'archive_created':False,'new_source_model_account_analysis_execution':False,'historical_method_versions_resolved':3,'budget_snapshot':D['budget'],'primary_margin':.02,'pointwise_confidence':.99,'primary_plot_uses_group_mean_table_uses_full_mean':True})
 atomic_json(O/'draft_build.json',{'status':'built_pending_numeric_and_visual_QA','recorded_at_utc':datetime.now(timezone.utc).isoformat(),'builder_sha256':sha256(Path(__file__)),'input_bundle_sha256':sha256(S/'inputs.json'),'pdf_sha256':sha256(pdf),'content_model_sha256':sha256(O/'content_model.json'),'source_files_unchanged':True,'study_jobs_rerun':0,'PDF_operation_marker_not_repeated_per_user_instruction':True})
 print('INTEGRATED_V2_MANUSCRIPT_BUILT_NO_STUDY_EXECUTION',str(pdf),flush=True)
if __name__=='__main__':main()
