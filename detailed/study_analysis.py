from pathlib import Path
import json,csv,numpy as np
from run_ccx import ROOT,NAMES
def all_results():return [json.loads(p.read_text()) for p in (ROOT/'runs').glob('*/metrics.json')]
def get(design='Uniform',mode='Tension',h=1.2,nonlinear=False,package=10000.,adhesive=.1):
    return next(a for a in all_results() if a['design']==design and a['mode']==mode and a['mesh_h_mm']==h and a['nonlinear']==nonlinear and a['package_E_MPa']==package and a['adhesive_E_MPa']==adhesive)
def part(a,r):return next(v for v in a['part_metrics'] if v['region']==r)
def group(a,regions,key='mean_vm_MPa'):
    pp=[part(a,r) for r in regions];return sum(p[key]*p['mesh_volume_mm3'] for p in pp)/sum(p['mesh_volume_mm3'] for p in pp)
def audit():
    out=ROOT/'output';out.mkdir(exist_ok=True);rows=all_results();table=[]
    for a in rows:
        assert a['relative_force_balance']<2e-5
        for p in a['part_metrics']:
            assert all(np.isfinite(v) for v in p.values() if isinstance(v,(float,int)))
            assert p['mean_vm_MPa']>0 and p['max_gp_vm_MPa']>=p['p95_vm_MPa']>=p['mean_vm_MPa']
            table.append({k:a[k] for k in ['mesh_h_mm','design','mode','nonlinear','package_E_MPa','adhesive_E_MPa']}|p)
    with (out/'All_Component_Results.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=table[0]);w.writeheader();w.writerows(table)
    changes={}
    scaling=[]
    for d in ['Uniform','Single','Graded']:
        fine=get(d);mid=get(d,h=1.7)
        changes[d]={NAMES[r]:dict(mean_stress_change_percent=100*abs(part(fine,r)['mean_vm_MPa']/part(mid,r)['mean_vm_MPa']-1),maximum_stress_change_percent=100*abs(part(fine,r)['max_gp_vm_MPa']/part(mid,r)['max_gp_vm_MPa']-1)) for r in range(4,16)}
        compression=get(d,mode='Compression',h=1.7)
        scaling.extend(abs(part(compression,r)['mean_vm_MPa']/(.5*part(mid,r)['mean_vm_MPa'])-1) for r in range(4,16))
    # Preserve the measured load-scaling discrepancy; do not present it as exact.
    # This screening check requires it to remain well below spatial mesh changes.
    assert max(scaling)<.005
    # Geometry fidelity and FE connectivity of the finest mesh.
    mesh=np.load(ROOT/'meshes/h1.2/mesh.npz');p,c,region=mesh['points'],mesh['cells'],mesh['region'];corners=p[c[:,:4]];vol=abs(np.einsum('ij,ij->i',np.cross(corners[:,1]-corners[:,0],corners[:,2]-corners[:,0]),corners[:,3]-corners[:,0]))/6
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    links=coo_matrix((np.ones(c.size-len(c)),(np.repeat(c[:,0],9),c[:,1:].ravel())),shape=(len(p),len(p))).tocsr();components,_=connected_components(links,directed=False);assert components==1
    cad=json.loads((ROOT/'sources/cad_inventory.json').read_text());frags=json.loads((ROOT/'meshes/h1.2/mesh_audit.json').read_text())['fragments'];fidelity={}
    for owner in range(1,17):
        masks=(region==owner) if owner!=3 else np.isin(region,[31,32,33]);actual=sum(a['volume_mm3'] for a in frags if a['owner']==owner);approx=float(vol[masks].sum());fidelity[str(owner)]=dict(fragmented_CAD_volume_mm3=actual,mesh_volume_mm3=approx,relative_volume_error_percent=100*(approx/actual-1))
    report=dict(solved_assembly_cases=len(rows),connected_components=components,maximum_relative_force_balance=max(a['relative_force_balance'] for a in rows),compression_scaling_relative_error=float(max(scaling)),mesh_volume_fidelity=fidelity,mesh_changes=changes,finest_mesh_nodes=len(p),finest_mesh_elements=len(c),finest_mesh_dofs=3*len(p),minimum_corner_volume_mm3=float(min(vol)),checks_passed=True)
    (out/'Study_Audit.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2));return report
if __name__=='__main__':audit()
