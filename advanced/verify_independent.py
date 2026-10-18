"""Independent high-contrast quadratic assembly with matching perimeter constraints."""
import json
import numpy as np
from scipy.spatial import cKDTree
from skfem import MeshTet, Basis, ElementVector, ElementTetP2, BilinearForm, asm, condense, solve
from skfem.helpers import sym_grad, ddot, trace
from model import ROOT, write_deck, execute, parse_and_check, affine_displacement, boundary_nodes


def main():
    mesh_path=ROOT/'verification/cube.npz'
    mesh=np.load(mesh_path);p,c,r=mesh['points'],mesh['cells'],mesh['region']
    vertices=np.unique(c[:,:4])
    independent=MeshTet(p[vertices].T,np.searchsorted(vertices,c[:,:4]).T)
    basis=Basis(independent,ElementVector(ElementTetP2()),intorder=2)
    indices=basis.split_indices()
    coords=basis.doflocs[:,indices[0]].T
    distances,lookup=cKDTree(coords).query(p)
    assert max(distances)<1e-8
    perimeter,pin=boundary_nodes(p,c,r)
    fixed=np.concatenate([indices[0][lookup[perimeter]],indices[1][lookup[perimeter]],
                          np.array([indices[2][lookup[pin]]])])
    reports=[]
    nu=.49;loading=(.00255,.00255,.0149)
    # Include the largest bulk-gold / soft-adhesive modulus ratio in the grid.
    for contrast in [10.,392500.,1570000.]:
        dest=ROOT/'verification'/f'independent_contrast_{contrast:g}'
        write_deck(dest,mesh_path,loading,homogeneous=True,skin_E=.2,nu=nu,verification_contrast=contrast)
        execute(dest);checks=parse_and_check(dest)
        E=np.where(independent.p[:,independent.t].mean(axis=1)[0]>0,.2*contrast,.2)
        @BilinearForm
        def form(u,v,w):
            mu=w.E/(2*(1+nu));lam=w.E*nu/((1+nu)*(1-2*nu))
            return 2*mu*ddot(sym_grad(u),sym_grad(v))+lam*trace(sym_grad(u))*trace(sym_grad(v))
        K=asm(form,basis,E=np.repeat(E[:,None],basis.X.shape[1],axis=1))
        prescribed=affine_displacement(coords,loading)
        initial=np.zeros(basis.N)
        for axis in range(2):
            initial[indices[axis]]=prescribed[:,axis]
        solution=solve(*condense(K,np.zeros(basis.N),x=initial,D=fixed))
        u=np.column_stack([solution[ix] for ix in indices])[lookup]
        direct=np.load(dest/'fields.npz')['displacement']
        relative=float(np.linalg.norm(u-direct)/np.linalg.norm(u))
        error=float(np.max(abs(u-direct)))
        assert relative<2e-5,(contrast,relative)
        report=dict(contrast=contrast,nu=nu,independent_displacement_relative_error=relative,
                    displacement_max_absolute_error_mm=error,**checks)
        reports.append(report)
    (ROOT/'verification/independent_high_contrast.json').write_text(json.dumps(reports,indent=2))
    print(json.dumps(reports,indent=2),flush=True)


if __name__=='__main__':
    main()
