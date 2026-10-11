#!/usr/bin/env python3
"""Fail-closed pipeline with explicit current execution state and source validation."""
from pathlib import Path
import argparse,json,os,subprocess,sys,time,importlib.metadata,re,uuid
ROOT=Path(__file__).resolve().parent

def run():
    p=argparse.ArgumentParser();p.add_argument('--check-only',action='store_true');args=p.parse_args()
    out=ROOT/'outputs';out.mkdir(exist_ok=True);logs=out/'logs';logs.mkdir(exist_ok=True)
    state={'run_id':str(uuid.uuid4()),'status':'running','stages':[],'check_only':args.check_only}
    def save_state():
        (out/'run_state.json').write_text(json.dumps(state,indent=2))
        (out/'execution.json').write_text(json.dumps(state['stages'],indent=2))
    # Supersede old success stamps before any failure-prone work.
    for name in ['validation.json','validation_provenance.json','test_results.json','clean_checkout_validation.json']:
        (out/name).unlink(missing_ok=True)
    save_state()
    env=os.environ.copy();env['PYTHONHASHSEED']='0';env['TZ']='America/Chicago'
    local_r=Path.home()/'R/library'
    if local_r.exists():env['R_LIBS_USER']=str(local_r)+(':'+env['R_LIBS_USER'] if env.get('R_LIBS_USER') else '')
    cmds=[] if args.check_only else [('processing',[sys.executable,'src/pipeline.py']),('R_reference',['Rscript','r/survey_analysis.R',str(ROOT)]),('reviewer_sensitivities',[ 'Rscript','r/reviewer_sensitivities.R',str(ROOT)])]
    cmds += [('Python_R_comparison',[sys.executable,'src/validate.py']),('tests',[sys.executable,'-m','unittest','discover','-s','tests','-v'])]
    if not args.check_only:cmds += [('figures',[sys.executable,'src/figures.py']),('reports',[sys.executable,'src/report.py'])]
    for name,cmd in cmds:
        start=time.monotonic();print('Running',name,flush=True)
        try:
            r=subprocess.run(cmd,cwd=ROOT,env=env,capture_output=True,text=True)
            output=r.stdout+r.stderr;rc=r.returncode
        except OSError as e:output=str(e);rc=127
        (logs/(name+'.log')).write_text(output)
        state['stages'].append({'stage':name,'returncode':rc,'elapsed_seconds':round(time.monotonic()-start,3)})
        save_state()
        if name=='tests':
            m=re.search(r'Ran (\d+) tests',output)
            failures=re.search(r'failures=(\d+)',output);errors=re.search(r'errors=(\d+)',output)
            result={'tests_run':int(m.group(1)) if m else None,'passed':rc==0,'returncode':rc,'failed':int(failures.group(1)) if failures else 0,'errors':int(errors.group(1)) if errors else 0,'log':'outputs/logs/tests.log'}
            (out/'test_results.json').write_text(json.dumps(result,indent=2))
        if rc:
            state['status']='failed';state['failed_stage']=name;save_state()
            (out/'validation.json').unlink(missing_ok=True)
            (out/'validation_provenance.json').unlink(missing_ok=True)
            print(output);raise SystemExit(f'{name} failed; prior success stamps invalidated and downstream reporting stopped')
        print(r.stdout.strip(),flush=True)
    versions={'python':sys.version,'seed':20261010,'stochastic_primary_operations':False}
    for name in ['numpy','pandas','scipy','statsmodels','matplotlib']:versions[name]=importlib.metadata.version(name)
    (out/'python_environment.json').write_text(json.dumps(versions,indent=2))
    if not args.check_only:
        r=subprocess.run([sys.executable,'src/qa.py'],cwd=ROOT,env=env,capture_output=True,text=True)
        (logs/'qa.log').write_text(r.stdout+r.stderr)
        state['stages'].append({'stage':'QA','returncode':r.returncode});save_state()
        if r.returncode:
            state['status']='failed';state['failed_stage']='QA';save_state();print(r.stdout+r.stderr);raise SystemExit('QA failed')
        print(r.stdout.strip())
    state['status']='complete';save_state();print('Complete. All required stages passed.')

if __name__=='__main__':run()
