"""Material sensitivity and opt-in nonlinear exploration; run after run_study.py.
The exploratory nonlinear assembly protocol has not established convergence.
"""
from run_ccx import ROOT,deck,execute
from parse_ccx import metrics
import json,time,sys
while not (ROOT/'study_progress.json').exists() or len(json.loads((ROOT/'study_progress.json').read_text()).get('completed',[]))<15:
    time.sleep(3)
def run(design,nonlinear=False,package=10000.,adhesive=.1):
    dest=deck(1.7,design,'Tension',nonlinear,package,adhesive)
    valid=(dest/'execution.json').exists() and json.loads((dest/'execution.json').read_text()).get('job_finished')
    if not valid or (not (dest/'fields.npz').exists() and not (dest/'job.dat').exists()):execute(dest)
    if not (dest/'metrics.json').exists() or not (dest/'fields.npz').exists():metrics(dest)
for E in [2000.,130000.]:run('Uniform',package=E)
for E in [.05,.5]:run('Uniform',adhesive=E)
if '--nonlinear' in sys.argv:
    for design in ['Uniform','Single','Graded']:run(design,True)
