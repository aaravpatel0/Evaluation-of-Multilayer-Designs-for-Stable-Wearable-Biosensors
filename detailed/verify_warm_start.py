from run_ccx import ROOT,CCX
from parse_ccx import blocks
import numpy as np,os,subprocess,json
def main():
    source=ROOT/'verification/nu0.3_heteroFalse';txt=(source/'job.inp').read_text();u=blocks(source/'job.dat')['displacements','nall'];base=txt.replace('*ELASTIC\n1.0,0.3','*HYPERELASTIC,NEO HOOKE\n0.1923076923076923,2.4').replace('*STEP\n','*STEP,NLGEOM=YES\n').replace('*STATIC,SOLVER=PASTIX\n','*STATIC,SOLVER=PASTIX\n1.,1.,1.e-6,1.\n');assert '*HYPERELASTIC' in base
    answers=[]
    for name in ['cold','warm']:
        dest=ROOT/'verification'/f'neo_hookean_{name}';dest.mkdir(exist_ok=True);text=base
        if name=='warm':
            initial='*INITIAL CONDITIONS,TYPE=DISPLACEMENT\n'+''.join(f'{int(v[0])},{i},{v[i]:.12g}\n' for v in u for i in [1,2,3]);text=text.replace('*STEP,NLGEOM',initial+'*STEP,NLGEOM')
        (dest/'job.inp').write_text(text);env=os.environ.copy();env['OMP_NUM_THREADS']='4'
        with (dest/'solver.log').open('w') as f:r=subprocess.run([str(CCX),'-i','job'],cwd=dest,env=env,stdout=f,stderr=subprocess.STDOUT)
        assert r.returncode==0 and 'Job finished' in (dest/'solver.log').read_text();data=blocks(dest/'job.dat');answers.append(data['displacements','nall'][:,1:])
    error=float(np.linalg.norm(answers[0]-answers[1])/np.linalg.norm(answers[0]));assert error<2e-5
    f0=blocks(ROOT/'verification/neo_hookean_cold/job.dat')['forces','nall'][:,1:];f1=blocks(ROOT/'verification/neo_hookean_warm/job.dat')['forces','nall'][:,1:];force_error=float(np.linalg.norm(f0-f1)/np.linalg.norm(f0));assert force_error<2e-5
    report=dict(benchmark='Neo-Hookean cube at 1% extension, identical reference geometry and final boundary conditions',cold_vs_linear_initialized_displacement_relative_error=error,cold_vs_linear_initialized_force_relative_error=force_error,passed=True)
    (ROOT/'verification/warm_start_verification.json').write_text(json.dumps(report,indent=2));print(report)
if __name__=='__main__':main()
