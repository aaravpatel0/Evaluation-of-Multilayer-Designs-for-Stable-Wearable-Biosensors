"""Directional tensor combinations and mechanical tradeoff metrics, not clinical predictions."""
import argparse, csv, json
import numpy as np
from model import ROOT, PROJECT, BASIS, SOLVER_TAG,BACKEND
from interface import interface_geometry, surface_stress, traction


def tensor_norm_squared(e):
    return np.sum(e*e*np.array([1,1,1,2,2,2]),axis=-1)


def von_mises(s):
    return np.sqrt(.5*((s[...,0]-s[...,1])**2+(s[...,1]-s[...,2])**2+
                       (s[...,2]-s[...,0])**2)+3*np.sum(s[...,3:]**2,axis=-1))


def absolute_principal(e):
    matrix=np.zeros((*e.shape[:-1],3,3))
    matrix[...,0,0]=e[...,0];matrix[...,1,1]=e[...,1];matrix[...,2,2]=e[...,2]
    matrix[...,0,1]=matrix[...,1,0]=e[...,3]
    matrix[...,0,2]=matrix[...,2,0]=e[...,4]
    matrix[...,1,2]=matrix[...,2,1]=e[...,5]
    return np.max(abs(np.linalg.eigvalsh(matrix)),axis=-1)


def quantile(values,weights,q=.95):
    order=np.argsort(values)
    index=np.searchsorted(np.cumsum(weights[order]),q*np.sum(weights))
    return float(values[order[min(index,len(values)-1)]])


def coefficients(angle,nu=.49):
    t=np.deg2rad(angle);a=np.cos(t);b=np.sin(t)
    return np.array([a*a-nu*b*b,b*b-nu*a*a,2*(1+nu)*a*b])


def analyze(h=1.7,design='Uniform',skin=.2,adhesive=.1,geometry='Supplied'):
    gate=f'superposition_h{h:g}_{geometry}_{design}_S{skin:g}_A{adhesive:g}.json'
    validation=json.loads((ROOT/'verification'/gate).read_text())
    assert validation.get('accepted') and validation.get('execution_backend')==BACKEND
    prefix='' if geometry=='Supplied' else f'{geometry}_'
    stem=f'{SOLVER_TAG}_h{h:g}_{prefix}{design}_S{skin:g}_A{adhesive:g}'
    paths=[ROOT/'runs'/f'{stem}_{mode}' for mode in BASIS]
    for path in paths:
        assert (path/'checks.json').exists() and (path/'fields.npz').exists(), path
        check=json.loads((path/'checks.json').read_text())
        assert check.get('checks_schema')==2 and check.get('accepted'),path
    meta=json.loads((paths[0]/'input_metadata.json').read_text())
    mesh=np.load(PROJECT/meta['mesh_path']);p,c,r=mesh['points'],mesh['cells'],mesh['region']
    vertices=p[c[:,:4]]
    volume=np.abs(np.linalg.det(vertices[:,1:]-vertices[:,:1]))/6
    wire=np.isin(r,[13,14]);skin_mask=r==1
    weight=np.repeat(volume[wire]/4,4)
    sw=np.repeat(volume[skin_mask]/4,4)
    geocache=ROOT/'cache'/f'interface_{geometry}_h{h:g}.npz'
    if not geocache.exists():
        geo=interface_geometry(p,c,r)
        geocache.parent.mkdir(exist_ok=True)
        np.savez_compressed(geocache,**geo)
    geo=dict(np.load(geocache))
    fields=[np.load(path/'fields.npz') for path in paths]
    ws=np.array([f['stress'][wire].reshape(-1,6) for f in fields])
    we=np.array([f['strain'][wire].reshape(-1,6) for f in fields])
    deltas=[];ta=[];ts=[];adh_s=[];adh_e=[]
    adhesive_mask=r==2
    aw=np.repeat(volume[adhesive_mask]/4,4)
    references=[ROOT/'references'/f'{geometry}_h{h:g}_{mode}' for mode in BASIS]
    bare_mesh=np.load(ROOT/'meshes'/f'bare_{geometry}_h{h:g}.npz')
    assert np.array_equal(bare_mesh['original_element_ids'],np.where(skin_mask)[0])
    assert np.array_equal(bare_mesh['points'],p[bare_mesh['original_node_ids']])
    assert np.array_equal(bare_mesh['original_node_ids'][bare_mesh['cells']],c[skin_mask])
    for path in references:
        assert json.loads((path/'checks.json').read_text())['accepted']
    ref=[np.load(path/'fields.npz')['strain'].reshape(-1,6) for path in references]
    for i,f in enumerate(fields):
        assert f['strain'][skin_mask].reshape(-1,6).shape==ref[i].shape
        deltas.append(f['strain'][skin_mask].reshape(-1,6)-ref[i])
        adh_s.append(f['stress'][adhesive_mask].reshape(-1,6))
        adh_e.append(f['strain'][adhesive_mask].reshape(-1,6))
        ta.append(traction(surface_stress(p,c,f['displacement'],geo,'adhesive',adhesive),geo['normal']))
        ts.append(traction(surface_stress(p,c,f['displacement'],geo,'skin',skin),geo['normal']))
    Q=np.zeros((3,3))
    for i in range(3):
        for j in range(3):
            Q[i,j]=np.sum(sw*np.sum(deltas[i]*deltas[j]*np.array([1,1,1,2,2,2]),axis=1))/sw.sum()
    adhesive_energy=np.zeros((3,3))
    adhesive_distortion=np.zeros((3,3))
    deviator=[]
    for e in adh_e:
        dev=e.copy();dev[:,:3]-=e[:,:3].sum(axis=1)[:,None]/3
        deviator.append(dev)
    for i in range(3):
        for j in range(3):
            adhesive_energy[i,j]=.5*np.sum(aw*np.sum(adh_s[i]*adh_e[j]*np.array([1,1,1,2,2,2]),axis=1))
            adhesive_distortion[i,j]=np.sum(aw*np.sum(deviator[i]*deviator[j]*np.array([1,1,1,2,2,2]),axis=1))/aw.sum()
    adhesive_energy=.5*(adhesive_energy+adhesive_energy.T)
    assert np.min(np.linalg.eigvalsh(Q))>=-1e-12
    assert np.min(np.linalg.eigvalsh(adhesive_energy))>=-1e-12
    assert np.min(np.linalg.eigvalsh(adhesive_distortion))>=-1e-12
    del deltas
    ta,ts=np.array(ta),np.array(ts)
    out=ROOT/'output';out.mkdir(exist_ok=True)
    rows=[]
    loadings=[(f'Angle_{a:03d}',float(a),coefficients(a)) for a in range(0,180,5)]
    loadings.extend([('Equibiaxial_0.5percent',None,np.array([.5,.5,0.])),
                     ('Engineering_shear_1percent',None,np.array([0.,0.,1.]))])
    area=geo['area_mm2'];normal=geo['normal']
    for label,angle,coef in loadings:
        stress=np.einsum('i,ijk->jk',coef,ws);strain=np.einsum('i,ijk->jk',coef,we)
        vm=von_mises(stress);ep=absolute_principal(strain)
        a=np.einsum('i,ijk->jk',coef,ta);s=np.einsum('i,ijk->jk',coef,ts)
        normal_load=np.sum(a*normal,axis=1)
        shear=np.linalg.norm(a-normal_load[:,None]*normal,axis=1)
        mismatch=np.average(np.linalg.norm(a-s,axis=1),weights=area)
        denominator=np.average(.5*(np.linalg.norm(a,axis=1)+np.linalg.norm(s,axis=1)),weights=area)
        rows.append(dict(geometry_scenario=geometry,mesh_h_mm=h,design=design,skin_E_MPa=skin,
                         adhesive_E_MPa=adhesive,loading=label,angle_deg=angle,
                         wire_mean_vm_MPa=float(np.average(vm,weights=weight)),
                         wire_p95_vm_MPa=quantile(vm,weight),
                         wire_p95_absolute_principal_strain=quantile(ep,weight),
                         wire_max_absolute_principal_strain=float(np.max(ep)),
                         adhesive_interface_mean_shear_MPa=float(np.average(shear,weights=area)),
                         adhesive_interface_p95_shear_MPa=quantile(shear,area),
                         adhesive_interface_p95_tensile_MPa=quantile(np.maximum(normal_load,0),area),
                         skin_RMS_strain_perturbation=float(np.sqrt(max(coef@Q@coef,0))),
                         skin_RMS_perturbation_over_1percent=float(np.sqrt(max(coef@Q@coef,0))/.01),
                         adhesive_strain_energy_Nmm=float(coef@adhesive_energy@coef),
                         adhesive_RMS_deviatoric_strain=float(np.sqrt(max(coef@adhesive_distortion@coef,0))),
                         adhesive_energy_per_shared_area_N_per_mm=float(coef@adhesive_energy@coef/area.sum()),
                         area_weighted_relative_traction_mismatch=float(mismatch/max(denominator,1e-30)),
                         shared_interface_area_mm2=float(area.sum())))
    with (out/f'{stem}_responses.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=rows[0]);writer.writeheader();writer.writerows(rows)
    (out/f'{stem}_responses.json').write_text(json.dumps(rows,indent=2))
    diagnostics=dict(configuration=stem,skin_reference='bare_skin_FEM',skin_reference_cases=[str(path.relative_to(ROOT)) for path in references],skin_perturbation_Gram_matrix=Q.tolist(),
                     adhesive_energy_Gram_matrix_Nmm=adhesive_energy.tolist(),
                     adhesive_deviatoric_strain_Gram_matrix=adhesive_distortion.tolist(),
                     interface_area_mm2=float(area.sum()),wire_GP_count=len(weight),
                     maximum_interface_traction_mismatch=max(row['area_weighted_relative_traction_mismatch'] for row in rows))
    (out/f'{stem}_diagnostics.json').write_text(json.dumps(diagnostics,indent=2))
    print(json.dumps(diagnostics),flush=True)
    return rows


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--h',type=float,default=1.7)
    parser.add_argument('--design',default='Uniform')
    parser.add_argument('--skin',type=float,default=.2)
    parser.add_argument('--adhesive',type=float,default=.1)
    parser.add_argument('--geometry',choices=['Supplied','Filled'],default='Supplied')
    a=parser.parse_args()
    analyze(a.h,a.design,a.skin,a.adhesive,a.geometry)
