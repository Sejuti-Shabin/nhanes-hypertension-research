"""Compare independent R reference and Python calculations; fail on disagreement."""
import json, hashlib
import numpy as np
import pandas as pd
from data import OUT, ROOT


def validation_fingerprint():
    sources=['src/data.py','src/survey.py','src/pipeline.py','src/validate.py','run_all.py','r/survey_analysis.R','r/reviewer_sensitivities.R','r/reliability.R','data/source_manifest.json']
    outputs=['design_frame.csv','regression.csv','descriptive.csv','table1.csv','marginal_probabilities.csv','python_covariance.csv','r_covariance.csv','r_domain_validation.csv','r_jackknife_validation.csv','pir_response_weighting.csv','pir_response_summary.csv','ascertainment_bounds.csv']
    paths=[ROOT/p for p in sources]+list(sorted((ROOT/'data/raw').glob('*')))+list(sorted(OUT.glob('*.csv')))+[OUT/p for p in ['target_definition.json','cleaning_log.json','python_diagnostics.json','model_specifications.json']]
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}

def assert_current_validation():
    provenance=json.loads((OUT/'validation_provenance.json').read_text())
    if provenance['fingerprint']!=validation_fingerprint():raise AssertionError('Stale validation: source/output fingerprint changed')
    state=OUT/'run_state.json'
    if state.exists():
        status=json.loads(state.read_text())
        if status['status']=='failed':raise AssertionError('Current complete run failed; reporting blocked')
    result=json.loads((OUT/'validation.json').read_text())
    if not all(v['passed'] for v in result.values()):raise AssertionError('Validation incomplete')
    return result

def term_key(term):
    if term=='(Intercept)':return 'Intercept'
    for v in ['pir_group','education','race','sex']:
        if term.startswith(v):return v+'_'+term[len(v):].lstrip('_')
    return term

def run():
    report={};comparison=[]
    (OUT/'validation.json').unlink(missing_ok=True)
    for receipt in ['r_reference_receipt.csv','r_reviewer_receipt.csv']:
        entries=pd.read_csv(OUT/receipt)
        for row in entries.itertuples():
            current=hashlib.md5((ROOT/row.path).read_bytes()).hexdigest()
            if current!=row.md5:raise AssertionError(f'R execution receipt is stale: {row.path}')
    for name,keys,cols in [
      ('regression',['model','term'],['beta','se','odds_ratio','ci_low','ci_high','p','design_df','residual_df','n']),
      ('descriptive',['estimand','group','variable'],['estimate','se','n','design_df']),
      ('table1',['insurance','variable','level'],['estimate','se','n','design_df']),
      ('marginal',['estimand'],['estimate','se','ci_low','ci_high','n','design_df','inference_df'])]:
        py=pd.read_csv(OUT/f'python_{name}.csv')
        rp=OUT/({'marginal':'marginal_probabilities'}.get(name,name)+'.csv')
        r=pd.read_csv(rp)
        if name=='regression':r['term']=r.term.map(term_key)
        merged=py.merge(r,on=keys,suffixes=('_python','_r'),validate='one_to_one',how='outer',indicator=True)
        if not merged._merge.eq('both').all():raise AssertionError(f'Unmatched {name} rows: '+str(merged.loc[merged._merge!='both',keys]))
        for col in cols:
            a=merged[col+'_python'].to_numpy();b=merged[col+'_r'].to_numpy()
            ok=np.allclose(a,b,rtol=2e-6,atol=1e-8,equal_nan=True)
            diff=np.nanmax(np.abs(a-b))
            comparison.append({'analysis':name,'quantity':col,'rows':len(merged),'maximum_absolute_difference':float(diff),'passed':bool(ok)})
            if not ok:raise AssertionError(f'{name}.{col} disagrees: {diff}')
        report[name]={'rows_compared':len(merged),'passed':True}
    pycov=pd.read_csv(OUT/'python_covariance.csv');rcov=pd.read_csv(OUT/'r_covariance.csv')
    for v in ['term1','term2']:rcov[v]=rcov[v].map(term_key)
    cv=pycov.merge(rcov,on=['model','term1','term2'],suffixes=('_python','_r'),validate='one_to_one',how='outer',indicator=True)
    if not cv._merge.eq('both').all():raise AssertionError('Covariance terms unmatched')
    delta=np.abs(cv.covariance_python-cv.covariance_r)
    if not np.allclose(cv.covariance_python,cv.covariance_r,rtol=2e-6,atol=1e-8):raise AssertionError('Full covariance mismatch')
    report['full_covariance']={'entries_compared':len(cv),'max_absolute_difference':float(delta.max()),'passed':True}
    domains=pd.read_csv(OUT/'r_domain_validation.csv')
    if not domains.matched_python.all():raise AssertionError('Independent R domain failure')
    report['independent_domains']={'models':len(domains),'passed':True}
    raw=pd.read_csv(OUT/'r_raw_coding_validation.csv')
    if not raw.passed.all():raise AssertionError('R raw coding failed')
    report['raw_coding']={'variables':len(raw),'passed':True}
    pd.DataFrame(comparison).to_csv(OUT/'validation_comparison.csv',index=False)
    jk=pd.read_csv(OUT/'r_jackknife_validation.csv')
    response=pd.read_csv(OUT/'pir_response_summary.csv')
    if not np.isfinite(jk.jackknife_se).all() or not jk.replicates.eq(30).all():raise AssertionError('R JKn execution invalid')
    if int(response.iloc[0].replicate_count)!=30:raise AssertionError('PIR replicate execution invalid')
    report['R_replicate_execution']={'passed':True,'marginal_replicates':30,'PIR_replicates':30,'Python_PIR_validation':False,'scope':'Executed R replicate sensitivity; not an independent Python response-weighting verification'}
    (OUT/'validation.json').write_text(json.dumps(report,indent=2))
    (OUT/'validation_provenance.json').write_text(json.dumps({'fingerprint':validation_fingerprint(),'scope':'Current code/input/output content hashes'},indent=2))
    print('PASS: independent raw coding/domains, Python/R full covariance, coefficients, df, descriptive/marginal estimates; R replicate sensitivities executed')

if __name__=='__main__':run()
