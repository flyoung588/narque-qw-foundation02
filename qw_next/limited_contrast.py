"""Exactly two import-only children, same environment, DATA cap is sole varied input."""
import pathlib,signal,subprocess,sys,time
from router import save
def run(out):
 out=pathlib.Path(out);rows=[]
 for mode in ['512MiB','inherited']:
  d=out/mode;d.mkdir(parents=True,exist_ok=True)
  with (d/'stdout.log').open('wb') as a,(d/'stderr.log').open('wb') as b:
   p=subprocess.Popen([sys.executable,'-B',str(pathlib.Path(__file__).with_name('native_worker.py')),'--import-only',mode,str(d)],stdout=a,stderr=b,start_new_session=True)
   try:code=p.wait(timeout=20)
   except subprocess.TimeoutExpired:
    import os;os.killpg(p.pid,signal.SIGKILL);code=p.wait(timeout=3)
  rows.append({'mode':mode,'returncode':code,'success_file':(d/'import_success.json').exists()})
 save(out/'CONTRAST.json',{'rows':rows,'science_calculations':0,'scope':'import-only cap contrast in one environment; no SCF/molecule/gradient repeated. Even a contrasting outcome only identifies this import-stage causal association, not every historical crash.','cause_claim':'PENDING_AI_REVIEW_OF_ACTUAL_OUTCOMES'})
 return rows[-1]['returncode']==0 and rows[-1]['success_file']
