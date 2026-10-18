from pathlib import Path
import numpy as np,re,json,csv
from run_ccx import ROOT,NAMES
def blocks(path):
    out={};key=None;data=[]
    def keep():
        if key and data:out[key]=np.array(data)
    for line in Path(path).read_text(errors='replace').splitlines():
        low=line.strip().lower()
        match=re.match(r'(displacements|forces|stresses|strains)\s+\(.*?\)\s+for set\s+(\S+)\s+and time\s+(\S+)',low)
        if match:
            keep();key=(match[1],match[2]);data=[];continue
        fields=line.split()
        if key and fields and re.match(r'^\d+$',fields[0]):
            try:data.append([float(v.replace('D','E')) for v in fields])
            except ValueError:pass
        elif key and data and (not fields or not fields[0][0].isdigit()):keep();key=None;data=[]
    keep();return out

def metrics(dest):
    dest=Path(dest);meta=json.loads((dest/'input_metadata.json').read_text());mesh=np.load(ROOT/'meshes'/f'h{meta["mesh_h_mm"]:g}'/'mesh.npz');p,c,reg=mesh['points'],mesh['cells'],mesh['region'];b=blocks(dest/'job.dat')
    print('Parsed blocks',[(k,v.shape) for k,v in b.items()],flush=True)
    times=re.findall(r'and time\s+([\d.Ee+\-]+)',(dest/'job.dat').read_text(errors='replace'))
    assert times and abs(float(times[-1])-1.)<1e-7,'Final load fraction was not reached'
    stress=b['stresses','electronics'];strain=b['strains','electronics'];u=b['displacements','nall'];forces=b['forces','nall'];assert len(u)==len(p)
    assert np.array_equal(stress[:,:2],strain[:,:2])
    a,bp,cp,dp=[p[c[:,i]] for i in range(4)];vol=abs(np.einsum('ij,ij->i',np.cross(bp-a,cp-a),dp-a))/6
    element=stress[:,0].astype(int)-1;weights=vol[element]/4;s=stress[:,2:];e=strain[:,2:]
    vm=np.sqrt(.5*((s[:,0]-s[:,1])**2+(s[:,1]-s[:,2])**2+(s[:,2]-s[:,0])**2)+3*np.sum(s[:,3:]**2,axis=1))
    tensors=np.zeros((len(e),3,3));tensors[:,0,0]=e[:,0];tensors[:,1,1]=e[:,1];tensors[:,2,2]=e[:,2];tensors[:,0,1]=tensors[:,1,0]=e[:,3];tensors[:,0,2]=tensors[:,2,0]=e[:,4];tensors[:,1,2]=tensors[:,2,1]=e[:,5]
    principal=np.linalg.eigvalsh(tensors);maxabs=np.max(abs(principal),axis=1);rows=[]
    for region in range(4,16):
        mask=reg[element]==region
        if not mask.any():continue
        v,w=vm[mask],weights[mask];order=np.argsort(v);p95=v[order][np.searchsorted(np.cumsum(w[order])/sum(w),.95)]
        rows.append(dict(part=NAMES[region],region=region,gp_count=int(mask.sum()),mesh_volume_mm3=float(4*sum(w)/4),mean_vm_MPa=float(np.average(v,weights=w)),p95_vm_MPa=float(p95),max_gp_vm_MPa=float(max(v)),mean_abs_principal_strain=float(np.average(maxabs[mask],weights=w)),max_abs_principal_strain=float(max(maxabs[mask]))))
    forcebalance=np.linalg.norm(forces[:,1:].sum(axis=0));normalization=np.linalg.norm(forces[:,1:]);assert np.isfinite(vm).all()
    summary={**meta,'part_metrics':rows,'force_balance_N':float(forcebalance),'relative_force_balance':float(forcebalance/max(normalization,1e-30)),'maximum_displacement_mm':float(np.max(np.linalg.norm(u[:,1:],axis=1))),'minimum_element_volume_mm3':float(min(vol))}
    (dest/'metrics.json').write_text(json.dumps(summary,indent=2));np.savez_compressed(dest/'fields.npz',node_id=u[:,0].astype(int),displacement=u[:,1:],forces=forces[:,1:],element_id=element+1,gp=stress[:,1].astype(int),stress=s,strain=e,vm=vm)
    with (dest/'part_metrics.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=rows[0]);writer.writeheader();writer.writerows(rows)
    print(json.dumps({k:summary[k] for k in ['force_balance_N','relative_force_balance','maximum_displacement_mm']},indent=2));return summary
if __name__=='__main__':
    import sys;metrics(sys.argv[1])
