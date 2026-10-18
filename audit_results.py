from pathlib import Path
import csv,json,hashlib
import numpy as np
ROOT=Path(__file__).parent; R=ROOT/'results'
def read(name):
    return [{k:(v if k in ['design','mode'] else float(v)) for k,v in a.items()} for a in csv.DictReader((R/name).open())]
rows=read('metrics.csv');controls=read('controls.csv');allrows=rows+controls
assert len(rows)==55 and len(controls)==14
for row in allrows:
    assert all(np.isfinite(v) for v in row.values() if isinstance(v,float))
    assert row['energy_Nmm']>0 and row['gold_mean_vm_MPa']>0
    assert row['residual']<2e-6 and row['force_balance_N']<1e-7
def get(name,mode='Tension',r=16):
    return next(a for a in rows if a['design']==name and a['mode']==mode and a['refinement']==r and a['soft_MPa']==.1 and a['skin_MPa']==.2 and a['nu']==.49)
changes={}; scale_errors=[];fields=[]
for name in ['Uniform','Single','Graded']:
    fine=get(name);old=get(name,r=8)
    changes[name]={k:100*abs(fine[k]-old[k])/fine[k] for k in ['gold_mean_vm_MPa','gold_p95_vm_MPa','gold_max_cell_vm_MPa','gold_mean_abs_exx','energy_Nmm']}
    assert changes[name]['gold_mean_vm_MPa']<5
    for r in [1,2,4]:
        t=get(name,r=r);c=get(name,'Compression',r)
        error=abs(c['gold_mean_vm_MPa']/.5/t['gold_mean_vm_MPa']-1);scale_errors.append(error);assert error<1e-12
    d=np.load(R/f'{name}_Tension.npz');p=d['points'];c=d['cells'];gold=d['gold'];vm=d['vm'];assert np.isfinite(d['displacement']).all() and np.isfinite(vm).all()
    location=p[c[gold][np.argmax(vm[gold])]].mean(axis=0)
    fields.append({'design':name,'max_cell_stress_centroid_mm':location.tolist()})
for mode in ['Tension','Bending']:
    assert get('Single',mode)['gold_mean_vm_MPa'] < get('Graded',mode)['gold_mean_vm_MPa'] < get('Uniform',mode)['gold_mean_vm_MPa']
for r in [8,16]:
    for name in ['Matched','Reverse']:
        assert any(a['design']==name and a['refinement']==r for a in controls)
report=dict(status='passed',solved_cases=len(allrows),mesh_changes_percent=changes,maximum_relative_free_residual=max(a['residual'] for a in allrows),maximum_force_balance_N=max(a['force_balance_N'] for a in allrows),compression_scaling_error=max(scale_errors),fields=fields)
(R/'audit.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
