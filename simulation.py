"""Reproducible 2D plane-strain Q4 finite elements; mm, N, MPa.
Full integration of deviatoric stiffness, one-point volumetric integration.
No ANSYS outputs are used in the computations. Run: python simulation.py
"""
from pathlib import Path
import json, csv, time, platform
import numpy as np
import scipy
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import spsolve
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).parent
OUT=ROOT/'results'; OUT.mkdir(exist_ok=True)
NAMES=['Uniform','Single','Graded']

def layers(design, soft=.1, skin=.2, nu=.49):
    a=[('Skin',2.,skin,nu,10)]
    if design=='Uniform': a += [('PDMS',.4,1.8,nu,4)]
    if design in ['Single','Matched']: a += [('Soft',.2,soft if design=='Single' else 1/6,nu,4),('PDMS',.2,1.8,nu,4)]
    if design=='Graded': a += [('Soft',.1,soft,nu,2),('Medium',.1,.5,nu,2),('PDMS',.2,1.8,nu,4)]
    if design=='Reverse': a += [('Medium',.1,.5,nu,2),('Soft',.1,soft,nu,2),('PDMS',.2,1.8,nu,4)]
    return a+[('Sensor level',.02,1.8,nu,2),('Encapsulation',.1,1.8,nu,3)]

def mesh(design, refinement=1, **params):
    nx=50*refinement; xx=np.linspace(0,5,nx+1); yy=[0.]; bands=[]
    for name,t,E,nu,n in layers(design,**params):
        y0=yy[-1]; yy.extend(np.linspace(y0,y0+t,n*refinement+1)[1:]); bands.extend([(name,E,nu)]*(n*refinement))
    p=np.array([(x,y) for y in yy for x in xx]); cells=[]; mats=[]
    for j,(name,E,nu) in enumerate(bands):
        for i in range(nx):
            k=j*(nx+1)+i; cells.append([k,k+1,k+nx+2,k+nx+1])
            gold=name=='Sensor level' and xx[i+1]<=1+1e-10
            mats.append((110000.,.34,1) if gold else (E,nu,0))
    return p,np.array(cells),np.array(mats)

def Bmat(xy,xi,eta):
    dn=np.array([[-(1-eta),1-eta,1+eta,-(1+eta)],[-(1-xi),-(1+xi),1+xi,1-xi]])/4
    J=dn@xy; grad=np.linalg.solve(J,dn); B=np.zeros((3,8)); B[0,::2]=grad[0]; B[1,1::2]=grad[1]; B[2,::2]=grad[1]; B[2,1::2]=grad[0]
    return B,np.linalg.det(J)

def constit(E,nu):
    mu=E/(2*(1+nu)); bulk=E/(3*(1-2*nu)); v=np.array([1.,1.,0.]); Ddev=np.array([[4*mu/3,-2*mu/3,0],[-2*mu/3,4*mu/3,0],[0,0,mu]])
    return Ddev,bulk*np.outer(v,v),mu,bulk

def solve(design,mode='Tension',refinement=1,soft=.1,skin=.2,nu=.49,save=False):
    p,c,m=mesh(design,refinement,soft=soft,skin=skin,nu=nu); nd=2*len(p); ed=(c[:,:,None]*2+np.arange(2)).reshape(-1,8)
    kes=[]; areas=[]; cache={}; gps=[(a/np.sqrt(3),b/np.sqrt(3)) for a in [-1,1] for b in [-1,1]]
    for ids,mat in zip(c,m):
        xy=p[ids]; E,n,_=mat; key=tuple(np.round([xy[1,0]-xy[0,0],xy[3,1]-xy[0,1],E,n],12))
        if key not in cache:
            xy=xy-xy[0]; dd,dv,_,_=constit(E,n); ke=np.zeros((8,8)); area=0
            for xi,eta in gps:
                b,j=Bmat(xy,xi,eta); ke+=b.T@dd@b*j; area+=j
            b,j=Bmat(xy,0,0); ke+=b.T@dv@b*j*4; cache[key]=(ke,area)
        ke,area=cache[key]; kes.append(ke); areas.append(area)
    K=coo_matrix((np.array(kes).ravel(),(np.repeat(ed,8,axis=1).ravel(),np.tile(ed,(1,8)).ravel())),shape=(nd,nd)).tocsr()
    left=np.where((np.abs(p[:,0])<1e-9)&(p[:,1]<=2+1e-9))[0]; right=np.where((np.abs(p[:,0]-5)<1e-9)&(p[:,1]<=2+1e-9))[0]
    fixed=list((left[:,None]*2+np.arange(2)).ravel()); values=[0.]*len(fixed)
    if mode in ['Tension','Compression']:
        for node in right:
            fixed.extend([2*node,2*node+1]); values.extend([.05 if mode=='Tension' else -.025,0.])
    else:
        fixed.extend((2*right+1).tolist()); values.extend([-.05]*len(right))
    fixed=np.array(fixed); values=np.array(values); free=np.setdiff1d(np.arange(nd),fixed); u=np.zeros(nd); u[fixed]=values
    u[free]=spsolve(K[free][:,free],-K[free][:,fixed]@values); reactions=K@u
    relres=np.linalg.norm(reactions[free])/max(np.linalg.norm(reactions[fixed]),1e-30)
    vm=[]; exx=[]
    for ids,dofs,mat in zip(c,ed,m):
        E,n,_=mat; dd,dv,mu,bulk=constit(E,n); b,_=Bmat(p[ids],0,0); vol=(b@u[dofs])[:2].sum(); vals=[]; strains=[]
        for xi,eta in gps:
            b,_=Bmat(p[ids],xi,eta); eps=b@u[dofs]; s=dd@eps+bulk*vol*np.array([1,1,0]); sz=-2*mu/3*(eps[0]+eps[1])+bulk*vol
            vals.append(np.sqrt(.5*((s[0]-s[1])**2+(s[1]-sz)**2+(sz-s[0])**2)+3*s[2]**2)); strains.append(abs(eps[0]))
        vm.append(np.mean(vals)); exx.append(np.mean(strains))
    vm=np.array(vm); exx=np.array(exx); areas=np.array(areas); gold=m[:,2]==1; w=areas[gold]; vg=vm[gold]; order=np.argsort(vg); p95=vg[order][np.searchsorted(np.cumsum(w[order])/sum(w),.95)]
    row=dict(design=design,mode=mode,refinement=refinement,elements=len(c),dofs=nd,soft_MPa=soft,skin_MPa=skin,nu=nu,gold_mean_vm_MPa=np.average(vg,weights=w),gold_p95_vm_MPa=p95,gold_max_cell_vm_MPa=max(vg),gold_mean_abs_exx=np.average(exx[gold],weights=w),energy_Nmm=.5*u@reactions,residual=relres,force_balance_N=float(np.linalg.norm(reactions.reshape(-1,2).sum(axis=0))))
    if save: np.savez_compressed(OUT/f'{design}_{mode}.npz',points=p,cells=c,displacement=u.reshape(-1,2),vm=vm,gold=gold)
    print(json.dumps(row),flush=True)
    return row

def verify():
    xy=np.array([[0,0],[2,0],[2,1],[0,1.]])
    u=np.column_stack((.01*xy[:,0]+.003*xy[:,1],-.002*xy[:,1]+.004*xy[:,0])).ravel()
    errors=[np.max(abs(Bmat(xy,x,y)[0]@u-np.array([.01,-.002,.007]))) for x,y in [(0,0),(.577,.577),(-.577,.577)]]
    rigid=np.column_stack((-xy[:,1],xy[:,0])).ravel(); er=np.max(abs(Bmat(xy,0,0)[0]@rigid))
    return dict(affine_patch_strain_error=max(errors),rigid_rotation_strain_error=er)

def main():
    start=time.time(); rows=[]
    for r in [1,2,4]:
        for design in NAMES:
            for mode in ['Tension','Compression','Bending']: rows.append(solve(design,mode,r,save=r==4))
    for soft in [.05,.2]:
        for design in NAMES[1:]: rows.append(solve(design,'Tension',2,soft=soft))
    for skin in [.1,.4]:
        for design in NAMES: rows.append(solve(design,'Tension',2,skin=skin))
    for nu in [.45,.495]:
        for design in NAMES: rows.append(solve(design,'Tension',2,nu=nu))
    with (OUT/'metrics.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=rows[0]); writer.writeheader(); writer.writerows(rows)
    meta=dict(verification=verify(),elapsed_seconds=time.time()-start,python=platform.python_version(),numpy=np.__version__,scipy=scipy.__version__,cases=len(rows))
    (OUT/'run_summary.json').write_text(json.dumps(meta,indent=2)); print(meta)

if __name__=='__main__': main()
