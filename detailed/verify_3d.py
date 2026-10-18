"""Independent quadratic-tetrahedron comparisons and exact uniaxial benchmark."""
from pathlib import Path
import gmsh,numpy as np,meshio,json,subprocess,os
from skfem import MeshTet, Basis,ElementVector,ElementTetP2,BilinearForm,asm,condense,solve
from skfem.helpers import sym_grad,ddot,trace
from run_ccx import ROOT,CCX,lineset
from parse_ccx import blocks

def main():
    out=ROOT/'verification';out.mkdir(exist_ok=True)
    gmsh.initialize();gmsh.option.setNumber('General.Terminal',0);gmsh.model.occ.addBox(0,0,0,1,1,1);gmsh.model.occ.synchronize();gmsh.option.setNumber('Mesh.MeshSizeMax',.4);gmsh.option.setNumber('Mesh.MeshSizeMin',.4);gmsh.model.mesh.generate(3);gmsh.option.setNumber('Mesh.SecondOrderLinear',1);gmsh.model.mesh.setOrder(2)
    nt,xyz,_=gmsh.model.mesh.getNodes();p=np.array(xyz).reshape(-1,3);typ,et,en=gmsh.model.mesh.getElements(3);raw=np.array(en[0]).reshape(-1,10)[:,[0,1,2,3,4,5,6,7,9,8]];sort=np.argsort(nt);p=p[sort];c=np.searchsorted(nt[sort],raw);gmsh.finalize()
    # scikit-fem generates its own edge-node order from the same tetra vertices.
    vertices=np.unique(c[:,:4]);m=MeshTet(p[vertices].T,np.searchsorted(vertices,c[:,:4]).T);basis=Basis(m,ElementVector(ElementTetP2()),intorder=2)
    fixed=np.concatenate([basis.get_dofs(lambda x:np.isclose(x[0],0)).all(['u^1']),basis.get_dofs(lambda x:np.isclose(x[0],1)).all(['u^1']),basis.get_dofs(lambda x:np.isclose(x[1],0)).all(['u^2']),basis.get_dofs(lambda x:np.isclose(x[2],0)).all(['u^3'])])
    reports=[]
    for nu,hetero in [(.3,False),(.49,False),(.3,True)]:
        tag=f'nu{nu}_hetero{hetero}';dest=out/tag;dest.mkdir(exist_ok=True)
        elemE=np.where(p[c[:,:4]].mean(axis=1)[:,0]>.5,10.,1.) if hetero else np.ones(len(c))
        with (dest/'job.inp').open('w') as f:
            f.write('*NODE,NSET=NALL\n')
            for i,v in enumerate(p,1):f.write(f'{i},'+','.join(map(str,v))+'\n')
            for E in sorted(set(elemE)):
                f.write(f'*ELEMENT,TYPE=C3D10,ELSET=E{E:g}\n')
                for i in np.where(elemE==E)[0]:f.write(f'{i+1},'+','.join(str(int(a+1)) for a in c[i])+'\n')
                f.write(f'*MATERIAL,NAME=M{E:g}\n*ELASTIC\n{E},{nu}\n*SOLID SECTION,ELSET=E{E:g},MATERIAL=M{E:g}\n')
            for name,axis,value in [('LEFT',0,0),('RIGHT',0,1),('Y0',1,0),('Z0',2,0)]:lineset(f,'NSET',name,np.where(np.isclose(p[:,axis],value))[0]+1)
            f.write('*STEP\n*STATIC,SOLVER=PASTIX\n*BOUNDARY\nLEFT,1,1,0\nRIGHT,1,1,.01\nY0,2,2,0\nZ0,3,3,0\n*NODE PRINT,NSET=NALL\nU,RF\n*END STEP\n')
        env=os.environ.copy();env['OMP_NUM_THREADS']='4'
        with (dest/'solver.log').open('w') as f:r=subprocess.run([str(CCX),'-i','job'],cwd=dest,env=env,stdout=f,stderr=subprocess.STDOUT)
        if r.returncode:raise RuntimeError((dest/'solver.log').read_text()[-3000:])
        parsed=blocks(dest/'job.dat');disp=parsed['displacements','nall'];force=parsed['forces','nall'];ccu=disp[:,1:]
        @BilinearForm
        def elasticity(u,v,w):
            E=np.where(w.x[0]>.5,10.,1.) if hetero else 1.
            # For the heterogeneous benchmark use the CCX elementwise centroid assignment.
            if hetero:E=w.E
            lam=E*nu/((1+nu)*(1-2*nu));mu=E/(2*(1+nu));return 2*mu*ddot(sym_grad(u),sym_grad(v))+lam*trace(sym_grad(u))*trace(sym_grad(v))
        centroid=m.p[:,m.t].mean(axis=1);ee=np.where(centroid[0]>.5,10.,1.) if hetero else np.ones(m.nelements)
        K=asm(elasticity,basis,E=np.repeat(ee[:,None],basis.X.shape[1],axis=1));x=np.zeros(basis.N);x[basis.get_dofs(lambda x:np.isclose(x[0],1)).all(['u^1'])]=.01
        uu=solve(*condense(K,np.zeros(basis.N),x=x,D=fixed));nodal=basis.split_indices();sol=np.column_stack([uu[i] for i in nodal]);coords=basis.doflocs[:,nodal[0]].T
        from scipy.spatial import cKDTree
        dist,idx=cKDTree(coords).query(p);assert max(dist)<1e-8
        rel=np.linalg.norm(sol[idx]-ccu)/np.linalg.norm(ccu);reaction=force[np.isclose(p[:,0],1),1].sum()
        report=dict(nu=nu,heterogeneous=hetero,nodes=len(p),elements=len(c),independent_displacement_relative_error=float(rel),reaction_N=float(reaction),expected_reaction_N=None if hetero else .01)
        if not hetero:
            exact=np.column_stack((.01*p[:,0],-.01*nu*p[:,1],-.01*nu*p[:,2]));report['analytical_displacement_max_error_mm']=float(np.max(abs(ccu-exact)));report['analytical_reaction_relative_error']=float(abs(reaction/.01-1));assert report['analytical_reaction_relative_error']<2e-5
        assert rel<2e-5;reports.append(report)
    (out/'verification_summary.json').write_text(json.dumps(reports,indent=2));print(json.dumps(reports,indent=2))
if __name__=='__main__':main()
