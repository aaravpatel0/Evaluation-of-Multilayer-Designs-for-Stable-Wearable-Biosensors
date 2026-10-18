"""Defect correction of the unchanged linear FE equations, with auditable field sums."""
import argparse,json
from pathlib import Path
import numpy as np
from model import ROOT,PROJECT,write_deck,execute,read_fields,check_fields,boundary_nodes


def refine(dest,maxsteps=3,manufactured_initial=None):
    dest=Path(dest)
    meta=json.loads((dest/'input_metadata.json').read_text())
    mesh_path=PROJECT/meta['mesh_path'];mesh=np.load(mesh_path)
    if manufactured_initial is None:
        data=read_fields(dest)
    else:
        assert meta.get('manufactured_verification'),'Injected fields are allowed only in a labeled verification problem.'
        data={k:v.copy() for k,v in manufactured_initial.items()}
    initial=check_fields(mesh,meta,data)
    (dest/'initial_checks.json').write_text(json.dumps(initial,indent=2))
    np.savez_compressed(dest/'initial_fields.npz',**data)
    history=[dict(iteration=0,**initial)]
    perimeter,pin=boundary_nodes(mesh['points'],mesh['cells'],mesh['region'])
    fixed=np.zeros_like(data['displacement'],dtype=bool);fixed[perimeter,:2]=True;fixed[pin,2]=True
    for step in range(1,maxsteps+1):
        if history[-1]['accepted']:
            break
        r=data['forces']
        scale=min(max(np.linalg.norm(r[fixed])/max(np.linalg.norm(r[~fixed]),1e-30),1.),1e6)
        load=np.where(fixed,0.,-scale*r)
        correction=dest/f'correction_{step:02d}'
        write_deck(correction,mesh_path,(0.,0.,0.),design=meta['design'],skin_E=meta['skin_E_MPa'],
                   adhesive_E=meta['adhesive_E_MPa'],homogeneous=meta['homogeneous'],nu=meta['nu'],
                   geometry_scenario=meta.get('geometry_scenario','Supplied'),
                   verification_contrast=meta.get('verification_contrast',1.),nodal_loads=load)
        execute(correction)
        delta=read_fields(correction)
        # RF includes K*du at loaded free DOFs, verified with a separate point-load cube.
        for key in data:
            data[key]+=delta[key]/scale
        checks=check_fields(mesh,meta,data)
        checks.update(iteration=step,correction_load_scale=scale,
                      correction_free_DOF_relative_residual=float(np.linalg.norm((delta['forces']-load)[~fixed])/max(np.linalg.norm(load),1e-30)))
        history.append(checks)
        (dest/'residual_refinement_history.json').write_text(json.dumps(history,indent=2))
        print(dest.name,'REFINEMENT',step,json.dumps(checks),flush=True)
        if checks['free_DOF_force_relative_residual']>1.05*history[-2]['free_DOF_force_relative_residual']:
            raise RuntimeError('Residual correction diverged; no corrected fields accepted.')
    assert history[-1]['accepted'],history[-1]
    final=dict(history[-1],residual_correction_steps=len(history)-1,
               field_construction='Initial linear solve plus zero-prescribed-displacement residual-correction solves')
    np.savez_compressed(dest/'fields.npz',**data)
    (dest/'checks.json').write_text(json.dumps(final,indent=2))
    return final


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('case');parser.add_argument('--steps',type=int,default=3)
    args=parser.parse_args();refine(args.case,args.steps)
