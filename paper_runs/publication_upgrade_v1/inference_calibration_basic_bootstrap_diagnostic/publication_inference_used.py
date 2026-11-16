"""Paired economic bounds and dependence-aware inference with explicit estimands.

Sources: Politis & Romano (1994), DOI 10.1080/01621459.1994.10476870;
Newey & West (1987), DOI 10.2307/1913610; equivalence via Schuirmann (1987),
DOI 10.1007/BF01068419. Bootstrap inference is asymptotic, not an exact test.
"""
from __future__ import annotations
import numpy as np
from scipy.stats import norm


def stationary_indices(n, replicates, mean_block, rng):
    if n<2 or replicates<1 or not 1<=mean_block<=n:raise ValueError('Invalid bootstrap dimensions')
    result=np.empty((replicates,n),dtype=int);result[:,0]=rng.integers(n,size=replicates)
    for t in range(1,n):
        restart=rng.random(replicates)<1/mean_block
        result[:,t]=np.where(restart,rng.integers(n,size=replicates),(result[:,t-1]+1)%n)
    return result


def _bounds(estimate,draws,frequency,threshold):
    centered=np.asarray(draws)-estimate
    if not len(centered) or not np.isfinite(centered).all():raise ValueError('Invalid bootstrap distribution')
    lo95,hi95=estimate-np.quantile(centered,[.975,.025])
    lo90,hi90=estimate-np.quantile(centered,[.95,.05])
    se=float(np.std(draws,ddof=1))*frequency;effect=estimate*frequency
    p=float((1+np.sum(np.abs(centered)>=abs(estimate)))/(len(draws)+1))
    return {'annualized_arithmetic_effect':float(effect),'ci95_low':float(lo95*frequency),'ci95_high':float(hi95*frequency),'ci90_low':float(lo90*frequency),'ci90_high':float(hi90*frequency),'one_sided95_upper':float(hi90*frequency),'bootstrap_p_two_sided':p,'bootstrap_se_annualized':se,'economic_margin_annualized':float(threshold),'equivalent_within_margin_tost5':bool(lo90*frequency>-threshold and hi90*frequency<threshold),'rules_out_positive_margin_one_sided5':bool(hi90*frequency<threshold),'mde80_normal_approx_annualized':float((norm.ppf(.975)+norm.ppf(.8))*se),'power_at_margin_normal_approx':float(norm.cdf(-norm.ppf(.975)-threshold/se)+1-norm.cdf(norm.ppf(.975)-threshold/se)) if se>1e-14 else None}


def paired_effect(left,right,frequency=12,mean_block=6,replicates=4999,seed=20260907,threshold=.02):
    left=np.asarray(left,float);right=np.asarray(right,float)
    if left.ndim!=1 or left.shape!=right.shape or len(left)<12 or not np.isfinite(np.c_[left,right]).all():raise ValueError('At least 12 aligned finite paired observations required')
    difference=left-right;rng=np.random.default_rng(seed);indexes=stationary_indices(len(left),replicates,mean_block,rng);draws=difference[indexes].mean(axis=1)
    result=_bounds(float(difference.mean()),draws,frequency,threshold)
    result.update(observations=len(left),frequency=frequency,mean_block=mean_block,bootstrap_replicates=replicates,seed=seed,estimand='annualized mean paired return difference; confidence interval is not a CAGR interval')
    if np.all(left>-1) and np.all(right>-1):result['observed_cagr_difference']=float(np.expm1(np.log1p(left).mean()*frequency)-np.expm1(np.log1p(right).mean()*frequency))
    return result


def _design(y,factors):
    y=np.asarray(y,float);x=np.asarray(factors,float)
    if x.ndim==1:x=x[:,None]
    if y.ndim!=1 or x.ndim!=2 or len(y)!=len(x) or not np.isfinite(np.c_[y,x]).all():raise ValueError('Unaligned or nonfinite regression data')
    design=np.c_[np.ones(len(y)),x]
    if len(y)<=design.shape[1]+2 or np.linalg.matrix_rank(design)<design.shape[1]:raise ValueError('Unrestricted factor alpha is not identified with this sample/rank')
    return y,design


def ols_alpha(y,factors,frequency=12,hac_lags=3):
    y,x=_design(y,factors);n,k=x.shape;beta=np.linalg.lstsq(x,y,rcond=None)[0];residual=y-x@beta
    score=x*residual[:,None];meat=score.T@score
    lags=min(int(hac_lags),n-1)
    for lag in range(1,lags+1):
        gamma=score[lag:].T@score[:-lag];meat+=(1-lag/(lags+1))*(gamma+gamma.T)
    inverse=np.linalg.inv(x.T@x);cov=inverse@meat@inverse*(n/(n-k));se=float(np.sqrt(max(cov[0,0],0)));alpha=float(beta[0]);t=alpha/se if se>1e-14 else (0. if abs(alpha)<1e-14 else np.sign(alpha)*np.inf)
    return {'annualized_alpha':alpha*frequency,'hac_se_annualized':se*frequency,'hac_t':float(t),'hac_p_normal':float(2*norm.sf(abs(t))),'observations':n,'factor_count':k-1,'design_rank':int(np.linalg.matrix_rank(x)),'hac_lags':lags,'betas':beta[1:].tolist(),'residual':residual,'fitted':x@beta}


def refitted_alpha_bootstrap(y,factors,frequency=12,mean_block=6,replicates=1999,seed=20260907,threshold=.02):
    y,design=_design(y,factors);estimate=float(np.linalg.lstsq(design,y,rcond=None)[0][0]);indexes=stationary_indices(len(y),replicates,mean_block,np.random.default_rng(seed));draws=[];invalid=0
    for idx in indexes:
        x=design[idx];yy=y[idx]
        if np.linalg.matrix_rank(x)<x.shape[1]:invalid+=1;continue
        # Refit every coefficient jointly after resampling dates; never just resample a precomputed residual.
        draws.append(float(np.linalg.lstsq(x,yy,rcond=None)[0][0]))
    if len(draws)<.95*replicates:raise ValueError('Too many rank-deficient bootstrap draws')
    result=_bounds(estimate,draws,frequency,threshold);result.update(observations=len(y),factor_count=design.shape[1]-1,mean_block=mean_block,bootstrap_replicates=replicates,rank_deficient_draws=invalid,seed=seed,estimator_refitted_every_draw=True,estimand='intercept conditional on this specified factor model; not unrestricted JKP132 unless all 132 factors are identified')
    return result


def chronological_projection(y,factors,min_train=36,penalty=10.,components=None):
    """Expanding training-only ridge/PCA reconstruction; intentionally no alpha p-value."""
    y=np.asarray(y,float);x=np.asarray(factors,float)
    if y.ndim!=1 or x.ndim!=2 or len(y)!=len(x) or len(y)<=min_train or not np.isfinite(np.c_[y,x]).all():raise ValueError('Invalid chronological data')
    if penalty<=0:raise ValueError('Positive ridge penalty required')
    predictions=np.full(len(y),np.nan)
    for end in range(min_train,len(y)):
        xx=x[:end];yy=y[:end];mean=xx.mean(axis=0);sd=xx.std(axis=0);sd=np.where(sd>1e-12,sd,1.);z=(xx-mean)/sd;current=(x[end]-mean)/sd
        if components is not None:
            if not 1<=components<min(end,x.shape[1]):raise ValueError('Invalid PCA rank')
            basis=np.linalg.svd(z,full_matrices=False)[2][:components].T;z=z@basis;current=current@basis
        ym=yy.mean();centered=yy-ym
        # Dual solve is equivalent and stable when the number of factors exceeds history.
        if z.shape[1]>len(z):beta=z.T@np.linalg.solve(z@z.T+penalty*np.eye(len(z)),centered)
        else:beta=np.linalg.solve(z.T@z+penalty*np.eye(z.shape[1]),z.T@centered)
        predictions[end]=ym+current@beta
    residual=y[min_train:]-predictions[min_train:]
    return {'predictions':predictions,'residual':residual,'evaluation_start_index':min_train,'evaluation_observations':len(residual),'mean_residual':float(residual.mean()),'rmse':float(np.sqrt(np.mean(residual**2))),'label':'regularized chronological reconstruction diagnostic; no unrestricted spanning-alpha inference','penalty':penalty,'components':components}


def holm_adjust(pvalues):
    p=np.asarray(pvalues,float)
    if not np.isfinite(p).all() or ((p<0)|(p>1)).any():raise ValueError('Invalid p-values')
    order=np.argsort(p);adjusted=np.empty(len(p));adjusted[order]=np.minimum(1,np.maximum.accumulate((len(p)-np.arange(len(p)))*p[order]));return adjusted
