"""Create full design frame, tables and Python comparison estimates."""
import json
import numpy as np
import pandas as pd
from data import ROOT,OUT,load,prepare,eligible,dictionary,CATEGORIES
from survey import SPECS,ratio,fit,complete,standardized,jackknife_influence


def run():
    OUT.mkdir(exist_ok=True)
    raw,provenance=load()
    d_all=prepare(raw)
    d=d_all.loc[d_all.WTMEC2YR.gt(0)&d_all.RIDSTATR.eq(2)].reset_index(drop=True)
    if d[['SDMVSTRA','SDMVPSU']].isna().any().any():raise ValueError('Missing design keys')
    domain=eligible(d)
    analytic=domain&d.awareness.notna()&d.uninsured.notna()
    m3keep=complete(d,analytic,SPECS['M3'])
    flow=[]
    age=d_all.RIDAGEYR.between(20,64)
    exam=age&d_all.RIDSTATR.eq(2)&d_all.WTMEC2YR.gt(0)
    bp=exam&d_all.sbp.notna()&d_all.dbp.notna()
    stages=[('Initial DEMO_J respondents',pd.Series(True,index=d_all.index)),('Age 20–64',age),
            ('Examined, positive MEC weight',exam),('Ascertainment classifiable (BP or medication)',exam&d_all.hypertension_130.notna()),
            ('Operational hypertension eligible',eligible(d_all)),
            ('Valid awareness and insurance',eligible(d_all)&d_all.awareness.notna()&d_all.uninsured.notna())]
    previous=None
    for label,mask in stages:
        n=int(mask.sum());flow.append({'stage':label,'n':n,'excluded_since_prior':0 if previous is None else previous-n});previous=n
    flow.append({'stage':'Model 3 complete covariates','n':int(m3keep.sum()),'excluded_since_prior':previous-int(m3keep.sum())})
    pd.DataFrame(flow).to_csv(OUT/'sample_flow.csv',index=False)
    # Export all positive-weight examined persons, not just analytic adults.
    d['domain_primary']=domain.astype(int);d['domain_analytic']=analytic.astype(int);d['domain_m3']=m3keep.astype(int)
    d.to_csv(OUT/'design_frame.csv',index=False)
    dictionary().to_csv(ROOT/'data_dictionary.csv',index=False)
    (OUT/'provenance.json').write_text(json.dumps(provenance,indent=2))
    if not (ROOT/'data/source_manifest.json').exists():
        (ROOT/'data/source_manifest.json').write_text(json.dumps(provenance,indent=2))
    cleaning={
       'merge_rows':len(raw),'full_positive_exam_design_n':len(d),
       'n_strata':d.SDMVSTRA.nunique(),'n_psus':d.groupby(['SDMVSTRA','SDMVPSU']).ngroups,
       'age20_64_exam_n':int((d.RIDAGEYR.between(20,64)).sum()),
       'structural_medication_no_all':int(d_all.medication_structural_no.sum()),
       'age20_64_unknown_medication_n':int((d.RIDAGEYR.between(20,64)&d.medication.isna()).sum()),
       'unknown_case_despite_complete_BP_n':int((d.RIDAGEYR.between(20,64)&d.sbp.notna()&d.dbp.notna()&d.hypertension_130.isna()).sum()),
       'DBP_zero_readings_retained':int(d_all[[f'BPXDI{i}' for i in range(1,4)]].eq(0).sum().sum()),
       'current_medication_without_awareness_yes':int((d.medication.eq(1)&~d.awareness.eq(1)).sum()),
       'weight_note':'Normalize tiny XPORT decoded zero in all numeric fields, retain positive MEC examined design',
       'reading_note':'Separate available-reading means of first 3; both required for primary domain',
    }
    (OUT/'cleaning_log.json').write_text(json.dumps(cleaning,indent=2,default=int))
    miss=[]
    for label,mask in [('Target examined',d.RIDAGEYR.between(20,64)),('Hypertension eligible',domain),('Outcome/exposure complete',analytic)]:
        for v in ['sbp','dbp','medication','awareness','uninsured','RIDAGEYR','sex','race','education','pir','no_usual_care']:
            miss.append({'population':label,'variable':v,'n':int(mask.sum()),'missing_n':int(d.loc[mask,v].isna().sum()),
                         'missing_weighted_fraction':ratio(d,d[v].isna().astype(float),mask)['estimate']})
    pd.DataFrame(miss).to_csv(OUT/'missingness.csv',index=False)
    descriptive=[]
    target=d.RIDAGEYR.between(20,64)
    descriptive.append({'estimand':'Hypertension prevalence','group':'All','variable':'hypertension_130',**ratio(d,d.hypertension_130,target)})
    for label,mask in [('All',domain),('Insured',domain&d.uninsured.eq(0)),('Uninsured',domain&d.uninsured.eq(1))]:
        descriptive.append({'estimand':'Awareness prevalence','group':label,'variable':'awareness',**ratio(d,d.awareness,mask)})
    pd.DataFrame(descriptive).to_csv(OUT/'python_descriptive.csv',index=False)
    table1=[]
    for label,value in [('Insured',0),('Uninsured',1)]:
        group=analytic&d.uninsured.eq(value)
        for v in ['RIDAGEYR','pir','sbp','dbp','awareness']:
            table1.append({'insurance':label,'variable':v,'level':'Mean' if v!='awareness' else 'Aware','total_group_n':int(group.sum()),**ratio(d,d[v],group)})
        for v in ['sex','race','education','pir_group']:
            for level in CATEGORIES[v]:
                y=d[v].eq(level).astype(float).where(d[v].notna())
                table1.append({'insurance':label,'variable':v,'level':level,'total_group_n':int(group.sum()),'category_n':int((group&d[v].eq(level)).sum()),**ratio(d,y,group)})
    pd.DataFrame(table1).to_csv(OUT/'python_table1.csv',index=False)
    results=[];diags=[];cells=[];specrows=[];covariances=[]
    def model(ds,mask,variables,name,kind):
        ds=ds.copy();mask=mask&ds.awareness.notna()
        if 'uninsured' in variables:mask &= ds.uninsured.notna()
        tab,diag,info=fit(ds,mask,variables,name)
        results.append(tab);diags.append(diag);cells.extend(info['cells'])
        for i,term1 in enumerate(info['names']):
            for j,term2 in enumerate(info['names']):
                covariances.append({'model':name,'term1':term1,'term2':term2,'covariance':float(info['cov'][i,j])})
        keep=info['keep']
        safe='domain_'+name
        d[safe]=keep.astype(int)
        specrows.append({'model':name,'domain_column':safe,'formula':'awareness ~ '+' + '.join(variables),'kind':kind,'variables':variables})
        if name in ['readings23','readings1234']:
            # Alternative reading rules require their phenotype changes in R's frame.
            for v in ['sbp','dbp']: d[name+'_'+v]=ds[v]
        return info
    primary_info=None
    for name,variables in SPECS.items():
        info=model(d,analytic,variables,name,'primary')
        if name=='M3':primary_info=info
    for name in ['M1','M2']:model(d,m3keep,SPECS[name],name+'_common','sample sensitivity')
    sensitivities=[('threshold140','hypertension_140',(20,64),False,1,False),
                   ('measured130','elevated_130',(20,64),True,1,False),
                   ('measured140','elevated_140',(20,64),True,1,False),
                   ('age20_59','hypertension_130',(20,59),False,1,False),
                   ('age30_64','hypertension_130',(30,64),False,1,False),
                   ('two_readings','hypertension_130',(20,64),True,2,False),
                   ('bp_complete','hypertension_130',(20,64),True,1,False),
                   ('exclude_pregnant','hypertension_130',(20,64),False,1,True)]
    for name,definition,age,rb,mr,ep in sensitivities:
        model(d,eligible(d,age,definition,rb,mr,ep),SPECS['M3'],name,'case/age sensitivity')
    for name,readings in [('readings23',(2,3)),('readings1234',(1,2,3,4))]:
        ds=prepare(raw,readings).loc[d_all.WTMEC2YR.gt(0)&d_all.RIDSTATR.eq(2)].reset_index(drop=True)
        model(ds,eligible(ds),SPECS['M3'],name,'reading sensitivity')
    model(d,analytic,[v for v in SPECS['M3'] if v!='pir'],'omit_pir','confounder sensitivity')
    model(d,analytic,SPECS['M3']+['age10_sq'],'quadratic_age','functional form sensitivity')
    model(d,analytic,[v if v!='pir' else 'pir_group' for v in SPECS['M3']],'categorical_pir','functional form sensitivity')
    model(d,domain&(d.uninsured.eq(1)|(d.uninsured.eq(0)&d.HIQ210.eq(2))),SPECS['M3'],'insured_no_lapse','post-review coverage restriction')
    cov=['no_usual_care','age10','sex','race','education','pir']
    model(d,domain,cov,'usual_care','exploratory secondary')
    model(d,domain,cov+['uninsured'],'usual_care_insurance','exploratory secondary')
    pd.concat(results).to_csv(OUT/'python_regression.csv',index=False)
    pd.DataFrame(covariances).to_csv(OUT/'python_covariance.csv',index=False)
    pd.DataFrame(cells).to_csv(OUT/'model_cells.csv',index=False)
    (OUT/'python_diagnostics.json').write_text(json.dumps(diags,indent=2))
    (OUT/'model_specifications.json').write_text(json.dumps(specrows,indent=2))
    pd.DataFrame([{k:v for k,v in s.items() if k!='variables'} for s in specrows]).to_csv(OUT/'model_specifications.csv',index=False)
    standardized(d,primary_info).to_csv(OUT/'python_marginal.csv',index=False)
    # Individual influence and support diagnostics for descriptive standardization.
    sub=d.loc[primary_info['keep']].copy();j=primary_info['names'].index('uninsured')
    se=np.sqrt(primary_info['cov'][j,j])
    observations=sub[['SEQN','SDMVSTRA','SDMVPSU','uninsured','awareness','WTMEC2YR']].copy()
    observations['weighted_leverage']=primary_info['leverage']
    observations['fitted_probability']=primary_info['prediction']
    observations['linearized_uninsured_beta_influence']=primary_info['influence'][primary_info['keep'].to_numpy(),j]
    observations['influence_in_SE_units']=observations.linearized_uninsured_beta_influence/se
    observations.to_csv(OUT/'observation_influence.csv',index=False)
    support=[]
    for exposure,g in sub.groupby('uninsured'):
        for v in ['RIDAGEYR','pir']:
            support.append({'uninsured':exposure,'variable':v,'n':len(g),'min':float(g[v].min()),'max':float(g[v].max())})
        for v in ['sex','race','education']:
            for level in CATEGORIES[v]:
                h=g[g[v].eq(level)]
                support.append({'uninsured':exposure,'variable':v,'level':level,'n':len(h),'aware_n':int(h.awareness.sum()),'unaware_n':int((1-h.awareness).sum())})
    pd.DataFrame(support).to_csv(OUT/'standardization_support.csv',index=False)
    jackknife_influence(d,analytic,SPECS['M3'],primary_info).to_csv(OUT/'psu_influence.csv',index=False)
    # Missingness comparisons: retained and excluded cases, outcome-specific denominator.
    profiles=[]
    d['complete_covariates']=m3keep.astype(float)
    profiles.append({'sample':'All eligible outcome/exposure complete','variable':'complete_covariates',**ratio(d,d.complete_covariates,analytic)})
    for label,mask in [('Included M3',m3keep),('Excluded M3',analytic&~m3keep)]:
        for v in ['RIDAGEYR','uninsured','awareness','sbp','dbp','pir']:
            profiles.append({'sample':label,'variable':v,**ratio(d,d[v],mask)})
    pd.DataFrame(profiles).to_csv(OUT/'missingness_profiles.csv',index=False)
    bounds=[]
    for value in [0,1]:
        mask=domain&d.uninsured.eq(value)
        for scenario in ['Missing all unaware','Missing all aware']:
            y=d.awareness.fillna(0 if 'unaware' in scenario else 1)
            bounds.append({'uninsured':value,'scenario':scenario,**ratio(d,y,mask)})
    pd.DataFrame(bounds).to_csv(OUT/'awareness_missing_bounds.csv',index=False)
    # Quantify medication linkage by case ascertainment component and insurance.
    components=[]
    for value in [0,1]:
        for label,mask in [('Elevated measured',domain&d.elevated_130.eq(1)),('Medication only, BP below threshold',domain&d.elevated_130.eq(0)&d.medication.eq(1)),('Medication confirmed, missing BP',domain&d.medication.eq(1)&(d.sbp.isna()|d.dbp.isna()))]:
            mask &= d.uninsured.eq(value)
            components.append({'uninsured':value,'component':label,**ratio(d,d.awareness,mask)})
    pd.DataFrame(components).to_csv(OUT/'ascertainment_components.csv',index=False)
    ascertainment=[]
    target=d.RIDAGEYR.between(20,64)
    for exposure in ['All','Insured','Uninsured']:
        mask=target.copy()
        if exposure!='All':mask &= d.uninsured.eq(0 if exposure=='Insured' else 1)
        known=d.hypertension_130.notna();case=d.hypertension_130.eq(1);unknown=~known
        for scenario,value in [('Lower',0),('Upper',1)]:
            y=d.hypertension_130.fillna(value)
            ascertainment.append({'estimand':'Hypertension prevalence','group':exposure,'bound':scenario,'unclassifiable_n':int((mask&unknown).sum()),**ratio(d,y,mask)})
        for label,yes,denom in [
            ('Lower',case&d.awareness.eq(1),case|(unknown&~d.awareness.eq(1))),
            ('Upper',(case|unknown)&~d.awareness.eq(0),case|(unknown&~d.awareness.eq(0)))]:
            ascertainment.append({'estimand':'Awareness prevalence','group':exposure,'bound':label,'unclassifiable_n':int((mask&unknown).sum()),**ratio(d,yes.astype(float),mask&denom)})
    pd.DataFrame(ascertainment).to_csv(OUT/'ascertainment_bounds.csv',index=False)
    (OUT/'target_definition.json').write_text(json.dumps({'primary':'Age20–64 examined, hypertension ascertainable by elevated available mean or current medication; no complete-BP requirement','all_target_exam_n':int(target.sum()),'case_classifiable_n':int((target&d.hypertension_130.notna()).sum()),'unclassifiable_n':int((target&d.hypertension_130.isna()).sum()),'known_medication_missing_bp_n':int((target&d.medication.eq(1)&(d.sbp.isna()|d.dbp.isna())).sum()),'revision':'Post-review, after inspecting original results'},indent=2))
    d.to_csv(OUT/'design_frame.csv',index=False)
    print('Python processing complete:',len(d),'design rows;',int(analytic.sum()),'analysis cases;',int(m3keep.sum()),'M3 cases')

if __name__=='__main__':run()
