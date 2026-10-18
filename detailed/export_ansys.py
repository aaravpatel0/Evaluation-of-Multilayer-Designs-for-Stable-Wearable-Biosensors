"""Export a matched LINEAR APDL problem for a future independent comparison.
This deck is generated but has NOT been executed in ANSYS.
SOLID187 uses the same I,J,K,L,M,N,O,P,Q,R connectivity as the exported C3D10.
Requires a Mechanical APDL installation and a license supporting the mesh size.
"""
from run_ccx import ROOT,properties
import numpy as np,argparse
def export(h=1.2,design='Uniform'):
    mesh=np.load(ROOT/'meshes'/f'h{h:g}'/'mesh.npz');p,c,regions=mesh['points'],mesh['cells'],mesh['region'];out=ROOT/'output/ANSYS_Comparison';out.mkdir(exist_ok=True)
    path=out/f'{design}_h{h:g}_linear_extension.dat'
    with path.open('w') as f:
        f.write('! GENERATED MATCHED INPUT ONLY - ANSYS EXECUTION NOT PERFORMED\nFINISH\n/CLEAR\n/PREP7\nET,1,187\nTYPE,1\n')
        for r in sorted(set(regions)):
            E,nu=properties(r,design);f.write(f'MP,EX,{r},{E:.12g}\nMP,PRXY,{r},{nu:.12g}\n')
        for i,xyz in enumerate(p,1):f.write(f'N,{i},'+','.join(f'{v:.12g}' for v in xyz)+'\n')
        f.write('SHPP,OFF\n')
        prev=None
        for i,(conn,r) in enumerate(zip(c+1,regions),1):
            if r!=prev:f.write(f'MAT,{r}\n');prev=r
            f.write(f'EN,{i},'+','.join(str(int(x)) for x in conn[:8])+'\nEMORE,'+','.join(str(int(x)) for x in conn[8:])+'\n')
        f.write('SHPP,ON\nALLSEL,ALL\nCHECK\nFINISH\n/SOLU\nANTYPE,STATIC\nNLGEOM,OFF\nEQSLV,SPARSE\nSELTOL,1e-6\nNSEL,S,LOC,X,-30.000001,-29.999999\nNSEL,R,LOC,Z,-0.000001,2.000001\nD,ALL,UX,0\nD,ALL,UY,0\nD,ALL,UZ,0\nNSEL,S,LOC,X,29.999999,30.000001\nNSEL,R,LOC,Z,-0.000001,2.000001\nD,ALL,UX,0.6\nALLSEL,ALL\nOUTRES,ALL,ALL\nSOLVE\nFINISH\n/POST1\nSET,LAST\n/OUTPUT,ansys_nodal_results,txt\nPRNSOL,U,COMP\nPRRSOL\n/OUTPUT\nFINISH\n')
    print(path)
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--h',type=float,default=1.2);a.add_argument('--design',default='Uniform');args=a.parse_args();export(args.h,args.design)
