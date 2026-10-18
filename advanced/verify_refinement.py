"""Manufactured numerical-error test, separate from research simulations."""
import json
import numpy as np
from model import ROOT,read_fields,write_deck,execute,boundary_nodes
from residual_refinement import refine


def main():
    base=ROOT/'verification/nu0.3_XX'
    perturb=ROOT/'verification/cload_semantics'
    mesh_path=ROOT/'verification/cube.npz';mesh=np.load(mesh_path)
    p,c,r=mesh['points'],mesh['cells'],mesh['region']
    perimeter,pin=boundary_nodes(p,c,r)
    free_node=int(np.setdiff1d(np.arange(len(p)),perimeter)[0])
    loads=np.zeros_like(p);loads[free_node,0]=.001
    write_deck(perturb,mesh_path,(0,0,0),homogeneous=True,skin_E=1,nu=.3,nodal_loads=loads)
    execute(perturb)
    load_fields=read_fields(perturb)
    fixed=np.zeros_like(p,dtype=bool);fixed[perimeter,:2]=True;fixed[pin,2]=True
    error=float(np.linalg.norm((load_fields['forces']-loads)[~fixed])/np.linalg.norm(loads))
    assert error<2e-5,error
    (ROOT/'verification/cload_semantics_verification.json').write_text(json.dumps(dict(
        loaded_node=free_node+1,applied_force_N=.001,reported_internal_force_N=float(load_fields['forces'][free_node,0]),
        free_DOF_force_minus_applied_load_relative_error=error),indent=2))
    meta=json.loads((base/'input_metadata.json').read_text())
    other=json.loads((perturb/'input_metadata.json').read_text())
    assert meta['mesh_sha256']==other['mesh_sha256']
    exact=read_fields(base);delta=load_fields
    injected={key:exact[key]+.02*delta[key] for key in exact}
    dest=ROOT/'verification/manufactured_refinement';dest.mkdir(exist_ok=True)
    meta['manufactured_verification']=True
    meta['manufactured_error_definition']='Verified XX cube fields plus 0.02 times the independently solved zero-BC point-load cube fields'
    (dest/'input_metadata.json').write_text(json.dumps(meta,indent=2))
    final=refine(dest,3,manufactured_initial=injected)
    actual=np.load(dest/'fields.npz')
    errors={key:float(np.linalg.norm(actual[key]-exact[key])/max(np.linalg.norm(exact[key]),1e-30)) for key in exact}
    assert max(errors.values())<2e-5,errors
    report=dict(purpose='Manufactured numerical-error verification, not research data',
                recovery_relative_errors=errors,final_checks=final)
    (ROOT/'verification/residual_refinement_verification.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
