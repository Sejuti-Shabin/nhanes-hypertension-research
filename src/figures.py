"""Publication-style vector PDF and 300-DPI PNG, always from calculated files."""
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from matplotlib.ticker import FixedLocator, FuncFormatter
from data import ROOT,OUT
from validate import assert_current_validation

FIG=ROOT/'figures'
COLOR='#17656a';OTHER='#b16b39'
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.titlesize':13,
 'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42,'ps.fonttype':42})

def save(fig,name):
    FIG.mkdir(exist_ok=True)
    for ext in ['png','pdf']:fig.savefig(FIG/f'{name}.{ext}',dpi=300,bbox_inches='tight')
    plt.close(fig)

def run():
    validation=assert_current_validation()
    if not all(v['passed'] for v in validation.values()):raise ValueError('Validation failed')
    captions=[]
    flow=pd.read_csv(OUT/'sample_flow.csv')
    fig,ax=plt.subplots(figsize=(8,10));ax.set_xlim(0,1);ax.set_ylim(0,1);ax.axis('off')
    ys=np.linspace(.92,.12,len(flow))
    for i,((_,r),y) in enumerate(zip(flow.iterrows(),ys)):
        patch=FancyBboxPatch((.10,y-.035),.80,.075,boxstyle='round,pad=0.012',facecolor='#edf5f5',edgecolor=COLOR)
        ax.add_patch(patch);ax.text(.5,y,f'{r.stage}\nn = {r.n:,}',ha='center',va='center',fontsize=11)
        if i:
            ax.annotate('',xy=(.5,y+.05),xytext=(.5,ys[i-1]-.05),arrowprops={'arrowstyle':'->','color':COLOR})
            ax.text(.93,(y+ys[i-1])/2,f'−{r.excluded_since_prior:,}',ha='center',va='center',fontsize=10)
    ax.set_title('Participant selection · NHANES 2017–2018',pad=16)
    ax.text(.5,.015,'Counts are unweighted. Hypertension: ≥130/80 or current medication.\nKnown current medication establishes a case even without BP.',ha='center',fontsize=10)
    save(fig,'participant_flow')
    captions.append('Figure 1. Unweighted sequential selection counts. Revised primary eligibility admits medication-confirmed cases without BP; BP completeness is a sensitivity. The classifiable stage includes only records with resolved operational status. The last two stages distinguish outcome/exposure completeness from covariate completeness.')
    desc=pd.read_csv(OUT/'descriptive.csv');a=desc[(desc.estimand=='Awareness prevalence')&desc.group.isin(['Insured','Uninsured'])]
    fig,ax=plt.subplots(figsize=(7,4.5))
    for i,(_,r) in enumerate(a.iterrows()):
        ax.errorbar(i,100*r.estimate,yerr=[[100*(r.estimate-r.ci_low)],[100*(r.ci_high-r.estimate)]],fmt='o',markersize=9,color=[COLOR,OTHER][i],capsize=5)
        ax.text(i,100*r.ci_high+4,f'n = {r.n:,}',ha='center',fontsize=10)
    ax.set_xticks([0,1],a.group);ax.set_ylim(0,100);ax.set_ylabel('Reported hypertension awareness (%)')
    ax.set_title('Crude weighted awareness by insurance')
    ax.grid(axis='y',alpha=.18);fig.tight_layout();save(fig,'awareness_by_insurance')
    captions.append('Figure 2. Survey-weighted awareness in the primary hypertension domain by current insurance. Error bars are 95% beta/Korn–Graubard-type intervals from R survey; the plotted insurance estimates meet numeric NCHS screening. Unweighted n is outcome-specific. These are unadjusted percentages.')
    reg=pd.read_csv(OUT/'regression.csv');a=reg[(reg.model=='M3')&(reg.term!='(Intercept)')].iloc[::-1]
    labels={'uninsured':'Uninsured vs insured','age10':'Age, per 10 years','sexMale':'Male vs female','pir':'PIR, per 1 unit'}
    for t in a.term:
        if t.startswith('race'):labels[t]=t[4:]+' vs White'
        if t.startswith('education'):labels[t]=t[9:]+' vs college graduate'
    fig,ax=plt.subplots(figsize=(10,7.5));y=np.arange(len(a))
    ax.errorbar(a.odds_ratio,y,xerr=np.vstack([a.odds_ratio-a.ci_low,a.ci_high-a.odds_ratio]),fmt='o',capsize=3,color=COLOR)
    ax.set_yticks(y,[labels.get(t,t) for t in a.term]);ax.axvline(1,color='gray',ls='--',lw=1)
    ax.set_xscale('log');ax.xaxis.set_major_locator(FixedLocator([.1,.2,.5,1,2,5,10]));ax.xaxis.set_major_formatter(FuncFormatter(lambda v,pos: f'{v:g}'));ax.set_xlabel('Adjusted odds ratio (95% CI; log scale)')
    ax.set_title(f'Awareness · fully adjusted model\nn = {int(a.n.iloc[0]):,}; residual design df = {int(a.residual_df.iloc[0])}')
    ax.grid(axis='x',alpha=.18);fig.tight_layout();save(fig,'adjusted_odds_ratios')
    captions.append('Figure 3. Model 3 jointly adjusts for insurance, age, sex, six race/ethnicity categories, four education categories, and continuous PIR. Intervals use R svyglm residual design df (3). Covariate estimates are model coefficients, not identified causal effects; ORs are not risk ratios.')
    marginal=pd.read_csv(OUT/'marginal_probabilities.csv');a=marginal.iloc[:2]
    fig,ax=plt.subplots(figsize=(7,4.5));v=a.estimate.to_numpy()*100
    ax.errorbar([0,1],v,yerr=np.vstack([v-a.ci_low.to_numpy()*100,a.ci_high.to_numpy()*100-v]),fmt='o',markersize=9,capsize=5,color=COLOR)
    ax.set_xticks([0,1],a.estimand);ax.set_ylim(0,100);ax.set_ylabel('Standardized awareness probability (%)')
    ax.set_title('Weighted standardization over Model 3 cases');ax.grid(axis='y',alpha=.18)
    fig.tight_layout();save(fig,'adjusted_probabilities')
    captions.append('Figure 4. Model 3 predictions averaged over the weighted complete-case covariate distribution after setting insurance to each status. Joint Taylor linearization includes coefficient and empirical-distribution uncertainty; primary marginal intervals use Model 3 residual df, matching coefficient inference, with bounded logit probability intervals. Descriptive model standardization does not identify an insurance intervention effect.')
    selected=['M3','threshold140','measured130','measured140','readings23','two_readings','age20_59','omit_pir']
    labels2=['Primary 130/80 + medication','140/90 + medication','Measured-only 130/80','Measured-only 140/90','Available readings 2–3','At least two readings','Ages 20–59','Omit PIR']
    a=reg[(reg.term=='uninsured')&reg.model.isin(selected)].set_index('model').loc[selected]
    fig,ax=plt.subplots(figsize=(10,6));y=np.arange(len(a))[::-1]
    ax.errorbar(a.odds_ratio,y,xerr=np.vstack([a.odds_ratio-a.ci_low,a.ci_high-a.odds_ratio]),fmt='o',capsize=3,color=COLOR)
    ax.set_yticks(y,labels2);ax.axvline(1,color='gray',ls='--',lw=1);ax.set_xscale('log');ax.xaxis.set_major_locator(FixedLocator([.1,.2,.5,1,2,5,10]));ax.xaxis.set_major_formatter(FuncFormatter(lambda v,pos: f'{v:g}'))
    ax.set_xlabel('Uninsured versus insured odds ratio (95% CI; log scale)');ax.set_title('Sensitivity comparisons (original and post-review)')
    ax.grid(axis='x',alpha=.18);fig.tight_layout();save(fig,'sensitivity_comparisons')
    captions.append('Figure 5. Selected secondary estimates, including reviewer-directed eligibility revisions; no multiplicity adjustment or significance-driven selection. Case definitions alter populations. The measured-only 140/90 point estimate reverses direction, with substantial uncertainty. Each interval uses its model-specific residual design df.')
    (FIG/'CAPTIONS.md').write_text('# Figure captions\n\n'+'\n\n'.join(captions)+'\n')
    print('Created five figure pairs (300-DPI PNG + vector PDF)')

if __name__=='__main__':run()
