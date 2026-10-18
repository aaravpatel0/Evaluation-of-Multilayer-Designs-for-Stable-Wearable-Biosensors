"""Require complete accepted configurations and refinements before manuscript results."""
import csv,json,itertools,hashlib
from functools import lru_cache
import numpy as np
from model import ROOT,PROJECT,check_fields
from summarize import summarize,METRICS


def responses(h,geometry,design,skin,adhesive):
    prefix='' if geometry=='Supplied' else 'Filled_'
    path=ROOT/'output'/f'WSL_h{h:g}_{prefix}{design}_S{skin:g}_A{adhesive:g}_responses.json'
    rows=json.loads(path.read_text())
    assert len(rows)==38
    return rows


def main():
    summary=summarize()
    targets=json.loads((ROOT/'output/Refinement_Targets.json').read_text())
    assert len(targets)>=4
    comparisons=[]
    for geometry,design,skin,adhesive in targets:
        medium=responses(1.7,geometry,design,skin,adhesive)
        fine=responses(1.2,geometry,design,skin,adhesive)
        comparison=dict(geometry=geometry,design=design,skin_E_MPa=skin,adhesive_E_MPa=adhesive)
        for label,key in METRICS.items():
            a=max(r[key] for r in medium if r['angle_deg'] is not None)
            b=max(r[key] for r in fine if r['angle_deg'] is not None)
            comparison[label]=dict(medium_sampled_max=a,fine_sampled_max=b,
                                    relative_change_percent=100*abs(b/a-1))
        comparisons.append(comparison)
    required=[(1.7,'Supplied',d,.2,.1) for d in ['Uniform','Single','Graded']]
    required.extend((1.7,'Filled',d,s,a) for d,s,a in itertools.product(['Uniform','Single','Graded'],[.1,.2,.5],[.05,.1,.5]))
    required.extend((1.2,*target) for target in targets)
    checks=[];correction_solves=0
    @lru_cache(maxsize=4)
    def load_mesh(path):
        return dict(np.load(path))
    for h,geometry,design,skin,adhesive in required:
        validation=json.loads((ROOT/'verification'/f'superposition_h{h:g}_{geometry}_{design}_S{skin:g}_A{adhesive:g}.json').read_text())
        assert validation['accepted'] and max(validation['relative_field_errors'].values())<2e-5
        prefix='' if geometry=='Supplied' else 'Filled_'
        for mode in ['XX','YY','XY','Direct45']:
            directory=ROOT/'runs'/f'WSL_h{h:g}_{prefix}{design}_S{skin:g}_A{adhesive:g}_{mode}'
            assert (directory/'checks.json').exists(),directory
            check=json.loads((directory/'checks.json').read_text())
            assert check.get('checks_schema')==2 and check.get('accepted'),directory
            assert (directory/'fields.npz').exists(),directory
            execution=json.loads((directory/'execution.json').read_text())
            assert execution['job_finished'] and execution['returncode']==0
            assert execution['deck_sha256']==hashlib.sha256((directory/'job.inp').read_bytes()).hexdigest(),directory
            meta=json.loads((directory/'input_metadata.json').read_text())
            with np.load(directory/'fields.npz') as fields:
                rechecked=check_fields(load_mesh(PROJECT/meta['mesh_path']),meta,fields)
            assert rechecked['accepted'],(directory,rechecked)
            checks.append(rechecked)
            for correction in directory.glob('correction_*/execution.json'):
                status=json.loads(correction.read_text())
                assert status['job_finished'] and status['returncode']==0
                correction_solves+=1
    assert len(checks)==4*len(required)
    reference_checks=[]
    for geometry in ['Supplied','Filled']:
        for h in [1.7,1.2]:
            for mode in ['XX','YY','XY']:
                directory=ROOT/'references'/f'{geometry}_h{h:g}_{mode}'
                meta=json.loads((directory/'input_metadata.json').read_text())
                execution=json.loads((directory/'execution.json').read_text())
                assert execution['job_finished'] and execution['returncode']==0
                assert execution['deck_sha256']==hashlib.sha256((directory/'job.inp').read_bytes()).hexdigest()
                with np.load(directory/'fields.npz') as fields:
                    rechecked=check_fields(load_mesh(PROJECT/meta['mesh_path']),meta,fields)
                assert rechecked['accepted'],(directory,rechecked)
                reference_checks.append(rechecked)
    for gate in ['assembly_superposition.json','assembly_superposition_Filled.json']:
        record=json.loads((ROOT/'verification'/gate).read_text())
        assert record.get('accepted') and record['execution_backend']=='WSL'
        assert max(record['relative_field_errors'].values())<2e-5
    summary['mesh_comparisons']=comparisons
    summary['maximum_mesh_changes_percent']={label:max(r[label]['relative_change_percent'] for r in comparisons) for label in METRICS}
    summary['accepted_assembly_solves']=len(checks)
    summary['auxiliary_residual_correction_solves']=correction_solves
    summary['bare_skin_reference_solves']=len(reference_checks)
    summary['maximum_bare_skin_reference_residual']=max(a['free_DOF_force_relative_residual'] for a in reference_checks)
    summary['maximum_free_DOF_force_residual']=max(c['free_DOF_force_relative_residual'] for c in checks)
    summary['maximum_relative_energy_error']=max(c['relative_energy_error'] for c in checks)
    summary['scope']='Accepted medium-mesh material/direction screen with nominal and sampled-worst-case refined comparisons; no physical calibration'
    summary['supplied_contact_nominal']={design:responses(1.7,'Supplied',design,.2,.1) for design in ['Uniform','Single','Graded']}
    summary['filled_contact_nominal']={design:responses(1.7,'Filled',design,.2,.1) for design in ['Uniform','Single','Graded']}
    (ROOT/'output/Final_Study_Summary.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps({k:summary[k] for k in ['accepted_assembly_solves','maximum_mesh_changes_percent','maximum_free_DOF_force_residual','maximum_relative_energy_error']},indent=2))


if __name__=='__main__':
    main()
