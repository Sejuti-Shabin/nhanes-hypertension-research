"""Synthetic edge cases and authentic-data integrity; no fitted-result constants."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
import pandas as pd
from data import load,prepare,medication,classify,eligible,merge_frames,COMPONENTS
from survey import ratio,covariance,fit,SPECS,standardized

class CodingTests(unittest.TestCase):
    def test_skip_patterns(self):
        d=pd.DataFrame({'BPQ020':[2,1,1,1,9,1], 'BPQ040A':[np.nan,2,1,9,np.nan,1],
                        'BPQ050A':[np.nan,np.nan,1,np.nan,np.nan,2]})
        m,s=medication(d)
        np.testing.assert_allclose(m,[0,0,1,np.nan,np.nan,0],equal_nan=True)
        self.assertEqual(s.tolist(),[True,True,False,False,False,False])
    def test_three_valued_hypertension(self):
        s=pd.Series([130,120,120,np.nan,120,120]);b=pd.Series([70,80,70,np.nan,70,70]);m=pd.Series([np.nan,0,1,1,np.nan,0])
        measured,case=classify(s,b,m)
        np.testing.assert_allclose(measured,[1,1,0,np.nan,0,0],equal_nan=True)
        np.testing.assert_allclose(case,[1,1,1,1,np.nan,0],equal_nan=True)
        measured,case=classify(pd.Series([140.,120.]),pd.Series([np.nan,np.nan]),pd.Series([0.,0.]))
        np.testing.assert_allclose(measured,[1,np.nan],equal_nan=True)
        np.testing.assert_allclose(case,[1,np.nan],equal_nan=True)
    def test_failed_run_invalidates_stale_success(self):
        import tempfile,shutil,json,subprocess
        root=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            copy=Path(tmp)
            shutil.copy(root/'run_all.py',copy/'run_all.py')
            shutil.copytree(root/'src',copy/'src',ignore=shutil.ignore_patterns('__pycache__'))
            (copy/'outputs').mkdir()
            (copy/'outputs/validation.json').write_text('{"old":{"passed":true}}')
            proc=subprocess.run([sys.executable,str(copy/'run_all.py'),'--check-only'],capture_output=True,text=True)
            self.assertNotEqual(proc.returncode,0)
            self.assertFalse((copy/'outputs/validation.json').exists())
            state=json.loads((copy/'outputs/run_state.json').read_text())
            self.assertEqual(state['status'],'failed')
            self.assertEqual(state['failed_stage'],'Python_R_comparison')
            self.assertNotEqual(state['stages'][-1]['returncode'],0)
    def test_merge_duplicate_and_foreign_ids(self):
        frames={v:pd.DataFrame({'SEQN':[1,2]}) for v in COMPONENTS}
        self.assertEqual(len(merge_frames(frames)),2)
        frames['HIQ_J']=pd.DataFrame({'SEQN':[1,1]})
        with self.assertRaises(ValueError):merge_frames(frames)
        frames['HIQ_J']=pd.DataFrame({'SEQN':[3]})
        with self.assertRaises(ValueError):merge_frames(frames)
    def test_nchs_boundary_and_complement_rules(self):
        import subprocess
        root=Path(__file__).resolve().parents[1]
        r=subprocess.run(['Rscript',str(root/'tests/test_reliability.R'),str(root)],capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
    def test_full_domain_variance_and_lonely_psu(self):
        d=pd.DataFrame({'SDMVSTRA':[1,1,2,2],'SDMVPSU':[1,2,1,2],'WTMEC2YR':[1.,1.,1.,1.]})
        y=pd.Series([0.,1.,0.,1.]);allrows=pd.Series(True,index=d.index)
        e=ratio(d,y,allrows);self.assertAlmostEqual(e['estimate'],.5);self.assertAlmostEqual(e['se']**2,.125)
        e=ratio(d,y,pd.Series([True,True,False,False]));self.assertEqual(e['design_df'],2);self.assertAlmostEqual(e['se'],.5)
        with self.assertRaises(ValueError):covariance(d.iloc[:3],np.ones(3))

class AuthenticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw,_=load(download=False);cls.d=prepare(cls.raw)
        cls.exam=cls.d.loc[cls.d.WTMEC2YR.gt(0)&cls.d.RIDSTATR.eq(2)].reset_index(drop=True)
    def test_unique_merge_and_design(self):
        self.assertTrue(self.d.SEQN.is_unique);self.assertEqual(len(self.raw),len(self.d))
        self.assertTrue(self.d.loc[self.d.RIDSTATR.eq(1),'WTMEC2YR'].eq(0).all())
        self.assertTrue(self.exam[['SDMVSTRA','SDMVPSU']].notna().all().all())
        self.assertTrue(self.exam.WTMEC2YR.gt(0).all())
        self.assertTrue(self.exam.groupby('SDMVSTRA').SDMVPSU.nunique().ge(2).all())
    def test_missing_outcome_exposure_and_covariates(self):
        for source,derived in [('BPQ020','awareness'),('HIQ011','uninsured')]:
            self.assertTrue(self.d.loc[~self.d[source].isin([1,2]),derived].isna().all())
        self.assertTrue(self.d.loc[~self.d.DMDEDUC2.isin([1,2,3,4,5]),'education'].isna().all())
        self.assertTrue(self.d.loc[self.d.INDFMPIR.isna(),'pir'].isna().all())
    def test_bp_means_and_zero_dbp(self):
        expected=self.raw[[f'BPXSY{i}' for i in [1,2,3]]].mean(axis=1)
        np.testing.assert_allclose(self.d.sbp,expected,equal_nan=True)
        row=self.raw.iloc[[0]].copy()
        row[['BPXSY1','BPXSY2','BPXSY3']]=[120,np.nan,140]
        row[['BPXDI1','BPXDI2','BPXDI3']]=[0,np.nan,80]
        z=prepare(row)
        self.assertAlmostEqual(z.sbp.iloc[0],130);self.assertAlmostEqual(z.dbp.iloc[0],40)
    def test_domains_and_classification(self):
        e=eligible(self.d)
        self.assertTrue(self.d.loc[e,'RIDAGEYR'].between(20,64).all())
        self.assertTrue((self.d.loc[e,'medication'].eq(1)|(self.d.loc[e,'sbp'].notna()&self.d.loc[e,'dbp'].notna())).all())
        self.assertTrue(self.d.loc[e,'hypertension_130'].eq(1).all())
        positive=(self.d.sbp.ge(130)|self.d.dbp.ge(80)|self.d.medication.eq(1))
        self.assertTrue(positive[e].all())
        self.assertTrue((eligible(self.d,definition='elevated_130')<=e).all())
    def test_weight_scale_and_order_invariance(self):
        d=self.exam;domain=eligible(d)
        a,_,ia=fit(d,domain,SPECS['M3'],'test')
        z=d.copy();z.WTMEC2YR*=17.3
        b,_,ib=fit(z,domain,SPECS['M3'],'test')
        np.testing.assert_allclose(a[['beta','se']],b[['beta','se']],rtol=1e-9,atol=1e-10)
        np.testing.assert_allclose(standardized(d,ia)[['estimate','se']],standardized(z,ib)[['estimate','se']],rtol=1e-8,atol=1e-10)
        shuffled=d.sample(frac=1,random_state=20261010).reset_index(drop=True)
        c,_,_=fit(shuffled,eligible(shuffled),SPECS['M3'],'test')
        np.testing.assert_allclose(a[['beta','se']],c[['beta','se']],rtol=1e-8,atol=1e-10)
    def test_medication_missing_bp_preserved(self):
        d=self.d
        cases=eligible(d)
        treated_missing=d.RIDAGEYR.between(20,64)&d.WTMEC2YR.gt(0)&d.RIDSTATR.eq(2)&d.medication.eq(1)&(d.sbp.isna()|d.dbp.isna())
        self.assertTrue(cases[treated_missing].all())
        self.assertFalse(eligible(d,require_bp=True)[treated_missing].any())
    def test_marginal_df_and_bounded_probabilities(self):
        d=self.exam
        _,diag,info=fit(d,eligible(d),SPECS['M3'],'test')
        z=standardized(d,info)
        self.assertTrue(z.inference_df.eq(diag['residual_df']).all())
        self.assertTrue(z.iloc[:2].ci_low.between(0,1).all())
        self.assertTrue(z.iloc[:2].ci_high.between(0,1).all())
    def test_executed_replicate_sensitivities(self):
        from data import OUT
        jk=pd.read_csv(OUT/'r_jackknife_validation.csv')
        self.assertTrue(np.isfinite(jk[['estimate','jackknife_se']]).all().all())
        self.assertTrue(jk.replicates.eq(30).all())
        response=pd.read_csv(OUT/'pir_response_diagnostics.csv')
        self.assertTrue(response.response_probability.between(0,1,inclusive='neither').all())
        self.assertTrue(response.inverse_response_weight.ge(1).all())
        replicates=pd.read_csv(OUT/'pir_response_replicates.csv')
        self.assertEqual(len(replicates),30)
        self.assertTrue(np.isfinite(replicates).all().all())
    def test_external_reference(self):
        from validate import run
        run()

if __name__=='__main__':unittest.main()
