"""Taylor-linearized NHANES ratios and logistic scores; validated against R survey.

statsmodels supplies ONLY weighted score point estimates, never reported SE.
Full positive-weight exam design contributes zero influence outside each domain.
"""
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.special import expit, logit
from scipy.stats import t
from data import CATEGORIES

SPECS={'M1':['uninsured'],'M2':['uninsured','age10','sex'],
       'M3':['uninsured','age10','sex','race','education','pir']}

def matrix(d,variables):
    parts=[pd.Series(1.,index=d.index,name='Intercept')]
    for v in variables:
        if v in CATEGORIES:
            for level in CATEGORIES[v][1:]:parts.append(d[v].eq(level).astype(float).rename(v+'_'+level))
        else: parts.append(d[v].astype(float).rename(v))
    return pd.concat(parts,axis=1)

def complete(d,domain,variables,outcome='awareness'):
    keep=domain&d[outcome].notna()&d.WTMEC2YR.gt(0)
    for v in variables: keep &= d[v].notna()
    return keep

def covariance(d,influence):
    a=np.asarray(influence)
    if a.ndim==1:a=a[:,None]
    f=pd.DataFrame(a,index=d.index)
    f['stratum']=d.SDMVSTRA;f['psu']=d.SDMVPSU
    totals=f.groupby(['stratum','psu'],observed=True)[list(range(a.shape[1]))].sum()
    cov=np.zeros((a.shape[1],a.shape[1]));df=0
    for _,g in totals.groupby(level=0):
        m=len(g)
        if m<2:raise ValueError('Lonely PSU: inference refused')
        z=g.to_numpy()-g.to_numpy().mean(axis=0)
        cov+=m/(m-1)*z.T@z;df+=m-1
    return cov,df

def ratio(d,y,domain):
    y=pd.Series(y,index=d.index,dtype=float)
    keep=domain&y.notna();w=d.WTMEC2YR.where(keep,0).to_numpy()
    n=int(keep.sum());total=w.sum()
    if not total:return dict(n=0,estimate=np.nan,se=np.nan,ci_low=np.nan,ci_high=np.nan,design_df=np.nan)
    values=y.fillna(0).to_numpy();p=np.dot(w,values)/total
    cov,df=covariance(d,w*(values-p)/total);se=np.sqrt(cov[0,0]);q=t.ppf(.975,df)
    return dict(n=n,estimate=float(p),se=float(se),ci_low=float(p-q*se),ci_high=float(p+q*se),design_df=df)

def fit(d,domain,variables,model,do_diagnostics=True):
    keep=complete(d,domain,variables)
    sub=d.loc[keep];X=matrix(sub,variables);x=X.to_numpy();y=sub.awareness.to_numpy();w=sub.WTMEC2YR.to_numpy();w=w/w.mean()
    if len(np.unique(y))<2:raise ValueError('Outcome constant')
    if np.linalg.matrix_rank(x)!=x.shape[1]:raise ValueError('Rank-deficient model')
    res=sm.GLM(y,x,family=sm.families.Binomial(),freq_weights=w).fit(maxiter=200,tol=1e-11)
    if not res.converged:raise ValueError('Nonconvergence')
    beta=np.asarray(res.params);p=expit(x@beta)
    bread=(x.T*(w*p*(1-p)))@x
    scores=x*(w*(y-p))[:,None]
    inf=np.linalg.solve(bread,scores.T).T
    full=np.zeros((len(d),len(beta)));full[keep.to_numpy()]=inf
    cov,design_df=covariance(d,full)
    residual_df=design_df-(len(beta)-1)
    if residual_df<=0:raise ValueError('Nonpositive regression residual design df')
    se=np.sqrt(np.diag(cov));crit=t.ppf(.975,residual_df)
    table=pd.DataFrame({'model':model,'term':X.columns,'beta':beta,'se':se,
        'odds_ratio':np.exp(beta),'ci_low':np.exp(beta-crit*se),'ci_high':np.exp(beta+crit*se),
        't':beta/se,'p':2*t.sf(np.abs(beta/se),residual_df),
        'n':len(sub),'events':int(y.sum()),'design_df':design_df,'residual_df':residual_df})
    h=w*p*(1-p)*np.einsum('ij,jk,ik->i',x,np.linalg.inv(bread),x)
    diag={'model':model,'n':len(sub),'events':int(y.sum()),'nonevents':int((1-y).sum()),
          'converged':bool(res.converged),'rank':len(beta),'design_df':design_df,'residual_df':residual_df,
          'max_score':float(np.abs(scores.sum(axis=0)).max()),'bread_condition':float(np.linalg.cond(bread)),
          'covariance_min_eigenvalue':float(np.linalg.eigvalsh(cov).min()),
          'min_prediction':float(p.min()),'max_prediction':float(p.max()),'max_weighted_leverage':float(h.max()),
          'largest_leverage_SEQN':int(sub.iloc[np.argmax(h)].SEQN),
          'weights_normalized_by_mean':True}
    cells=[]
    if do_diagnostics:
        for v in variables:
            if v in CATEGORIES or v in ['uninsured','no_usual_care']:
                for level,g in sub.groupby(v,observed=True):
                    cells.append({'model':model,'variable':v,'level':str(level),'n':len(g),'aware_n':int(g.awareness.sum()),'unaware_n':int((1-g.awareness).sum())})
    return table,diag,{'keep':keep,'variables':variables,'beta':beta,'cov':cov,'influence':full,'X':x,'weight':w,'cells':cells,'names':X.columns.tolist(),'leverage':h,'prediction':p}

def standardized(d,fitinfo):
    """Joint linearization: coefficient uncertainty AND empirical covariate mix.

    Targets descriptive standardization over the complete-case hypertensive domain.
    R independently recomputes this influence and applies survey::svytotal.
    """
    keep=fitinfo['keep'];sub=d.loc[keep];w=sub.WTMEC2YR.to_numpy();total=w.sum()
    means=[];influences=[]
    for uninsured in [0.,1.]:
        z=sub.copy();z['uninsured']=uninsured;x=matrix(z,fitinfo['variables']).to_numpy();p=expit(x@fitinfo['beta'])
        mu=np.dot(w,p)/total
        grad=np.sum((w*p*(1-p))[:,None]*x,axis=0)/total
        influence=fitinfo['influence']@grad
        influence[keep.to_numpy()]+=w*(p-mu)/total
        means.append(mu);influences.append(influence)
    influences.append(influences[1]-influences[0]);means.append(means[1]-means[0])
    rows=[]
    for label,mu,inf in zip(['Insured','Uninsured','Uninsured minus insured'],means,influences):
        cov,df=covariance(d,inf);se=np.sqrt(cov[0,0]);reference_df=df-(len(fitinfo['beta'])-1);q=t.ppf(.975,reference_df)
        low,high=mu-q*se,mu+q*se
        method='Taylor t difference'
        if label!='Uninsured minus insured':
            low,high=expit(logit(mu)+np.array([-1,1])*q*se/(mu*(1-mu)))
            method='logit-transformed Taylor t'
        rows.append({'estimand':label,'estimate':mu,'se':se,'ci_low':low,'ci_high':high,'design_df':df,'inference_df':reference_df,'ci_method':method,'n':len(sub)})
    return pd.DataFrame(rows)

def jackknife_influence(d,domain,variables,base):
    """Delete-one PSU, double its stratum peer; report coefficient shifts, not primary SE."""
    rows=[];base_beta=base['beta'];j=base['names'].index('uninsured')
    for (stratum,psu),_ in d.groupby(['SDMVSTRA','SDMVPSU']):
        z=d.copy();same=z.SDMVSTRA.eq(stratum)
        z.loc[same&z.SDMVPSU.eq(psu),'WTMEC2YR']=0
        z.loc[same&~z.SDMVPSU.eq(psu),'WTMEC2YR']*=2
        # Fit score only: preserve original design; dropped weight does not remove a PSU.
        keep=complete(z,domain,variables);sub=z.loc[keep];x=matrix(sub,variables).to_numpy();w=sub.WTMEC2YR/sub.WTMEC2YR.mean()
        try:
            r=sm.GLM(sub.awareness.to_numpy(),x,family=sm.families.Binomial(),freq_weights=w).fit(maxiter=200)
            rows.append({'stratum':stratum,'removed_psu':psu,'converged':bool(r.converged),'uninsured_beta':r.params[j],
                         'delta_uninsured_beta':r.params[j]-base_beta[j],'max_abs_coefficient_shift':float(np.max(np.abs(r.params-base_beta)))})
        except Exception as e:rows.append({'stratum':stratum,'removed_psu':psu,'converged':False,'error':str(e)})
    return pd.DataFrame(rows)
