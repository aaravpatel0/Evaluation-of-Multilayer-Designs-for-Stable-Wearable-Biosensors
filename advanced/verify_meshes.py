"""Check connectivity, C3D10 edge-node placement, and existing CAD mesher audits."""
import json
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from model import ROOT,PROJECT


def main():
    reports=[]
    for scenario,base in [('Supplied',PROJECT/'detailed/meshes'),('Filled',ROOT/'meshes/filled')]:
        for h in [1.7,1.2]:
            mesh=np.load(base/f'h{h:g}/mesh.npz');p,c=mesh['points'],mesh['cells']
            audit=json.loads((base/f'h{h:g}/mesh_audit.json').read_text())
            assert audit['minimum_jacobian']>0
            assert np.isfinite(p).all() and c.shape[1]==10
            assert len(np.unique(c))==len(p)
            assert len(np.unique(np.sort(c[:,:4],axis=1),axis=0))==len(c)
            graph=coo_matrix((np.ones(9*len(c),dtype=np.int8),
                              (np.repeat(c[:,0],9),c[:,1:].ravel())),shape=(len(p),len(p))).tocsr()
            n,_=connected_components(graph,directed=False)
            assert n==1
            midpoint_error=0.
            for k,(i,j) in enumerate([(0,1),(1,2),(2,0),(0,3),(1,3),(2,3)]):
                midpoint_error=max(midpoint_error,float(np.max(np.linalg.norm(p[c[:,4+k]]-.5*(p[c[:,i]]+p[c[:,j]]),axis=1))))
            assert midpoint_error<1e-8
            v=p[c[:,:4]]
            volume=np.linalg.det(v[:,1:]-v[:,:1])/6
            assert min(volume)>0
            reports.append(dict(scenario=scenario,h_mm=h,nodes=len(p),elements=len(c),
                                connected_components=n,minimum_mesher_Jacobian=audit['minimum_jacobian'],
                                minimum_SICN_quality=audit['minimum_quality'],
                                minimum_signed_corner_volume_mm3=float(min(volume)),
                                maximum_edge_midpoint_error_mm=midpoint_error))
    (ROOT/'verification/mesh_verification.json').write_text(json.dumps(reports,indent=2))
    print(json.dumps(reports,indent=2))


if __name__=='__main__':
    main()
