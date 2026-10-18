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
        direct_fields=np.load(dest/'fields.npz')
        direct=direct_fields['displacement']
        relative=float(np.linalg.norm(u-direct)/np.linalg.norm(u))
        error=float(np.max(abs(u-direct)))
        # Element means avoid assuming the same quadrature-point numbering.
        # Straight-sided P2 strain and stress are linear inside each material
        # element, so both four-point rules recover their centroid values.
        expected=np.searchsorted(vertices,c[:,:4]).T
        assert np.array_equal(np.sort(independent.t,axis=0),np.sort(expected,axis=0))
        gradient=basis.interpolate(solution).grad
        eps=.5*(gradient+np.swapaxes(gradient,0,1))
        mu=E/(2*(1+nu));lam=E*nu/((1+nu)*(1-2*nu))
        sigma=2*mu[None,None,:,None]*eps+np.eye(3)[:,:,None,None]*lam[None,None,:,None]*np.trace(eps,axis1=0,axis2=1)[None,None,:,:]
        def components(tensor):
            return np.stack([tensor[0,0],tensor[1,1],tensor[2,2],tensor[0,1],tensor[0,2],tensor[1,2]],axis=-1).mean(axis=1)
        v=p[c[:,:4]]
        volume=abs(np.linalg.det(v[:,1:]-v[:,:1]))/6
        weight=np.sqrt(volume[:,None]*np.array([1,1,1,2,2,2]))
        field_errors={}
        for name,prediction in [('strain',components(eps)),('stress',components(sigma))]:
            target=direct_fields[name].mean(axis=1)
            field_errors[name]=float(np.linalg.norm(weight*(prediction-target))/np.linalg.norm(weight*prediction))
        assert relative<2e-5,(contrast,relative)
        assert max(field_errors.values())<2e-5,(contrast,field_errors)
        report=dict(contrast=contrast,nu=nu,independent_displacement_relative_error=relative,
                    displacement_max_absolute_error_mm=error,
                    independent_element_mean_tensor_relative_errors=field_errors,**checks)
        reports.append(report)
    (ROOT/'verification/independent_high_contrast.json').write_text(json.dumps(reports,indent=2))
    print(json.dumps(reports,indent=2),flush=True)


if __name__=='__main__':
    main()
