"""CalculiX decks and execution for the original multi-body 3D assembly.
All unconfirmed constituent properties are explicit analyst assumptions.
"""
from pathlib import Path
import numpy as np,json,subprocess,os,argparse,time
ROOT=Path(__file__).parent
CCX=ROOT/'tools/calculix223/calculix_2.23_4win/ccx_static.exe'
NAMES={1:'Skin',2:'Adhesive',31:'Lower_PDMS',32:'Middle_PDMS',33:'Upper_PDMS',4:'ABS_sensor_housing',5:'Sensor_1',6:'Sensor_2',7:'Sensor_3',8:'Sensor_4',9:'Gold_feature_1',10:'RC_transmitter',11:'Gold_feature_2',12:'ABS_feature',13:'Gold_wire_1',14:'Gold_wire_2',15:'Sensor_5',16:'PDMS_cover'}

def properties(region,design,package=10000.,adhesive=.1):
    if region==1:return .2,.49
    if region==2:return adhesive,.49
    if region in [4,12]:return 2300.,.35
    if region in [5,6,7,8,15]:return package,.30
    if region==10:return 20000.,.30
    if region in [9,11,13,14]:return 78500.,.42
    if design=='Single' and region in [31,32]:return .1,.49
    if design=='Graded' and region in [31,32]:return (.1 if region==31 else .5),.49
    return 1.8,.49

def lineset(f,kind,name,ids):
    f.write(f'*{kind}, {kind}= '+name+'\n')
    for i in range(0,len(ids),16):f.write(','.join(str(int(x)) for x in ids[i:i+16])+'\n')

def deck(h=2.5,design='Uniform',mode='Tension',nonlinear=False,package=10000.,adhesive=.1):
    mesh=np.load(ROOT/'meshes'/f'h{h:g}'/'mesh.npz');p=mesh['points'];c=mesh['cells'];reg=mesh['region'];dest=ROOT/'runs'/(f'h{h:g}_{design}_{mode}_{"NH" if nonlinear else "LE"}_P{package:g}_A{adhesive:g}'+('_Warm' if nonlinear else ''));dest.mkdir(parents=True,exist_ok=True)
    left=np.where((abs(p[:,0]+30)<1e-6)&(p[:,2]<=2.000001))[0]+1;right=np.where((abs(p[:,0]-30)<1e-6)&(p[:,2]<=2.000001))[0]+1
    assert len(left)>5 and len(right)>5
    with (dest/'job.inp').open('w') as f:
        f.write('*HEADING\nOriginal STEP biosensor assembly, mm N MPa, explicit assumed properties\n*NODE,NSET=NALL\n')
        for i,xyz in enumerate(p,1):f.write(f'{i},'+','.join(f'{v:.12g}' for v in xyz)+'\n')
        for region in sorted(set(reg)):
            f.write(f'*ELEMENT,TYPE=C3D10,ELSET=PART{region}\n')
            ids=np.where(reg==region)[0]
            for i in ids:f.write(f'{i+1},'+','.join(str(int(x+1)) for x in c[i])+'\n')
        lineset(f,'ELSET','ELECTRONICS',np.where((reg>=4)&(reg<=15))[0]+1)
        lineset(f,'ELSET','ALL',np.arange(len(c))+1)
        lineset(f,'NSET','LEFT',left);lineset(f,'NSET','RIGHT',right)
        for region in sorted(set(reg)):
            E,nu=properties(region,design,package,adhesive);f.write(f'*MATERIAL,NAME=MAT{region}\n')
            if nonlinear and region in [1,2,16,31,32,33]:
                C10=E/(4*(1+nu));D1=6*(1-2*nu)/E
                f.write(f'*HYPERELASTIC,NEO HOOKE\n{C10:.12g},{D1:.12g}\n')
            else:f.write(f'*ELASTIC\n{E:.12g},{nu:.12g}\n')
            f.write(f'*SOLID SECTION,ELSET=PART{region},MATERIAL=MAT{region}\n')
        if nonlinear:
            initial=np.load(ROOT/'runs'/f'h{h:g}_{design}_{mode}_LE_P{package:g}_A{adhesive:g}'/'fields.npz')['displacement']
            assert initial.shape==(len(p),3)
            f.write('*INITIAL CONDITIONS,TYPE=DISPLACEMENT\n')
            for node,vec in enumerate(initial,1):
                for axis,value in enumerate(vec,1):f.write(f'{node},{axis},{value:.12g}\n')
            f.write('*STEP,NLGEOM=YES,INC=100\n*STATIC,SOLVER=PASTIX\n1.,1.,1.e-6,1.\n')
        else:f.write('*STEP\n*STATIC,SOLVER=PASTIX\n')
        f.write('*BOUNDARY\nLEFT,1,3,0.\n')
        if mode=='Bending':f.write('RIGHT,3,3,-0.6\n')
        else:f.write(f'RIGHT,1,1,{.6 if mode=="Tension" else -.3}\n')
        f.write('*NODE PRINT,NSET=NALL,FREQUENCY=999999\nU,RF\n*EL PRINT,ELSET=ELECTRONICS,FREQUENCY=999999\nS,E\n*NODE FILE,FREQUENCY=999999\nU\n*END STEP\n')
    meta=dict(mesh_h_mm=h,design=design,mode=mode,nonlinear=nonlinear,package_E_MPa=package,adhesive_E_MPa=adhesive,nodes=len(p),elements=len(c),left_nodes=len(left),right_nodes=len(right),material_assumptions={NAMES[int(r)]:dict(E_MPa=properties(r,design,package,adhesive)[0],nu=properties(r,design,package,adhesive)[1]) for r in sorted(set(reg))})
    (dest/'input_metadata.json').write_text(json.dumps(meta,indent=2));return dest

def execute(dest):
    env=os.environ.copy();env.update(OMP_NUM_THREADS='4',CCX_NPROC_RESULTS='4',OPENBLAS_NUM_THREADS='4');start=time.time()
    with (dest/'solver.log').open('w') as log:
        r=subprocess.run([str(CCX),'-i','job'],cwd=dest,env=env,stdout=log,stderr=subprocess.STDOUT)
    txt=(dest/'solver.log').read_text(errors='replace')
    summary=dict(returncode=r.returncode,elapsed_seconds=time.time()-start,job_finished='Job finished' in txt,error_lines=[a for a in txt.splitlines() if '*ERROR' in a])
    (dest/'execution.json').write_text(json.dumps(summary,indent=2));print(dest.name,summary,flush=True)
    if r.returncode or not summary['job_finished'] or summary['error_lines']:raise RuntimeError(txt[-6000:])
    return dest
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--h',type=float,default=2.5);a.add_argument('--design',default='Uniform');a.add_argument('--mode',default='Tension');a.add_argument('--nonlinear',action='store_true');a.add_argument('--package',type=float,default=10000.);a.add_argument('--adhesive',type=float,default=.1);args=a.parse_args();execute(deck(args.h,args.design,args.mode,args.nonlinear,args.package,args.adhesive))
