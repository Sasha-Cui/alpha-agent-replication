#!/usr/bin/env python3
"""Audit and report completed EFS pools without changing any study result."""
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
from alpha_evolve.openrouter_budget import sha256,atomic_json
from alpha_evolve.publication_inference import grouped_t_effect,ols_alpha
from analyze_publication_upgrade import metrics
from analyze_efs_pooled_v2 import load_market,load_pool,month_path
from collect_v2_project_primary_family import adjust_project
from build_quanta_results_report_v2 import layout_check,md_table
PUBLIC=ROOT/'paper_runs/fidelity_completion_v2';PRIVATE=ROOT/'artifacts/fidelity_completion_v2'
SOURCE=PUBLIC/'efs_pooled_analysis';DATA=PRIVATE/'efs_pooled_analysis';OUT=PUBLIC/'efs_pooled_report'
GROUPS=['grammar_101_103','gpt41','deepseek_v3'];LABELS={'grammar_101_103':'Grammar pool','gpt41':'GPT-4.1 pool','deepseek_v3':'DeepSeek pool'}
FG='#172B4D';BG='#FFFFFF';COLORS={'grammar_101_103':'#596579','gpt41':'#17456B','deepseek_v3':'#00665C'};GOLD='#925000'
def read(p):return json.loads(p.read_text())
def close(a,b):return bool(np.isclose(a,b,rtol=0,atol=1e-12))
def save(fig,name):
    for ax in fig.axes:
        lo,hi=ax.get_xlim();ax.set_xticks([x for x in ax.get_xticks() if lo<=x<=hi])
    layout_check(fig)
    for suffix,dpi in [('.png',160),('_preview.png',80),('.pdf',160)]:fig.savefig(OUT/'visual_figures'/(name+suffix),dpi=dpi,facecolor=BG,edgecolor=BG)
    plt.close(fig)
def verify_metrics(series,row):
    for key,value in metrics(series,frequency=252).items():
        if isinstance(value,(int,float)) and not close(value,row[key]):raise ValueError('Performance recomputation failed: '+key)

def main():
    done=read(SOURCE/'completion.json');plan=read(PUBLIC/'efs_final_analysis_protocol.json')
    if done['status']!='both_efs_pooled_cases_complete_project_family_pending' or done['JKP132_unrestricted_alpha_identified']:raise ValueError('Wrong completed EFS scope')
    if sha256(ROOT/'scripts/analyze_efs_pooled_v2.py')!=done['script_sha256'] or sha256(PUBLIC/'efs_final_analysis_protocol.json')!=done['protocol_sha256']:raise ValueError('Executed analysis/protocol changed')
    if sha256(PUBLIC/'efs_monthly_inference_reference.json')!=done['monthly_calibration_reference_sha256']:raise ValueError('Monthly calibration reference changed')
    for name,digest in done['outputs'].items():
        if sha256(SOURCE/name)!=digest:raise ValueError('Analysis output changed: '+name)
    for name,digest in done['private_outputs'].items():
        if sha256(DATA/name)!=digest:raise ValueError('Private diagnostic changed: '+name)
    market_path=ROOT/'artifacts/economic_fidelity/v1/efs_us50_daily.parquet'
    if sha256(market_path)!=read(market_path.with_name('data_manifest.json'))['daily_extract_sha256']:raise ValueError('Frozen market changed')
    market=load_market(market_path);assert market.shape==(1510,50)
    pools={};bindings=[]
    for group in GROUPS:pools[group],evidence=load_pool(group,market);bindings.append(evidence)
    if bindings!=read(SOURCE/'execution_evidence.json'):raise ValueError('Pool evidence changed')
    primary=read(SOURCE/'primary_comparisons.json');performance=read(SOURCE/'performance.json');cost_rows=read(SOURCE/'descriptive_comparisons.json')
    attribution=read(SOURCE/'factor_attribution_diagnostics.json');recon=read(SOURCE/'chronological_reconstruction_diagnostics.json');allocation=read(SOURCE/'gross_factor_allocation_diagnostics.json')
    if len(primary)!=2 or len(performance)!=42 or len(cost_rows)!=8:raise ValueError('Incomplete fixed report population')
    daily=pd.read_csv(SOURCE/'daily_pool_returns.csv',parse_dates=['date'])
    if len(daily)!=24*1510:raise ValueError('Missing saved pool paths')
    for group,paths in pools.items():
        for (mode,cost),value in paths.items():
            saved=daily[(daily.group==group)&(daily['mode']==mode)&(daily.cost_bps==cost)].set_index('date')['return']
            if not saved.index.equals(value.index) or not np.allclose(saved,value,rtol=0,atol=1e-14):raise ValueError('Saved analysis path differs from native pool')
            verify_metrics(value,next(r for r in performance if r['group']==group and r['mode']==mode and r['cost_bps']==cost))
    controls=pd.read_parquet(ROOT/'artifacts/publication_upgrade_v1/efs_controls/daily_returns.parquet')
    for row in performance:
        group=row['group']
        if group in GROUPS:continue
        if group.startswith('frozen_'):
            values=controls[(controls.arm==group.removeprefix('frozen_'))&(controls.cadence=='daily')&(controls.cost_bps==10)]
            path=pd.Series(values['return'].to_numpy(),index=pd.DatetimeIndex(values.date))
        elif group.startswith('grammar_seed_'):
            frame=pd.read_csv(ROOT/('artifacts/publication_upgrade_v1/efs_matched/seed_'+group.rsplit('_',1)[-1]+'/daily_returns.csv'),parse_dates=['date']).set_index('date');path=frame.total_cost_10
        else:
            folder=ROOT/'paper_runs/economic_fidelity/efs_v1' if group=='gpt41_1' else PUBLIC/'efs'/group
            path=pd.read_csv(folder/'llm_daily_returns.csv',parse_dates=['date']).set_index('date').total_cost_10
        if not path.index.equals(market.index):raise ValueError('Incomplete descriptive calendar')
        verify_metrics(path,row)
    monthly={g:month_path(pools[g][('causal_discovery_gated',10)]) for g in GROUPS}
    factors= pd.read_csv(ROOT/plan['jkp']['factor_file']);factor_cols=['capm_top1000_mkt']+[c for c in factors if c.startswith('char__')]
    if sha256(ROOT/plan['jkp']['factor_file'])!=done['factor_panel_sha256'] or len(factor_cols)!=133:raise ValueError('Wrong factor panel')
    factors.index=pd.to_datetime(factors.realization_month).dt.to_period('M');factors=factors.loc[monthly[GROUPS[0]].index,factor_cols]
    for row in primary:
        group=row['backend'];diff=monthly[group]-monthly['grammar_101_103'];result=grouped_t_effect(monthly[group].to_numpy(),monthly['grammar_101_103'].to_numpy(),frequency=12,groups=4,threshold=.02,confidence=.99)
        for key in ['full_sample_annualized_effect','annualized_arithmetic_effect','primary_ci_low','primary_ci_high','group_t_p_two_sided']:
            if not close(result[key],row[key]):raise ValueError('Primary mean/interval/p mismatch')
        if not close(row['conservative_project_family_p'],min(1,4*row['group_t_p_two_sided'])):raise ValueError('Wrong four-denominator bound')
        try:ols_alpha(diff.to_numpy(),factors.to_numpy(),frequency=12)
        except ValueError:pass
        else:raise ValueError('Unidentified134-parameter regression accepted')
        diagnostic=next(r for r in attribution if r['backend']==group and r['model']=='prespecified_six_factor_projection')
        projected=grouped_t_effect(diff.to_numpy(),factors=factors[plan['jkp']['low_dimensional_diagnostic']].to_numpy(),frequency=12,groups=4,threshold=.02,confidence=.99)
        for key in ['full_sample_annualized_effect','annualized_arithmetic_effect','primary_ci_low','primary_ci_high','group_t_p_two_sided']:
            if not close(projected[key],diagnostic[key]):raise ValueError('Six-factor diagnostic mismatch')
        for cost in [0,10,25,50]:
            left=pools[group][('causal_discovery_gated',cost)];right=pools['grammar_101_103'][('causal_discovery_gated',cost)]
            record=next(r for r in cost_rows if r['backend']==group and r['cost_bps']==cost)
            if not close(12*(month_path(left)-month_path(right)).mean(),record['full_sample_annualized_monthly_mean_increment']) or not close((1+left).prod()-(1+right).prod(),record['cumulative_return_difference']):raise ValueError('Fee diagnostic mismatch')
        for row in [r for r in recon if r['backend']==group]:
            f=pd.read_csv(DATA/(group+'_'+row['model']+'_reconstruction.csv'))
            if f.month.tolist()!=list(pd.period_range('2022-01','2024-12',freq='M').astype(str)):raise ValueError('Projection months changed')
            residual=f.difference-f.reconstructed
            if not np.allclose(residual,f.residual,rtol=0,atol=1e-14) or not close(residual.mean(),row['mean_residual']) or not close(np.sqrt(np.mean(residual**2)),row['rmse']):raise ValueError('Projection residual diagnostic mismatch')
    baseline=None;allocation_table=[]
    for group in GROUPS:
        prefix='grammar' if group=='grammar_101_103' else group
        frame=pd.read_csv(DATA/(prefix+'_allocation_returns.csv'),index_col='month');weights=np.load(DATA/(prefix+'_allocation_weights.npz'))
        if frame.index.tolist()!=list(pd.period_range('2022-01','2024-12',freq='M').astype(str)) or weights['weights'].shape!=(36,2,134):raise ValueError('Allocation calendar/weights changed')
        if baseline is None:baseline=frame.jkp_only.to_numpy()
        if not np.allclose(baseline,frame.jkp_only,rtol=0,atol=1e-14):raise ValueError('Common baseline differs')
        records=[r for r in allocation if r['backend']==group]
        for i,arm in enumerate(frame.columns):
            row=next(r for r in records if r['arm']==arm);values=frame[arm].to_numpy()
            for key,value in [('mean_annualized',12*values.mean()),('vol_annualized',np.sqrt(12)*values.std(ddof=1)),('certainty_equivalent_gamma10_annualized',12*(values.mean()-5*values.var(ddof=1))),('mean_agent_weight_in_input_units',weights['weights'][:,i,-1].mean())]:
                if not close(row[key],value):raise ValueError('Allocation summary mismatch')
        a=next(r for r in records if r['arm']!='jkp_only');b=next(r for r in records if r['arm']=='jkp_only')
        allocation_table.append({'pool':LABELS[group],'backend':group,'ce_increment_bps':1e4*(a['certainty_equivalent_gamma10_annualized']-b['certainty_equivalent_gamma10_annualized']),'mean_sleeve_weight_input_units':a['mean_agent_weight_in_input_units']})
    latest=read(PUBLIC/'project_primary_family/latest.json');family_path=ROOT/latest['snapshot'];family_done=read(family_path/'completion.json')
    if sha256(family_path/'completion.json')!=latest['completion_sha256'] or family_done['status']!='partial_four_contrast_family' or len(family_done['available_cases'])!=3:raise ValueError('Wrong project family scope')
    family=read(family_path/'comparisons.json')
    for name,digest in family_done['outputs'].items():
        if sha256(family_path/name)!=digest:raise ValueError('Project family output changed')
    if sha256(ROOT/'scripts/collect_v2_project_primary_family.py')!=family_done['script_sha256']:raise ValueError('Collector source changed')
    adjusted=adjust_project(family)
    if any(not close(a['project_adjusted_p'],b['project_adjusted_p']) or a['conditional_positive_increment_familywise']!=b['conditional_positive_increment_familywise'] for a,b in zip(family,adjusted)):raise ValueError('Project adjustment mismatch')
    if OUT.exists():raise ValueError('Inspect and preserve existing complete/partial report before rebuilding')
    for folder in ['visual_figures','visual_tables']:(OUT/folder).mkdir(parents=True)
    for name,rows in [('primary',primary),('performance',performance),('cost_sensitivity',cost_rows),('six_factor_and_unidentified',attribution),('reconstruction',recon),('allocation',allocation),('allocation_increment',allocation_table),('project_family',family)]:pd.DataFrame(rows).to_csv(OUT/'visual_tables'/(name+'_full_audit.csv'),index=False)
    plt.rcParams.update({'text.color':FG,'axes.labelcolor':FG,'axes.edgecolor':FG,'xtick.color':FG,'ytick.color':FG,'axes.facecolor':BG,'figure.facecolor':BG,'savefig.facecolor':BG,'legend.labelcolor':FG,'legend.facecolor':BG,'legend.edgecolor':'#B5C2D2','font.family':'DejaVu Sans','font.size':11})
    fig,ax=plt.subplots(figsize=(10,5.5));fig.subplots_adjust(left=.11,right=.97,top=.82,bottom=.2)
    for group in GROUPS:
        value=pools[group][('causal_discovery_gated',10)];ax.plot(value.index,(1+value).cumprod(),label=LABELS[group],color=COLORS[group],lw=1.6)
    ax.set_ylabel('Net wealth (initial capital = 1)');ax.grid(color='#D8E0EA',lw=.6);ax.set_axisbelow(True);ax.legend(loc='upper center',bbox_to_anchor=(.5,-.12),ncol=3,frameon=True)
    fig.suptitle('EFS: three-trajectory causal pools versus matched grammar',color=FG,fontsize=14,y=.97);fig.text(.5,.885,'Fixed 2019–2024 US50 panel | 1,510 sessions | 10bp per traded notional',ha='center',color=FG);save(fig,'causal_wealth')
    fig,ax=plt.subplots(figsize=(10,4.6));fig.subplots_adjust(left=.19,right=.96,top=.79,bottom=.25)
    for i,row in enumerate(primary):
        mean=100*row['annualized_arithmetic_effect'];lo=100*row['primary_ci_low'];hi=100*row['primary_ci_high'];ax.errorbar(mean,i,xerr=[[mean-lo],[hi-mean]],fmt='o',capsize=5,lw=2,color=COLORS[row['backend']])
    ax.set_yticks([0,1],[LABELS[r['backend']] for r in primary]);ax.set_ylim(-.55,1.55);ax.invert_yaxis();ax.axvline(0,color=FG,ls='--',lw=1,label='Zero increment');ax.axvline(2,color=GOLD,ls=':',lw=1.5,label='+2pp margin');ax.set_xlabel('Annualized monthly-mean increment versus grammar (pp/year)');ax.grid(axis='x',color='#D8E0EA',lw=.6);ax.set_axisbelow(True);ax.legend(loc='upper center',bbox_to_anchor=(.5,-.23),ncol=2)
    fig.suptitle('Positive means, wide uncertainty',color=FG,fontsize=15,y=.97);fig.text(.5,.88,'72 months | four 18-month blocks | pointwise 99% intervals',ha='center',color=FG);save(fig,'primary_intervals')
    fig,ax=plt.subplots(figsize=(9,4.8));fig.subplots_adjust(left=.12,right=.96,top=.83,bottom=.23)
    for group in GROUPS[1:]:
        chosen=sorted([r for r in cost_rows if r['backend']==group],key=lambda r:r['cost_bps']);ax.plot([r['cost_bps'] for r in chosen],[100*r['full_sample_annualized_monthly_mean_increment'] for r in chosen],marker='o',color=COLORS[group],label=LABELS[group])
    ax.axvline(10,color=FG,ls=':',lw=1);ax.set_xticks([0,10,25,50]);ax.set_xlabel('Transaction cost per traded notional (bp)');ax.set_ylabel('Monthly-mean increment (pp/year)');ax.grid(color='#D8E0EA',lw=.6);ax.set_axisbelow(True);ax.legend(loc='upper center',bbox_to_anchor=(.5,-.2),ncol=2);fig.suptitle('Fee sensitivity: the 10bp comparison remains primary',color=FG,fontsize=14,y=.97);save(fig,'fee_sensitivity')
    fig,ax=plt.subplots(figsize=(9,4.6));fig.subplots_adjust(left=.23,right=.95,top=.8,bottom=.19)
    for i,row in enumerate(allocation_table):
        value=row['ce_increment_bps'];ax.barh(i,value,color=COLORS[row['backend']],height=.45);ax.scatter([value],[i],color=COLORS[row['backend']],s=25);ax.text(value-.2,i,f'{value:.2f}',ha='right',va='center',color=FG)
    ax.set_yticks(range(3),[r['pool'] for r in allocation_table]);ax.invert_yaxis();ax.set_xlim(min(r['ce_increment_bps'] for r in allocation_table)-2,1);ax.axvline(0,color=FG,lw=1);ax.set_xlabel('Change in annualized certainty equivalent (bp/year)');ax.grid(axis='x',color='#D8E0EA',lw=.6);ax.set_axisbelow(True);fig.suptitle('Fixed gross-factor allocator diagnostic, 2022–2024',color=FG,fontsize=14,y=.97);fig.text(.5,.87,'Same JKP-only baseline | 36 months | financing and factor costs omitted',ha='center',color=FG);save(fig,'allocation_diagnostic')
    primary_table=[{'pool':LABELS[r['backend']],'mean':f"{100*r['full_sample_annualized_effect']:+.3f}",'ci':f"[{100*r['primary_ci_low']:.3f}, {100*r['primary_ci_high']:.3f}]",'raw':f"{r['group_t_p_two_sided']:.6f}",'adjusted':f"{r['conservative_project_family_p']:.3f}"} for r in primary]
    wealth_table=[{'pool':LABELS[r['group']],'wealth':f"{r['ending_wealth']:.6f}",'growth':f"{100*r['cagr']:.3f}%",'drawdown':f"{100*r['max_drawdown']:.3f}%"} for r in performance if r['group'] in GROUPS and r['mode']=='causal_discovery_gated' and r['cost_bps']==10]
    fee_table=[{'cost':c,**{g:f"{100*next(r['full_sample_annualized_monthly_mean_increment'] for r in cost_rows if r['backend']==g and r['cost_bps']==c):+.3f}" for g in GROUPS[1:]}} for c in [0,10,25,50]]
    alloc_table=[{'pool':r['pool'],'ce':f"{r['ce_increment_bps']:+.3f}",'weight':f"{r['mean_sleeve_weight_input_units']:.8f}"} for r in allocation_table]
    six_table=[{'pool':LABELS[r['backend']],'grouped':f"{100*r['annualized_arithmetic_effect']:+.3f}",'ci':f"[{100*r['primary_ci_low']:.3f}, {100*r['primary_ci_high']:.3f}]",'raw':f"{r['group_t_p_two_sided']:.6f}"} for r in attribution if r['model']=='prespecified_six_factor_projection']
    recon_table=[{'pool':LABELS[r['backend']],'model':r['model'],'rmse':f"{100*r['rmse']:.3f}",'residual':f"{1200*r['mean_residual']:+.3f}"} for r in recon]
    lines=['# EFS: completed matched-pool comparisons','',f"The causal GPT-4.1 and DeepSeek pools add {100*primary[0]['full_sample_annualized_effect']:+.3f} and {100*primary[1]['full_sample_annualized_effect']:+.3f} percentage points of annualized monthly mean net return, respectively, over the fixed three-trajectory grammar pool at10bp. Both99% intervals include zero and the+2pp/year margin; neither establishes equivalence nor rules out a positive2pp effect. Their conservative four-case adjusted p-values are both1.0.",'','These complete EFS comparisons do not complete the original four-case family: strict Alpha remains unavailable. Quanta plus the two EFS effects comprise three available cases, retaining four in the correction denominator. The separately completed Alpha observed-history sensitivity cannot fill the missing original contrast. No significant incremental alpha or full-paper reproduction is established.','','## Net account paths','','![Three causal pool wealth paths](visual_figures/causal_wealth.png)','',*md_table(wealth_table,[('Pool','pool'),('Ending wealth','wealth'),('252-session geometric annualization','growth'),('Maximum drawdown','drawdown')]),'','[All42 performance rows](visual_tables/performance_full_audit.csv). Displayed paths are the causal10bp pools on the same1,510-session US50 history. Growth is252-session geometric annualization, not calendar-time CAGR. Primary inference instead uses72 compounded monthly returns and12-times monthly mean differences.','','## Primary effects and uncertainty','','![EFS primary intervals](visual_figures/primary_intervals.png)','',*md_table(primary_table,[('Pool minus grammar','pool'),('Mean, pp/year','mean'),('Pointwise99% interval, pp','ci'),('Raw p','raw'),('Conservative4p','adjusted')]),'','[Full primary statistics](visual_tables/primary_full_audit.csv) · [Partial project-family audit](visual_tables/project_family_full_audit.csv). Four equally sized18-month blocks make grouped and full-sample mean differences equal here. The intervals are pointwise, not simultaneous2pp bounds; the correction is conservative4p, not Holm on a reduced three-case family. Quanta’s broader adjusted p remains0.555869.','','## Matched scope and chronology','','| Setting | Frozen choice and limit |','|---|---|','| Matched trajectories | Three per pool; grammar seeds101/102/103 fixed before pooled comparison |','| Search budgets | 290planned rounds and870planned candidates per trajectory; actual LLM admission/parsing failures retained |','| Libraries | Grammar1104; GPT-4.1 1820; DeepSeek2198 union functions, including initial seeds |','| Formation | Earliest discovery-date gating; frozen paper-guided financial engine |','| Primary cost | 10bp per traded notional;0/25/50bp descriptive |','| Hindsight | Retrospective final-union accounts retained only as diagnostics |','| Replication boundary | Hypothesis spaces, compute and model dollars differ; no isolated LLM-specific causal advantage |','','All six LLM source trajectories passed290-round completion, exact full cached replay, holdings/output identities, every preserved transport prefix and frozen engine checks. Every pool’s eight saved account paths independently re-account within9.35e-16. The grammar pool recovers the frozen execution archive without a new search. Raw historical driver bytes differ from a later formatted copy; archive/AST/generator/account evidence are distinct, not a claim of byte identity. All ten historical grammar controls and six individual LLM trials remain in the full audit table; no favorable individual replaces a pool.','','## Fee sensitivity','','![Descriptive cost sensitivity](visual_figures/fee_sensitivity.png)','',*md_table(fee_table,[('Cost, bp','cost'),('GPT increment, pp/year','gpt41'),('DeepSeek increment, pp/year','deepseek_v3')]),'','[Full fee audit](visual_tables/cost_sensitivity_full_audit.csv). Each model pool is compared with the grammar pool at the same cost. These eight descriptive comparisons do not change the primary fee or enter as selected replacements.','','## What the JKP diagnostics can identify','','Unrestricted JKP132-plus-market attribution would require134 coefficients including the intercept, with only72 monthly observations. It is not identified and was refused; no pseudoinverse estimate is presented as unrestricted alpha. The prespecified six-factor projection is a separate conditional diagnostic. Its factor list is fixed in [the protocol](../efs_final_analysis_protocol.json).','','| Diagnostic | Role and limit |','|---|---|','| Six-factor grouped intercept | Conditional low-dimensional projection; not JKP132 residual alpha |','| Expanding ridge10 / PCA5-ridge10 | Prior36+months fit coefficients/scaling/PCA; contemporaneous factor realizations reconstruct the current difference |','| Fixed allocation | Prior-history weights; common JKP-only baseline and identical policy for both LLM pools and grammar |','',*md_table(six_table,[('Pool','pool'),('Grouped intercept, pp/year','grouped'),('Pointwise99% interval, pp','ci'),('Diagnostic raw p','raw')]),'','[Full attribution audit](visual_tables/six_factor_and_unidentified_full_audit.csv). Block-specific fitted intercepts and the full-sample OLS intercept are different estimators; the table reports the grouped quantity. These tests are outside the primary family.','',*md_table(recon_table,[('Pool','pool'),('Projection','model'),('Monthly RMSE, pp','rmse'),('Annualized residual mean, pp','residual')]),'','[Full reconstruction audit](visual_tables/reconstruction_full_audit.csv). These36-month2022–2024 reconstructions use contemporaneous factor realizations. They are not tradable forecasts, and their residual means are not unrestricted-alpha p-values.','','## Fixed gross-factor allocation diagnostic','','![Common allocator certainty-equivalent increments](visual_figures/allocation_diagnostic.png)','',*md_table(alloc_table,[('Added sleeve','pool'),('CE change, bp/year','ce'),('Mean sleeve exposure in input units','weight')]),'','[Full allocator audit](visual_tables/allocation_full_audit.csv) · [Increment audit](visual_tables/allocation_increment_full_audit.csv). The common JKP-only certainty equivalent is0.374148% annually under risk aversion10. The grammar sleeve receives zero weight; both LLM sleeves slightly lower this chosen diagnostic in this realization. This does not establish what every allocator could achieve. Exposures are weights in original input-return units, not stand-alone recommendations.','','The fixed policy uses expanding36-month initialization, covariance diagonal shrinkage0.5, past-volatility scaling to0.10, nonnegative agent exposure, signed factor weights and L1 risk-budget cap1. Agent internal10bp costs are included; factor internal turnover, financing and allocation-change costs are absent. This is neither a net deployable fund nor a claim about the best attainable frontier.','','## Calibration and claim boundaries','','Monthly inference uses the existing N72 validation,2000 replications per cell, with all18 zero-effect cells retained. Mean-contrast nominal99% coverage ranged98.6–99.2%; six-factor coverage98.4–99.35%. Some coverage is below nominal. Approximate independent normal block estimates and Monte Carlo uncertainty remain; no exact real-world1% guarantee or transfer of nativeN238/963 calibration is claimed. See [monthly validation reference](../efs_monthly_inference_reference.json).','','Libraries and trajectories share a historical market path. These conditional comparisons do not integrate all search uncertainty, create independent market histories, establish pristine model/data snapshots, or reproduce every original-paper experiment. Frozen v1’s six-case family remains separate and unchanged. All69 papers retain distinct evidence/gaps. Independent human source review and the final whole-study archive remain external or pending.','','## Evidence and reproduction','','[Report validation](validation.json) · [Lineage](lineage.json) · [Completed EFS analysis](../efs_pooled_analysis/completion.json) · [Source review packet](../SOURCE_REVIEW_PACKET.md).','','The builder verifies completed public/private/source/pool hashes, re-accounts24 pool paths, recomputes42 performance rows,2primary contrasts,8fee differences,2six-factor projections and4reconstruction residual summaries, and checks6allocator summaries and the partial-family correction. It writes no source/model result, fits no new native search/model and makes no API call. The [no-image report](REPORT.md) contains the same tables and definitions.','','From the canonical checkout, with no existing report directory:','','```bash','/nfs/roberts/project/pi_btk22/zc362/environments/venvs/alpha-agent-replication-py312-20260813/bin/python scripts/build_efs_pooled_report_v2.py','```','','Inspect and preserve any existing complete or partial report before regeneration.']
    for group in GROUPS:
        ordered_wealth = [next(r['ending_wealth'] for r in performance if r['group']==group and r['mode']=='causal_discovery_gated' and r['cost_bps']==c) for c in [0,10,25,50]]
        if not all(a>b for a,b in zip(ordered_wealth,ordered_wealth[1:])):raise ValueError('Fee interpretation requires decreasing absolute wealth')
    zero_gpt=next(r['full_sample_annualized_monthly_mean_increment'] for r in cost_rows if r['backend']=='gpt41' and r['cost_bps']==0)
    zero_deep=next(r['full_sample_annualized_monthly_mean_increment'] for r in cost_rows if r['backend']=='deepseek_v3' and r['cost_bps']==0)
    position=lines.index('## What the JKP diagnostics can identify')
    lines[position:position]=[f"At zero costs, the mean increments are {100*zero_gpt:+.3f}pp/year for GPT-4.1 and {100*zero_deep:+.3f}pp/year for DeepSeek. The relative gap grows along this fee ladder because costs reduce grammar returns more than model-pool returns in this sample. Each pool's absolute ending wealth decreases as costs rise. The frozen10bp comparison remains primary; no fee was selected from the better-looking result.", ""]
    lines[4:4]=['This is the frozen paper-guided US50 implementation; an attributable author implementation was not recovered. Current served models are disclosed substitutions, including DeepSeek-V3-0324/SiliconFlow. Exact replay and account conformance validate this implementation, not the original paper across its markets, models and ablations.', '']
    text='\n'.join(lines)+'\n';(OUT/'VISUAL_REPORT.md').write_text(text);(OUT/'REPORT.md').write_text(re.sub(r'!\[[^]]*\]\([^)]*\)\n?','',text))
    atomic_json(OUT/'lineage.json',{'analysis_completion_sha256':sha256(SOURCE/'completion.json'),'executed_analyzer_sha256':done['script_sha256'],'collector_completion_sha256':latest['completion_sha256'],'collector_snapshot':latest['snapshot'],'builder_sha256':sha256(Path(__file__)),'helper_sha256':sha256(ROOT/'scripts/build_quanta_results_report_v2.py'),'pool_bindings':bindings,'private_output_hashes':done['private_outputs'],'new_model_calls':0,'no_frozen_results_overwritten':True})
    atomic_json(OUT/'contract.json',{'primary_frequency':12,'primary_months':72,'account_days':1510,'groups':4,'block_months':18,'primary_cost_bps':10,'matched_trajectory_count':3,'grammar_seeds':[101,102,103],'available_project_cases':3,'project_correction_denominator':4,'strict_alpha_unavailable':True,'unrestricted134_parameter_OLS_identified':False,'regularized_projection_is_tradable_forecast':False,'allocation_is_net_deployable_fund':False})
    images=[]
    for name in ['causal_wealth','primary_intervals','fee_sensitivity','allocation_diagnostic']:
        p=OUT/'visual_figures'/(name+'.png');a=np.asarray(Image.open(p).convert('RGB'))
        if a.std()<10:raise ValueError('Blank figure')
        images.append({'path':str(p.relative_to(OUT)),'sha256':sha256(p),'shape':list(a.shape),'pixel_std':float(a.std())})
    def lum(color):
        v=np.array([int(color[i:i+2],16)/255 for i in (1,3,5)]);v=np.where(v<=.04045,v/12.92,((v+.055)/1.055)**2.4);return float(v@np.array([.2126,.7152,.0722]))
    contrast=(lum(BG)+.05)/(lum(FG)+.05)
    if contrast<7:raise ValueError('Insufficient contrast')
    for target in re.findall(r'\]\(([^)]+)\)',text):
        if target!='validation.json' and not (OUT/target).is_file():raise ValueError('Broken report link: '+target)
    for m in re.finditer(r'!\[[^]]*\]\([^)]*\)',text):
        if not text[m.end():].lstrip().startswith('|'):raise ValueError('Figure/table pairing absent')
    if '![' in (OUT/'REPORT.md').read_text():raise ValueError('Image in no-image report')
    atomic_json(OUT/'validation.json',{'status':'numeric_layout_pass_assistant_visual_review_pending','independent_pool_paths_reaccounted':24,'performance_rows_recomputed':42,'primary_contrasts_recomputed':2,'six_factor_diagnostics_recomputed':2,'fee_differences_recomputed':8,'reconstruction_residual_summaries_checked':4,'allocation_summaries_checked':6,'identical_common_allocator_baseline':True,'project_denominator':4,'available_project_cases':3,'text_contrast_ratio':contrast,'figure_text_within_canvas':True,'links_exist':True,'figure_table_pairing':True,'no_image_report_pass':True,'figures':images,'human_attestation':None,'outputs':{str(p.relative_to(OUT)):sha256(p) for p in OUT.rglob('*') if p.is_file() and p.name!='validation.json'}})
    print('EFS_REPORT_NUMERIC_LAYOUT_PASS',contrast,flush=True)
if __name__=='__main__':main()
