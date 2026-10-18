from run_ccx import deck,execute,ROOT
from parse_ccx import metrics
import json,time
records=[];start=time.time()
def run(h,design,mode='Tension',nonlinear=False,package=10000.,adhesive=.1):
    dest=deck(h,design,mode,nonlinear,package,adhesive)
    valid=(dest/'execution.json').exists() and json.loads((dest/'execution.json').read_text()).get('job_finished')
    if not valid or (not (dest/'fields.npz').exists() and not (dest/'job.dat').exists()):execute(dest)
    if not (dest/'metrics.json').exists() or not (dest/'fields.npz').exists():metrics(dest)
    records.append(str(dest.relative_to(ROOT)));(ROOT/'study_progress.json').write_text(json.dumps(dict(completed=records,elapsed_seconds=time.time()-start),indent=2))
for d in ['Uniform','Single','Graded']:run(2.5,d)
for d in ['Uniform','Single','Graded']:run(1.7,d)
for mode in ['Bending','Compression']:
    for d in ['Uniform','Single','Graded']:run(1.7,d,mode)
for d in ['Uniform','Single','Graded']:run(1.2,d)
print('Primary linear study finished',flush=True)
