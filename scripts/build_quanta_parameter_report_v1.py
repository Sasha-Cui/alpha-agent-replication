"""Present completed Quanta parameter economics; never execute a study or model."""
from pathlib import Path
import sys,json,re
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.lines import Line2D
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'src'))
from alpha_evolve.openrouter_budget import sha256,atomic_json
U=R/'paper_runs/fidelity_completion_v2';P=R/'artifacts/fidelity_completion_v2';A=U/'quanta_paper_parameter_sensitivity';O=U/'quanta_parameter_report'
TEXT='#172b4d';MUTED='#475569';BLUE='#075985';GREY='#64748b';WHITE='#ffffff';GRID='#cbd5e1'

def table(headers,rows):
 return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |',*['| '+' | '.join(map(str,row))+' |' for row in rows]])

def main():
 if (O/'report_completion.json').exists():raise ValueError('Preserve completed report; use a new version for changes')
 O.mkdir(exist_ok=True);F=O/'visual_figures';T=O/'visual_tables';F.mkdir(exist_ok=True);T.mkdir(exist_ok=True)
 done=json.loads((A/'completion.json').read_text());assert done['status']=='separate_exploratory_parameter_sensitivity_complete_not_primary'
 for name,h in done['outputs'].items():assert sha256(A/name)==h
 audit_path=P/'quanta_parameter_economic_completion_20260920_2141/validation.json';audit=json.loads(audit_path.read_text());assert audit['status']=='actual_quanta_parameter_library_four_accounts_and_exploratory_analysis_complete' and audit['analysis_completion_sha256']==sha256(A/'completion.json')
 comparisons=json.loads((A/'comparisons.json').read_text());performance=json.loads((A/'performance.json').read_text());daily=pd.read_csv(A/'daily_net_returns.csv',parse_dates=['date'])
 for row in comparisons:assert row['observations']==963 and row['primary_ci_low']<-.02 and row['primary_ci_high']>.02
 order=[('opening_information','alpha158'),('opening_information','source4'),('native','alpha158'),('native','source4')]
 comps=[next(x for x in comparisons if (x['execution'],x['baseline'])==key) for key in order]
 labels={'source4':'Source4','alpha158':'Alpha158'}
 def name(row):return ('Opening proxy' if row['execution']=='opening_information' else 'Native diagnostic')+' / '+labels[row['baseline']]
 def csv_rows(rows,path):pd.DataFrame([{k:json.dumps(v,sort_keys=True) if isinstance(v,(dict,list)) else v for k,v in row.items()} for row in rows]).to_csv(path,index=False)
 csv_rows(comparisons,T/'comparisons_full_audit.csv');csv_rows(performance,T/'performance_full_audit.csv')
 processed=[]
 for arm in ['source4','alpha158']:
  run=P/('quantaalpha_paper_parameters_oos_'+arm+'_plus_library');proof=json.loads((run/'independent_accounts/validation.json').read_text())
  for row in proof['processed_features']:processed.append({'baseline':arm,**row,'source_validation':str(run/'independent_accounts/validation.json')})
 csv_rows(processed,T/'processed_features_full_audit.csv')
 contract={'scope':'Exploratory Quanta paper-parameter fixed-library sensitivity; not primary or isolated parameter effect','display_order':order,'dates':['2022-01-07','2025-12-26'],'sessions':963,'source_program_hashes':142,'expression_columns':142,'raw_matrix_rows':801001,'base_features':[4,158],'augmented_features':[146,300],'new_augmented_models':2,'opening_replays_of_saved_predictions':2,'baseline_refits':0,'annualization':252,'group_lengths':[241,241,241,240],'pointwise_confidence':.99,'economic_margin_pp_per_year':2,'p_values':'Raw descriptive two-sided four-group t p-values; no project family significance claim','source_parameters':{'symbol_length_threshold':250,'base_features_threshold':6,'duplication_threshold':5,'requested_factors':3,'directions':10,'total_phases':5,'consistency_checks':True},'symbol_length_is_not_stock_universe_size':True,'model':'openai/gpt-5.2','source_max_tokens':3000,'source_reasoning_effort':'none','original_primary_replaced':False,'human_review':False}
 atomic_json(O/'report_contract.json',contract)
 plt.rcParams.update({'figure.facecolor':WHITE,'axes.facecolor':WHITE,'savefig.facecolor':WHITE,'text.color':TEXT,'axes.labelcolor':TEXT,'xtick.color':TEXT,'ytick.color':TEXT,'axes.edgecolor':GRID,'grid.color':GRID,'font.family':'DejaVu Sans','font.size':10,'axes.titleweight':'bold','axes.titlecolor':TEXT,'legend.facecolor':WHITE,'legend.edgecolor':GRID,'legend.labelcolor':TEXT})
 fig,ax=plt.subplots(figsize=(10.8,4.7));fig.subplots_adjust(left=.29,right=.97,bottom=.24,top=.80)
 ax.axvspan(-2,2,color='#e0f2fe');ax.axvline(0,color=MUTED,lw=1)
 for y,row in enumerate(comps):
  mean=row['annualized_arithmetic_effect']*100;lo=row['primary_ci_low']*100;hi=row['primary_ci_high']*100;color=BLUE if row['execution']=='opening_information' else GREY
  ax.errorbar(mean,y,xerr=[[mean-lo],[hi-mean]],fmt='o',color=color,elinewidth=2,capsize=5,markersize=7)
  ax.text(hi+.7,y,f"p={row['group_t_p_two_sided']:.3f}",color=TEXT,va='center',fontsize=9)
 ax.set_yticks(range(4),[name(x) for x in comps]);ax.invert_yaxis();ax.set_xlim(-31,44);ax.set_xlabel('Annualized paired net-return increment (percentage points/year)',color=TEXT);ax.grid(axis='x',alpha=.6);ax.set_axisbelow(True)
 for spine in ['top','right','left']:ax.spines[spine].set_visible(False)
 fig.suptitle('Positive estimates, wide intervals: all four comparisons remain inconclusive',x=.03,ha='left',y=.98,color=TEXT,fontsize=13,fontweight='bold')
 fig.text(.03,.89,'Equal-weight four-block means and pointwise 99% t intervals; blue band = ±2 pp annual margin.',color=MUTED,fontsize=10)
 fig.text(.03,.05,'Opening proxy = finite current open / prior close eligibility. Native execution is a conformance diagnostic. Raw p-values.',color=MUTED,fontsize=9)
 fig.savefig(F/'effects_99.png',dpi=170);plt.close(fig)
 fig,axes=plt.subplots(1,2,figsize=(10.8,4.6));fig.subplots_adjust(left=.075,right=.98,bottom=.24,top=.78,wspace=.23)
 for ax,arm in zip(axes,['source4','alpha158']):
  for role,color,label in [('explicitly_reused_common_baseline',GREY,'Reused baseline'),('variant_augmented',BLUE,'Baseline + 142 expressions')]:
   frame=daily[(daily.execution=='opening_information')&(daily.baseline==arm)&(daily.role==role)].sort_values('date');assert len(frame)==963 and not frame.date.duplicated().any()
   wealth=(1+frame.net_return).cumprod();expected=next(x['ending_wealth'] for x in performance if x['execution']=='opening_information' and x['baseline']==arm and x['role']==role);assert abs(float(wealth.iloc[-1])-expected)<1e-12
   ax.plot(frame.date,wealth,color=color,lw=1.6,label=label)
  ax.set_ylim(.74,1.34);ax.set_yticks([.8,.9,1.,1.1,1.2,1.3]);ax.set_title(labels[arm],color=TEXT);ax.set_ylabel('Wealth per initial 1, net costs',color=TEXT);ax.grid(alpha=.45);ax.xaxis.set_major_locator(mdates.YearLocator());ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'));ax.spines['top'].set_visible(False);ax.spines['right'].set_visible(False)
 fig.suptitle('Opening-information proxy: the same 963 sessions and saved predictions',x=.03,ha='left',y=.98,color=TEXT,fontsize=13,fontweight='bold')
 fig.text(.03,.89,'2022-01-07 to 2025-12-26. Two augmented fits; four common native/opening baseline paths reused without refitting.',color=MUTED,fontsize=10)
 legend=fig.legend(handles=[Line2D([0],[0],color=GREY,lw=2,label='Reused baseline'),Line2D([0],[0],color=BLUE,lw=2,label='Baseline + 142 expressions')],loc='lower center',bbox_to_anchor=(.5,.03),ncol=2,frameon=False)
 for text in legend.get_texts():text.set_color(TEXT)
 fig.savefig(F/'opening_wealth.png',dpi=170);plt.close(fig)
 effect_table=table(['Comparison','Full mean Δ pp/y','Group mean Δ pp/y','Pointwise 99% CI, pp/y','Raw p'],[[name(x),f"{100*x['full_sample_annualized_effect']:+.4f}",f"{100*x['annualized_arithmetic_effect']:+.4f}",f"[{100*x['primary_ci_low']:+.4f}, {100*x['primary_ci_high']:+.4f}]",f"{x['group_t_p_two_sided']:.6f}"] for x in comps])
 wealth_rows=[]
 for arm in ['source4','alpha158']:
  rows={x['role']:x for x in performance if x['execution']=='opening_information' and x['baseline']==arm};a=rows['variant_augmented'];b=rows['explicitly_reused_common_baseline'];wealth_rows.append([labels[arm],f"{b['ending_wealth']:.8f}",f"{a['ending_wealth']:.8f}",f"{100*b['max_drawdown']:.3f}%",f"{100*a['max_drawdown']:.3f}%"])
 wealth_table=table(['Opening proxy','Baseline wealth','Augmented wealth','Baseline drawdown','Augmented drawdown'],wealth_rows)
 processing_table=table(['Arm / segment','Rows','Features','Processed missing','Processed infinity','Constant/missing columns'],[[labels[x['baseline']]+' / '+x['segment'],f"{x['rows']:,}",x['features'],x['missing_values'],x['infinite_values'],x['constant_or_missing_columns']] for x in processed])
 raw_table=table(['Completed raw library diagnostic','Value'],[['Rows × expression columns','801,001 × 142'],['Raw infinite cells',f"{audit['raw_library_infinite_cells']:,}"],['Columns containing raw infinity',audit['raw_library_infinite_columns']],['Raw missing cells',f"{audit['raw_library_missing_cells']:,}"],['Full-universe proof programs flagged for infinity','12 (different universe/check scope)']])
 artifacts=[{'role':'Canonical comparisons','file':str(A/'comparisons.json'),'sha256':sha256(A/'comparisons.json')},{'role':'Canonical performance','file':str(A/'performance.json'),'sha256':sha256(A/'performance.json')},{'role':'Saved aggregate net paths','file':str(A/'daily_net_returns.csv'),'sha256':sha256(A/'daily_net_returns.csv')},{'role':'Economic preservation audit (private)','file':str(audit_path),'sha256':sha256(audit_path)},{'role':'Fixed library manifest (private)','file':str(P/'quantaalpha_paper_parameters_fixed_library/library_manifest.json'),'sha256':audit['library_manifest_sha256']},{'role':'Frozen economic protocol','file':str(U/'quanta_paper_parameter_evaluation_protocol.json'),'sha256':done['protocol_sha256']}]
 csv_rows(artifacts,T/'artifact_index.csv');atomic_json(T/'raw_library_diagnostics.json',{k:audit[k] for k in ['raw_library_infinite_cells','raw_library_infinite_columns','raw_library_missing_cells','full_universe_proof_raw_infinity_program_flags','raw_infinity_scopes_differ']})
 headline=next(x for x in comps if x['execution']=='opening_information' and x['baseline']=='alpha158')
 hp={x['role']:x for x in performance if x['execution']=='opening_information' and x['baseline']=='alpha158'}
 text=f'''# Quanta paper-parameter sensitivity — completed exploratory results

All four comparisons remain **inconclusive at the ±2 percentage-point annual margin**. Point estimates are positive, while every pointwise 99% interval covers zero and both margin endpoints. This does not establish equivalence, significant alpha, an isolated parameter effect or a faithful full-paper reproduction.

For the opening-information Alpha158 comparison, the full-sample mean increment is **{100*headline['full_sample_annualized_effect']:+.4f} pp/year**; the four-block estimate is **{100*headline['annualized_arithmetic_effect']:+.4f} pp/year**, with grouped pointwise 99% interval **[{100*headline['primary_ci_low']:+.4f}, {100*headline['primary_ci_high']:+.4f}] pp/year** and raw two-sided p = **{headline['group_t_p_two_sided']:.6f}**. Ending wealth is **{hp['variant_augmented']['ending_wealth']:.8f}** versus the reused baseline's **{hp['explicitly_reused_common_baseline']['ending_wealth']:.8f}**. The opening Source4 comparison is also inconclusive. All four comparisons are retained below.

## Comparison and inference

![Annualized paired effects with pointwise 99% intervals](visual_figures/effects_99.png)

{effect_table}

[Full comparison audit CSV](visual_tables/comparisons_full_audit.csv). The figure uses equal-weight block means; the full-sample mean weights all963sessions equally. Blocks contain241/241/241/240sessions, explaining their small differences. Annualization is252×the corresponding daily mean difference. Intervals and p-values use four contiguous groups and3degrees of freedom, under the stated approximate block-independence/normality assumptions. These are pointwise intervals, not simultaneous margin bounds. The saved factor_count=0 denotes no factor adjustment; there is no JKP132 attribution or per-block model refit in this comparison. Raw p-values are descriptive exploratory values, with no project-family significance claim.

## Opening-information wealth paths

![Opening-information proxy wealth paths](visual_figures/opening_wealth.png)

{wealth_table}

[Full performance audit CSV](visual_tables/performance_full_audit.csv). Both panels use the same963sessions,2022-01-07 through2025-12-26. Wealth compounds saved daily returns net of costs. The cagr field in the canonical audit means252-session geometric annualization, not calendar-year CAGR. Drawdown is the maximum compounded-wealth drawdown; it is not a drawdown of an additive excess-return curve.

## Fixed comparison contract

The default report view is the opening-information comparison; native execution is a conformance diagnostic. The intervention adds the entire142-expression library to Source4 or Alpha158. It is not an isolated comparison of one search parameter, and no configuration is selected for trading from these results.

| Contract | Completed setting |
| --- | --- |
| Baseline / augmented features | Source4:4→146; Alpha158:158→300 |
| New fits / opening replays |2augmented fits;2replays of their saved predictions |
| Common baseline reuse |4existing native/opening paths;0baseline refits |
| Economic settings |Identical within each comparison; buy5bp/sell15bp,min5, native lot rules and common calendars |
| Generation / evaluation boundary |Six generation fields bounded through2022-01-05; first signalJan6/fillJan7,2022 |
| Search settings |Symbol-length threshold250,base-feature threshold6,duplication5,consistencyON,3requested factors,10directions/10crossovers/five total phases |
| Meaning of symbol length |Expression complexity threshold; not the stock-universe size |
| Source model |Current GPT-5.2/OpenAI,max3000,reasoningnone,recorded ordinal seeds and supported request parameters |
| Source parameters versus released default |Multiple settings/routes/histories differ; no isolated parameter-effect or historical-model equivalence claim |

The opening proxy uses finite positive current open/prior close and the same9.5% threshold, with saved predictions/labels, fees,lots and dates held fixed. Native Qlib eligibility uses same-day closing-change/missingness information. Board/auction/liquidity/adjustment-vintage fidelity remains incomplete. Generation did not receive evaluation HDFs; later deterministic program proofs and fixed-library evaluation use the declared full panel. AppendixA.4 defines five total phases; AppendixBconflicts. Historical seeds,zoo,segment-splicing and pristine model/data snapshots remain gaps.

## Raw values and native preprocessing

{raw_table}

[Raw-library diagnostic JSON](visual_tables/raw_library_diagnostics.json). The12full-universe proof flags and7membership-filtered library columns have different scopes; their cell counts must not be added. All142programs remain in the library. Raw infinities and missingness are retained in source/library evidence, even though the actual processed model inputs are finite.

{processing_table}

[Full processed-feature audit CSV](visual_tables/processed_features_full_audit.csv). These are saved independent-validator diagnostics from the two actual native fits; the opening replays reuse their predictions and processed-feature evidence. No factor, model or account was regenerated for this report.

## Completed evidence and limits

The source/full replay preserve3644chat,589embedding and680quality-event records,50LOOP IDs separately from50POOL IDs, both original and partial history gates and reconstructed RNG receipts. Reconstructed RNG is not a comparison with unavailable original RAM. All51saved source-period backtest workspaces are accounted for:50pool/export experiments plus1explicit baseline. All50source accounts pass243sessions. The142full-universe program proofs pass four actual historical cutoffs and exact native matrix comparisons;12raw-infinity flags remain preserved. These counts are workflow records, not independent trials or scientific successes.

The fixed library contains801,001rows and142distinct expressions. The four later-period native/opening accounts pass independent validation for963sessions each, with their recipes, predictions, features, matrices and calendars hash-bound. The original timeout, V2continuation guard failure, terminal-telemetry admission issue and failed old matrix-containment proof attempts remain preserved. Only failed/unstarted work was continued; completed source/model/proof jobs and baseline fits were not repeated.

The experiment is a separately declared exploratory paper-parameter sensitivity. It does not replace released-default Quanta, the strict Alpha primary, the original four-primary family, the54-secondary family or any of the frozen v1six comparisons. All69paper dispositions remain separate. One market history, current models and incomplete historical inputs prevent a pristine or untouched-holdout claim. Existing bootstrap calibration limits remain relevant; no confidence guarantee is imported from a different sample length.

This case's numerical execution is complete. AMZN's separately unapproved retry and complete13-equity accounting remain unresolved elsewhere in the project. The full manuscript, immutable public/private bundles and durable independent archives remain separate work. Assistant numerical/visual QA is not independent human source review. Project preservation copies are not final/off-allocation archives.

## Audit artifacts and reproduction

[Canonical comparisons](../quanta_paper_parameter_sensitivity/comparisons.json), [canonical performance](../quanta_paper_parameter_sensitivity/performance.json), [analysis completion](../quanta_paper_parameter_sensitivity/completion.json), [source/proof admission](../quanta_all142_proofs_completion.json), [source accounts](../quanta_source_closure_completion.json), [full artifact index with absolute paths and hashes](visual_tables/artifact_index.csv), [report contract](report_contract.json).

Rebuild presentation artifacts only, from already completed results:

```bash
cd /nfs/roberts/project/pi_btk22/zc362/alpha_evolve
/nfs/roberts/project/pi_btk22/zc362/environments/venvs/alpha-agent-replication-py312-20260813/bin/python scripts/build_quanta_parameter_report_v1.py
/nfs/roberts/project/pi_btk22/zc362/environments/venvs/alpha-agent-replication-py312-20260813/bin/python scripts/validate_quanta_parameter_report_v1.py
```

A completed report is preserved; later presentation changes require a new report version. These commands do not rerun the study, its sources, models, accounts or completed factor proofs.
'''
 (O/'VISUAL_REPORT.md').write_text(text)
 (O/'REPORT.md').write_text(re.sub(r'!\[[^\]]*\]\([^)]*\)\n\n','',text))
 atomic_json(O/'report_build.json',{'status':'built_pending_numeric_and_assistant_visual_QA','builder_sha256':sha256(Path(__file__)),'canonical_analysis_completion_sha256':sha256(A/'completion.json'),'economic_audit_sha256':sha256(audit_path),'inputs':{str(A/n):h for n,h in done['outputs'].items()},'new_study_execution':False,'independent_human_review':False})
 print('QUANTA_PARAMETER_REPORT_BUILT_FROM_COMPLETED_RESULTS',flush=True)
if __name__=='__main__':main()
