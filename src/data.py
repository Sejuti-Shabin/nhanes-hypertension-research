"""Authentic NHANES source ingestion, codebook checks and explicit phenotypes."""
from pathlib import Path
import hashlib, json, urllib.request, datetime
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data/raw'
OUT = ROOT / 'outputs'
BASE = 'https://wwwn.cdc.gov/nchs/data/nhanes/public/2017/datafiles/'
COMPONENTS = ['DEMO_J', 'BPX_J', 'BPQ_J', 'HIQ_J', 'HUQ_J']
CATEGORIES = {
    'sex': ['Female', 'Male'],
    'race': ['White', 'Black', 'Mexican American', 'Other Hispanic', 'Asian', 'Other/multiracial'],
    'education': ['College graduate', 'Some college/AA', 'High school/GED', 'Below high school'],
    'pir_group': ['PIR >2', 'PIR >1–2', 'PIR ≤1'],
}
VARIABLES = {
 'DEMO_J': ['SEQN','RIDAGEYR','RIAGENDR','RIDRETH3','DMDEDUC2','INDFMPIR','RIDSTATR','WTMEC2YR','SDMVSTRA','SDMVPSU','RIDEXPRG'],
 'BPX_J': ['SEQN'] + [f'BPX{kind}{i}' for kind in ['SY','DI'] for i in range(1,5)],
 'BPQ_J': ['SEQN','BPQ020','BPQ040A','BPQ050A'],
 'HIQ_J': ['SEQN','HIQ011','HIQ210'], 'HUQ_J': ['SEQN','HUQ030'],
}

def merge_frames(frames):
    d = frames['DEMO_J'].copy()
    for name in COMPONENTS:
        f=frames[name]
        if f.SEQN.isna().any() or not f.SEQN.is_unique:
            raise ValueError(f'{name}: missing/duplicate SEQN')
        if name != 'DEMO_J':
            if not set(f.SEQN).issubset(set(d.SEQN)): raise ValueError('Unmatched component IDs')
            d=d.merge(f,on='SEQN',how='left',validate='one_to_one')
    if len(d)!=len(frames['DEMO_J']): raise ValueError('Merge changed base population')
    return d

def load(download=True):
    RAW.mkdir(parents=True,exist_ok=True)
    frames={}; provenance={}
    for name in COMPONENTS:
        entries={}
        for ext in ['xpt','htm']:
            p=RAW/f'{name}.{ext}'
            if not p.exists():
                if not download: raise FileNotFoundError(p)
                payload=urllib.request.urlopen(BASE+p.name,timeout=60).read()
                if ext=='xpt' and not payload.startswith(b'HEADER RECORD'): raise ValueError('Not XPORT')
                p.write_bytes(payload)
            entries[ext]={'url':BASE+p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size}
        f=pd.read_sas(RAW/f'{name}.xpt',format='xport')
        # Normalize actual numeric zero decoded by older XPORT readers as ~5e-79.
        for col in f.select_dtypes('number'):
            f.loc[f[col].abs().lt(1e-50),col]=0.0
        if not set(VARIABLES[name]).issubset(f.columns): raise ValueError(f'Missing variables: {name}')
        html=(RAW/f'{name}.htm').read_text(errors='replace')
        for v in VARIABLES[name]:
            if f'id="{v}"' not in html: raise ValueError(f'Variable absent from codebook: {v}')
        frames[name]=f[VARIABLES[name]]
        entries['rows']=len(f); provenance[name]=entries
    # Validate against committed hashes when available; no silent source refresh.
    manifest=ROOT/'data/source_manifest.json'
    if manifest.exists():
        expected=json.loads(manifest.read_text())
        for name in COMPONENTS:
            for ext in ['xpt','htm']:
                if provenance[name][ext]['sha256']!=expected[name][ext]['sha256']:
                    raise ValueError(f'Source checksum changed: {name}.{ext}')
    return merge_frames(frames),provenance

def medication(d):
    m=d.BPQ050A.map({1:1.,2:0.})
    structural=d.BPQ050A.isna() & (d.BPQ020.eq(2) | (d.BPQ020.eq(1)&d.BPQ040A.eq(2)))
    m.loc[structural]=0.
    return m,structural

def classify(sbp,dbp,med,s=130,b=80):
    valid=sbp.notna()&dbp.notna()
    measured=pd.Series(np.nan,index=sbp.index)
    measured.loc[valid]=0.
    # A known elevated component establishes the OR even if its companion is missing.
    measured.loc[sbp.ge(s)|dbp.ge(b)]=1.
    case=pd.Series(np.nan,index=sbp.index)
    case.loc[measured.eq(1)|med.eq(1)]=1.
    case.loc[measured.eq(0)&med.eq(0)]=0.
    return measured,case

def prepare(raw,readings=(1,2,3)):
    d=raw.copy()
    for col in d.select_dtypes('number'):
        d.loc[d[col].abs().lt(1e-50),col]=0.
    for i in range(1,5):
        sy,di=f'BPXSY{i}',f'BPXDI{i}'
        if ((d[sy].notna() & ~d[sy].between(1,300)) | (d[di].notna() & ~d[di].between(0,300))).any():
            raise ValueError('BP outside protocol range')
        if (d[sy].notna() & d[di].notna() & (d[sy]<=d[di])).any(): raise ValueError('Invalid paired BP')
    d['sbp']=d[[f'BPXSY{i}' for i in readings]].mean(axis=1)
    d['dbp']=d[[f'BPXDI{i}' for i in readings]].mean(axis=1)
    d['n_sbp']=d[[f'BPXSY{i}' for i in readings]].notna().sum(axis=1)
    d['n_dbp']=d[[f'BPXDI{i}' for i in readings]].notna().sum(axis=1)
    d['medication'],d['medication_structural_no']=medication(d)
    d['awareness']=d.BPQ020.map({1:1.,2:0.})
    d['uninsured']=d.HIQ011.map({1:0.,2:1.})
    d['no_usual_care']=d.HUQ030.map({1:0.,2:1.,3:0.})
    d['sex']=d.RIAGENDR.map({1:'Male',2:'Female'})
    d['race']=d.RIDRETH3.map({1:'Mexican American',2:'Other Hispanic',3:'White',4:'Black',6:'Asian',7:'Other/multiracial'})
    d['education']=d.DMDEDUC2.map({1:'Below high school',2:'Below high school',3:'High school/GED',4:'Some college/AA',5:'College graduate'})
    d['pir']=d.INDFMPIR.where(d.INDFMPIR.between(0,5))
    d['pir_group']=pd.cut(d.pir,[-.001,1,2,5],labels=['PIR ≤1','PIR >1–2','PIR >2']).astype(object)
    d['age10']=(d.RIDAGEYR-40)/10
    d['age10_sq']=d.age10**2
    for name,(s,b) in {'130':(130,80),'140':(140,90)}.items():
        d[f'elevated_{name}'],d[f'hypertension_{name}']=classify(d.sbp,d.dbp,d.medication,s,b)
    d['one']=1.
    return d

def eligible(d,age=(20,64),definition='hypertension_130',require_bp=False,min_readings=1,exclude_pregnant=False):
    mask=d.RIDAGEYR.between(*age)&d.RIDSTATR.eq(2)&d.WTMEC2YR.gt(0)&d[definition].eq(1)
    if require_bp: mask &= d.sbp.notna()&d.dbp.notna()&d.n_sbp.ge(min_readings)&d.n_dbp.ge(min_readings)
    if exclude_pregnant: mask &= ~d.RIDEXPRG.eq(1)
    return mask

def dictionary():
    descriptions={
      'SEQN':'Public-use respondent identifier; unique within component',
      'RIDAGEYR':'Age in years; primary 20–64, avoids 80+ top code',
      'RIAGENDR':'NHANES binary sex coding: 1 male, 2 female; not gender identity',
      'RIDRETH3':'Race/ethnicity: 1 Mexican American, 2 other Hispanic, 3 White, 4 Black, 6 Asian, 7 other/multiracial',
      'DMDEDUC2':'Adult education: 1/2 below high school, 3 high school/GED, 4 some college/AA, 5 college; 7/9 unknown',
      'INDFMPIR':'Family income-to-poverty ratio, 0–5; top-coded 5, missing preserved',
      'RIDSTATR':'1 interview only, 2 interviewed/examined',
      'WTMEC2YR':'Two-year MEC examination weight; require positive, do not divide by cycles',
      'SDMVSTRA':'Masked variance stratum', 'SDMVPSU':'Masked PSU within stratum',
      'RIDEXPRG':'Pregnancy status: 1 pregnant; 2 not pregnant; 3 cannot determine; eligibility-limited missingness',
      'BPQ020':'Awareness proxy: 1 ever told hypertension by professional, 2 no; 7/9/missing unknown',
      'BPQ040A':'Ever told to take prescribed BP medicine: 1 yes, 2 no; NOT current use',
      'BPQ050A':'Current prescribed BP medicine: 1 yes, 2 no; structural no inferred only from documented skips',
      'HIQ011':'Current coverage: 1 insured, 2 uninsured; 7/9 unknown',
      'HIQ210':'Any period without insurance in past 12 months among currently insured: 1 yes, 2 no, 7/9 unknown; uninsured structural skip is NOT no lapse',
      'HUQ030':'Usual care place: 1 one, 2 none, 3 multiple; 7/9 unknown',
    }
    rows=[]
    for component,cols in VARIABLES.items():
        for v in cols:
            if v=='SEQN' and component!='DEMO_J': continue
            desc=descriptions.get(v,'Systolic' if 'SY' in v else 'Diastolic')
            if v.startswith('BPX'):desc+=f' reading {v[-1]}, mmHg; fourth attempt sensitivity only; DBP 0 retained'
            rows.append({'variable':v,'source':component,'definition_and_coding':desc,'codebook':BASE+component+'.htm#'+v})
    derived={
      'sbp':'Mean of available first three SBP values; missing if none',
      'dbp':'Mean of available first three DBP values; zero valid',
      'medication':'BPQ050A yes/no plus structural skip no; residual unknown missing',
      'awareness':'BPQ020: 1 -> 1, 2 -> 0, other -> missing',
      'uninsured':'HIQ011: 2 -> 1, 1 -> 0, other -> missing',
      'no_usual_care':'HUQ030: 2 -> 1, 1/3 -> 0, other -> missing',
      'hypertension_130':'Measured SBP ≥130 or DBP ≥80 or medication=1; normal measurement+medication unknown -> missing',
      'hypertension_140':'Same rule at 140/90',
      'elevated_130':'Measured-only 130/80; known elevated component establishes positive; both means required for negative',
      'elevated_140':'Measured-only 140/90; known elevated component establishes positive; both means required for negative',
      'age10':'(RIDAGEYR-40)/10', 'age10_sq':'Squared centered age term, sensitivity',
      'sex':'Female reference, Male indicator', 'race':'Six categories, White reference',
      'education':'Four categories, College graduate reference',
      'pir':'INDFMPIR restricted to [0,5]; continuous primary adjustment',
      'pir_group':'≤1, >1–2, >2; >2 reference in sensitivity',
      'n_sbp':'Count of available readings in selected rule','n_dbp':'Count of available readings in selected rule',
      'medication_structural_no':'Flag for BPQ050A missing coded no by skip logic',
    }
    rows.extend({'variable':v,'source':'derived','definition_and_coding':desc,'codebook':''} for v,desc in derived.items())
    return pd.DataFrame(rows)
