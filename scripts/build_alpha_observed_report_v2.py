#!/usr/bin/env python3
"""Report the complete, separate observed-history sensitivity from saved paths."""
from pathlib import Path
import json,re,sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from alpha_evolve.openrouter_budget import atomic_json,sha256
from alpha_evolve.publication_inference import grouped_t_effect
from analyze_publication_upgrade import metrics
from build_quanta_results_report_v2 import layout_check,md_table
PUBLIC=ROOT/'paper_runs/fidelity_completion_v2'
SOURCE=PUBLIC/'alpha_observed_history_sensitivity'
OUT=PUBLIC/'alpha_observed_history_report'
FG='#172B4D';BG='#FFFFFF';BLUE='#17456B';GOLD='#925000';GREY='#596579'

def read(p):return json.loads(p.read_text())
def close(a,b):return bool(np.isclose(a,b,rtol=0,atol=1e-12))
def save(fig,name):
    for ax in fig.axes:
        low,high=ax.get_xlim();ax.set_xticks([x for x in ax.get_xticks() if low<=x<=high])
    layout_check(fig)
    for suffix,dpi in [('.png',160),('_preview.png',80),('.pdf',160)]:
        fig.savefig(OUT/'visual_figures'/(name+suffix),dpi=dpi,facecolor=BG,edgecolor=BG)
    plt.close(fig)

def main():
    done=read(SOURCE/'completion.json')
    if done['status']!='exploratory_observed_history_sensitivity_complete_not_primary':raise ValueError('Complete separate analysis required')
    if any(done[k] for k in ['strict_primary_eligibility','original_four_case_family_complete','original54_secondary_family_complete','full_original_paper_reproduced']):raise ValueError('Sensitivity scope was changed')
    for name,digest in done['outputs'].items():
        if sha256(SOURCE/name)!=digest:raise ValueError('Analysis output changed: '+name)
    for name,digest in done['source_files'].items():
        if sha256(ROOT/name)!=digest:raise ValueError('Exact executed analyzer source changed: '+name)
    if sha256(PUBLIC/'alpha_observed_history_sensitivity_protocol.json')!=done['protocol_sha256']:raise ValueError('Protocol changed')
    library=read(PUBLIC/'alpha_observed_library_validation.json')
    native=read(PUBLIC/'alpha_observed_native_validation.json')
    costs=read(PUBLIC/'alpha_observed_cost_attribution.json')
    for record in [library,native]:
        if sha256(ROOT/record['private_validation_path'])!=record['private_validation_sha256']:raise ValueError('Runtime audit binding changed')
    catalogue=read(SOURCE/'observed_source_catalogue.json')
    if [r['trial'] for r in catalogue['trials']]!=list(range(1,21)) or catalogue['actual_attempted_rounds']!=96 or catalogue['unattempted_rounds']!=4:raise ValueError('All20 actual outcomes required')
    raw=pd.read_csv(SOURCE/'daily_net_returns.csv',parse_dates=['date'])
    comparisons=read(SOURCE/'comparisons.json');performance=read(SOURCE/'performance.json')
    if len(comparisons)!=2 or len(performance)!=4 or len(raw)!=4*238:raise ValueError('Incomplete fixed comparison population')
    if sorted(r['execution'] for r in comparisons)!=['native','opening_information']:raise ValueError('Wrong execution scopes')
    paths={};numeric_checks=[]
    for execution in ['native','opening_information']:
        for arm in ['alpha158','alpha158_plus_library']:
            values=raw[(raw.execution==execution)&(raw.arm==arm)].set_index('date').net_return
            if len(values)!=238 or not values.index.is_unique or not values.index.is_monotonic_increasing or not np.isfinite(values).all():raise ValueError('Incomplete or invalid saved path')
            provider=Path(read(ROOT/'artifacts/fidelity_completion_v2/quantaalpha_data/manifest.json')['provider_path'])
            calendar=pd.DatetimeIndex(pd.to_datetime((provider/'calendars/day.txt').read_text().splitlines()))
            expected=calendar[(calendar>=pd.Timestamp('2025-01-06'))&(calendar<=pd.Timestamp('2025-12-26'))]
            if not values.index.equals(expected):raise ValueError('Full exact calendar required; no intersection')
            paths[(execution,arm)]=values
            report=next(r for r in performance if r['execution']==execution and r['arm']==arm)
            actual=metrics(values,frequency=252)
            for key,value in actual.items():
                if isinstance(value,(int,float)) and not close(value,report[key]):raise ValueError('Performance recomputation failed: '+key)
            numeric_checks.append({'execution':execution,'arm':arm,'metrics_recomputed':list(actual)})
        left=paths[(execution,'alpha158_plus_library')];right=paths[(execution,'alpha158')]
        result=grouped_t_effect(left.to_numpy(),right.to_numpy(),frequency=252,groups=4,threshold=.02,confidence=.99)
        row=next(r for r in comparisons if r['execution']==execution)
        for key in ['full_sample_annualized_effect','annualized_arithmetic_effect','primary_ci_low','primary_ci_high','group_t_p_two_sided']:
            if not close(result[key],row[key]):raise ValueError('Comparison recomputation failed: '+key)
        if row['project_family_significance_claim'] or row['strict_primary_eligibility']:raise ValueError('Forbidden primary substitution')
    if OUT.exists():raise ValueError('Existing or partial report must be inspected and preserved before rebuilding')
    for name in ['visual_figures','visual_tables']:(OUT/name).mkdir(parents=True)
    pd.DataFrame(comparisons).to_csv(OUT/'visual_tables/comparisons_full_audit.csv',index=False)
    pd.DataFrame(performance).to_csv(OUT/'visual_tables/performance_full_audit.csv',index=False)
    trial_rows=[{k:r[k] for k in ['trial','native_status','attempted_rounds','failed_round_indices','unattempted_round_indices','completed_trajectories','used_program_count']} for r in catalogue['trials']]
    pd.DataFrame(trial_rows).to_csv(OUT/'visual_tables/all20_source_outcomes.csv',index=False)
    feature_rows=[dict(arm=r['arm'],**x) for r in native['arms'] for x in r['processed_features']]
    pd.DataFrame(feature_rows).to_csv(OUT/'visual_tables/processed_features.csv',index=False)
    plt.rcParams.update({'text.color':FG,'axes.labelcolor':FG,'axes.edgecolor':FG,'xtick.color':FG,'ytick.color':FG,'axes.facecolor':BG,'figure.facecolor':BG,'savefig.facecolor':BG,'legend.labelcolor':FG,'legend.facecolor':BG,'legend.edgecolor':'#B5C2D2','font.size':11,'font.family':'DejaVu Sans'})
    fig,ax=plt.subplots(figsize=(10,5.4));fig.subplots_adjust(left=.11,right=.97,bottom=.2,top=.82)
    for arm,label,color in [('alpha158','Alpha158',GREY),('alpha158_plus_library','Alpha158 + observed library',BLUE)]:
        series=paths[('opening_information',arm)];ax.plot(series.index,(1+series).cumprod(),color=color,lw=1.8,label=label)
    ax.set_ylabel('Net wealth (initial capital = 1)');ax.grid(color='#D8E0EA',lw=.6);ax.set_axisbelow(True)
    ax.legend(loc='upper center',bbox_to_anchor=(.5,-.12),ncol=2,frameon=True)
    fig.suptitle('AlphaAgent observed-history sensitivity',fontsize=15,color=FG,y=.97)
    fig.text(.5,.885,'Opening-information eligibility | 238 sessions | all 20 source outcomes',ha='center',color=FG)
    save(fig,'opening_wealth')
    ordered=[next(r for r in comparisons if r['execution']==x) for x in ['opening_information','native']]
    fig,ax=plt.subplots(figsize=(10,4.7));fig.subplots_adjust(left=.25,right=.96,bottom=.25,top=.78)
    for i,row in enumerate(ordered):
        mean=100*row['annualized_arithmetic_effect'];lo=100*row['primary_ci_low'];hi=100*row['primary_ci_high']
        ax.errorbar(mean,i,xerr=[[mean-lo],[hi-mean]],fmt='o',capsize=5,color=BLUE if i==0 else GREY,lw=2)
    ax.set_yticks([0,1],['Opening information','Native diagnostic']);ax.set_ylim(-.55,1.55);ax.invert_yaxis()
    ax.axvline(0,color=FG,ls='--',lw=1,label='Zero increment');ax.axvline(2,color=GOLD,ls=':',lw=1.5,label='+2 pp margin')
    ax.set_xlabel('Grouped annualized arithmetic-mean increment (pp/year)');ax.grid(axis='x',color='#D8E0EA',lw=.6);ax.set_axisbelow(True)
    ax.legend(loc='upper center',bbox_to_anchor=(.5,-.23),ncol=2,frameon=True)
    fig.suptitle('Paired increment over the same Alpha158 baseline',fontsize=14,color=FG,y=.97)
    fig.text(.5,.875,'Four contiguous time blocks | pointwise 99% intervals | exploratory only',ha='center',color=FG)
    save(fig,'paired_intervals')
    primary=ordered[0]
    wealth_rows=[{'arm':'Alpha158' if r['arm']=='alpha158' else 'Alpha158 + observed library','wealth':f"{r['ending_wealth']:.6f}",'return':f"{100*(r['ending_wealth']-1):+.3f}%"} for r in performance if r['execution']=='opening_information']
    effect_rows=[{'execution':'Opening information' if r['execution']=='opening_information' else 'Native diagnostic','mean':f"{100*r['full_sample_annualized_effect']:+.3f}",'grouped':f"{100*r['annualized_arithmetic_effect']:+.3f}",'interval':f"[{100*r['primary_ci_low']:.3f}, {100*r['primary_ci_high']:.3f}]",'p':f"{r['group_t_p_two_sided']:.6f}"} for r in ordered]
    lines=['# AlphaAgent: all20 observed-history sensitivity','',f"The observed library changes the full-sample annualized mean net return by {100*primary['full_sample_annualized_effect']:+.3f} percentage points relative to Alpha158 under opening-information eligibility. The grouped pointwise99% interval is [{100*primary['primary_ci_low']:.3f}, {100*primary['primary_ci_high']:.3f}]pp/year, with descriptive raw p={primary['group_t_p_two_sided']:.6f}.",'','This is the separately declared exploratory comparison conditional on all20 realized source outcomes and their mixed attempt budgets. The original strict20-by5 primary is unavailable because trials12/14 ended early. This result cannot replace that primary or enter the original four-primary/54-secondary families. No confirmatory or project-family significance claim is made.','','## Net wealth under opening information','','![Opening-information net wealth](visual_figures/opening_wealth.png)','',*md_table(wealth_rows,[('Arm','arm'),('Ending wealth','wealth'),('Cumulative return','return')]),'','[Full performance audit](visual_tables/performance_full_audit.csv). Both paths use the exact same238-session calendar, January6–December26,2025, native fees/lots/portfolio settings and initial capital. Wealth is normalized for display.','','## Mean increments and execution diagnostic','','![Paired mean increments and pointwise intervals](visual_figures/paired_intervals.png)','',*md_table(effect_rows,[('Execution','execution'),('Full mean, pp/year','mean'),('Grouped mean, pp/year','grouped'),('Pointwise99% interval, pp','interval'),('Raw p','p')]),'','[Full comparison audit](visual_tables/comparisons_full_audit.csv). Full-sample and equally weighted block means are distinct estimators. Error bars are centered on the grouped mean; intervals concern arithmetic mean differences, not geometric growth or simultaneous2pp bounds. No multiplicity-adjusted significance flag is assigned to this separate sensitivity.','','## Fixed comparison contract','','| Choice | Executed scope |','|---|---|','| Library population | All20 original outcomes; no later-return selection |','| Features | Alpha158 versus Alpha158 +146 observed expression columns |','| Fitting | Two fixed native fits; common nonfeature settings |','| Economic sensitivity | Opening-information eligibility; same saved predictions/labels |','| Diagnostic | Source-native eligibility using same-day change/closing missingness |','| Inference | Four contiguous groups;252-session annualization;99% pointwise intervals;2pp margin |','| Untested / unavailable | Strict100-attempt primary; independent market histories; pristine historical model snapshot |','','The opening proxy uses finite positive current open and prior close with the same uniform9.5% threshold. It preserves native predictions, labels, fees, lots, capital and dates without refitting. Exact board/auction/liquidity/impact and adjustment-vintage rules are not reproduced. Native eligibility results are diagnostics.','','## Source outcomes, costs and missingness','',f"All20 source outcomes contributed their actual backtested programs:96 attempted rounds,4 unattempted rounds and86 completed native histories. Sixteen searches returned normally;08/15 failed on their final attempted round, while12/14 failed early. All recorded responses, failures, embeddings, financial histories and actual-used-program proofs were verified. The159 program uses yield157 distinct program hashes and146 expressions;11 exact-expression duplicates have identical numerical columns. No failed trial or factor was removed to improve returns.",'','[All20 source outcomes](visual_tables/all20_source_outcomes.csv) · [Materialization evidence](../alpha_observed_library_validation.json) · [Source catalogue](../alpha_observed_source_progress.json).', '',f"Recorded-response cost exposure is ${costs['attributed_unique_response_cost_and_reservations_usd']:.8f}: returned chats, shared embeddings counted once, and all four retained missing-response reservations. This is not necessarily incremental spending since the corrected protocol; trial01 reuses a recorded bounded prefix. Other pilots/routes remain in the shared Alpha cap. See [cost attribution](../alpha_observed_cost_attribution.json).",'','The raw unique matrix retains five infinite cells from two programs. Native processed features have zero infinities but retain missing values. The augmented arm has two constant-or-missing columns in each segment and2,206,039/372,206/394,459 missing cells in training/validation/test. [Full processed-feature audit](visual_tables/processed_features.csv). No source factor was replaced or silently repaired for this report.','','## Interpretation and replication boundaries','','The comparison is conditional on one realized library and one market history. It does not propagate search/model-selection uncertainty or isolate a language-model-specific causal advantage. Repeated source tasks are not independent market histories. The separately frozen protocol predates these Alpha later-period returns, but historical data and current models do not establish an untouched holdout. Five-field source generation boundaries and full-universe prefix checks do not certify historical model-knowledge purity.','','Grouped calibration used4096 replications in each of eight specified synthetic cells and observed98.80–99.12% coverage for nominal99% intervals. Approximate independent normal block means remain assumptions; this is not an exact real-world1% error guarantee. The original short-sample bootstrap undercoverage remains diagnostic. Annualized mean means252 times a daily arithmetic mean; underlying cagr fields mean252-session geometric annualization, not calendar-time CAGR.','','This Chinese-market Alpha158 comparison is not JKP132 attribution, a full-paper reproduction, human source attestation or a final whole-study publication package. All69 papers retain separate evidence and gaps.','','## Evidence, validation and reproduction','','[Report validation](validation.json) · [Lineage](lineage.json) · [Completed separate analysis](../alpha_observed_history_sensitivity/completion.json) · [Source review packet](../SOURCE_REVIEW_PACKET.md).','','The builder checks completed analysis and exact executed-source hashes, recomputes both contrasts and all four path metrics from saved238-session returns, verifies complete calendars, and produces both reports and figures without fitting or API calls. The no-image counterpart is [REPORT.md](REPORT.md).','','From the canonical Bouchet checkout, when no existing report directory is present:','','```bash','/nfs/roberts/project/pi_btk22/zc362/environments/venvs/alpha-agent-replication-py312-20260813/bin/python scripts/build_alpha_observed_report_v2.py','```','','Existing complete or partial reports must be inspected and preserved before regeneration.']
    zero = primary['primary_ci_low'] <= 0 <= primary['primary_ci_high']
    positive_margin = primary['primary_ci_low'] <= .02 <= primary['primary_ci_high']
    interpretation = "The pointwise interval " + ("includes" if zero else "excludes") + " zero and " + ("includes" if positive_margin else "excludes") + " the +2pp/year margin. "
    interpretation += "Equivalence within the stated margin is " + ("supported by this pointwise interval" if primary['within_margin_using_pointwise99'] else "not established") + "; a positive2pp effect is " + ("ruled out by this pointwise interval" if primary['rules_out_positive_margin_using_pointwise99'] else "not ruled out") + ". These are conditional exploratory statements."
    lines[4:4] = [interpretation, ""]
    text='\n'.join(lines)+'\n';(OUT/'VISUAL_REPORT.md').write_text(text);(OUT/'REPORT.md').write_text(re.sub(r'!\[[^]]*\]\([^)]*\)\n?','',text))
    atomic_json(OUT/'contract.json',{'scope':done['scope'],'source_outcomes':20,'actual_attempts':96,'missing_rounds':4,'execution_sensitivity':'opening_information','native_role':'diagnostic','feature_counts':[158,304],'sessions':238,'family_entry':False,'comparison_choice_based_on_returns':False})
    atomic_json(OUT/'lineage.json',{'analysis_completion_sha256':sha256(SOURCE/'completion.json'),'analysis_source_files':done['source_files'],'builder_sha256':sha256(Path(__file__)),'presentation_helpers_sha256':sha256(ROOT/'scripts/build_quanta_results_report_v2.py'),'materialization_audit_sha256':sha256(PUBLIC/'alpha_observed_library_validation.json'),'native_audit_sha256':sha256(PUBLIC/'alpha_observed_native_validation.json'),'numeric_recomputation':numeric_checks,'source_results_overwritten':False,'new_model_calls':0})
    images=[]
    for name in ['opening_wealth','paired_intervals']:
        path=OUT/'visual_figures'/(name+'.png');a=np.asarray(Image.open(path).convert('RGB'))
        if a.std()<10:raise ValueError('Blank figure')
        images.append({'path':str(path.relative_to(OUT)),'sha256':sha256(path),'shape':list(a.shape),'pixel_std':float(a.std())})
    def lum(color):
        v=np.array([int(color[i:i+2],16)/255 for i in (1,3,5)]);v=np.where(v<=.04045,v/12.92,((v+.055)/1.055)**2.4);return float(v@np.array([.2126,.7152,.0722]))
    contrast=(lum(BG)+.05)/(lum(FG)+.05)
    if contrast<7:raise ValueError('Text contrast insufficient')
    for target in re.findall(r'\]\(([^)]+)\)',text):
        if target!='validation.json' and not (OUT/target).is_file():raise ValueError('Broken report link: '+target)
    for match in re.finditer(r'!\[[^]]*\]\([^)]*\)',text):
        if not text[match.end():].lstrip().startswith('|'):raise ValueError('Figure must immediately precede table')
    if '![' in (OUT/'REPORT.md').read_text():raise ValueError('Image in no-image report')
    atomic_json(OUT/'validation.json',{'status':'numeric_layout_pass_assistant_visual_review_pending','comparisons_recomputed':2,'performance_paths_recomputed':4,'exact_calendar_sessions':238,'all20_outcomes_retained':True,'text_contrast_ratio':contrast,'figure_text_within_canvas':True,'each_figure_followed_by_table':True,'links_exist':True,'no_image_report_pass':True,'human_attestation':None,'figures':images,'outputs':{str(p.relative_to(OUT)):sha256(p) for p in OUT.rglob('*') if p.is_file() and p.name!='validation.json'}})
    print('OBSERVED_ALPHA_REPORT_NUMERIC_LAYOUT_PASS',contrast,flush=True)
if __name__=='__main__':main()
