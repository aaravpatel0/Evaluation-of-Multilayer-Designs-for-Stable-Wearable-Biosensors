"""Read-only local-equilibrium audit of retained earlier and exploratory fields."""
from functools import lru_cache
from pathlib import Path
import json,sys
import numpy as np
from model import ROOT,PROJECT,boundary_nodes

@lru_cache(maxsize=4)
def mesh(path):
    return dict(np.load(path))


def main():
    rows=[]
    for field_path in sorted((PROJECT/'detailed/runs').glob('*/fields.npz')):
        dest=field_path.parent
        if not (dest/'metrics.json').exists():
            continue
        meta=json.loads((dest/'input_metadata.json').read_text())
        m=mesh(PROJECT/f'detailed/meshes/h{meta["mesh_h_mm"]:g}/mesh.npz')
        p=m['points'];mask=np.zeros_like(p,dtype=bool)
        left=(abs(p[:,0]+30)<1e-6)&(p[:,2]<=2.000001)
        right=(abs(p[:,0]-30)<1e-6)&(p[:,2]<=2.000001)
        mask[left,:]=True;mask[right,2 if meta['mode']=='Bending' else 0]=True
        data=np.load(field_path);r=data['forces'];u=data['displacement']
        residual=float(np.linalg.norm(r[~mask])/np.linalg.norm(r[mask]))
        rows.append(dict(case=dest.relative_to(PROJECT).as_posix(),
                         free_DOF_relative_force_residual=residual,
                         prescribed_DOF_work_Nmm=float(.5*np.sum((u*r)[mask])),
                         free_DOF_work_Nmm=float(.5*np.sum((u*r)[~mask]))))
    for field_path in sorted((ROOT/'runs').glob('*/fields.npz')):
        dest=field_path.parent
        if dest.name.startswith('SPL_'):
            continue
        meta=json.loads((dest/'input_metadata.json').read_text())
        m=mesh(PROJECT/meta['mesh_path']);p=m['points']
        perimeter,pin=boundary_nodes(p,m['cells'],m['region'])
        mask=np.zeros_like(p,dtype=bool);mask[perimeter,:2]=True;mask[pin,2]=True
        data=np.load(field_path);r=data['forces'];u=data['displacement']
        residual=float(np.linalg.norm(r[~mask])/np.linalg.norm(r[mask]))
        rows.append(dict(case=dest.relative_to(PROJECT).as_posix(),
                         free_DOF_relative_force_residual=residual,
                         prescribed_DOF_work_Nmm=float(.5*np.sum((u*r)[mask])),
                         free_DOF_work_Nmm=float(.5*np.sum((u*r)[~mask]))))
    out=ROOT/'verification/existing_field_equilibrium_audit.json'
    out.write_text(json.dumps(rows,indent=2))
    print(json.dumps(dict(cases=len(rows),maximum_relative_free_DOF_residual=max(r['free_DOF_relative_force_residual'] for r in rows),
                         original_19_range=[min(r['free_DOF_relative_force_residual'] for r in rows if r['case'].startswith('detailed/')),
                                            max(r['free_DOF_relative_force_residual'] for r in rows if r['case'].startswith('detailed/'))]),indent=2))


if __name__=='__main__':
    main()
