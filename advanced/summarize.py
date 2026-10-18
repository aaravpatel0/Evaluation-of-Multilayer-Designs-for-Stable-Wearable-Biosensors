"""Inspect complete accepted response grids before producing design conclusions."""
import json,csv,itertools
from model import ROOT

METRICS={'wire':'wire_p95_absolute_principal_strain',
         'skin':'skin_RMS_perturbation_over_1percent',
         'adhesive':'adhesive_RMS_deviatoric_strain'}


def summarize():
    rows=[]
    expected=list(itertools.product(['Uniform','Single','Graded'],[.1,.2,.5],[.05,.1,.5]))
    for design,skin,adhesive in expected:
        path=ROOT/'output'/f'WSL_h1.7_Filled_{design}_S{skin:g}_A{adhesive:g}_responses.json'
        assert path.exists(),f'Missing planned configuration: {path.name}'
        diagnostics=json.loads(path.with_name(path.name.replace('_responses.json','_diagnostics.json')).read_text())
        assert diagnostics.get('skin_reference')=='bare_skin_FEM','Reanalyze against matched bare-skin FE references before final tradeoff selection.'
        responses=json.loads(path.read_text())
        assert len(responses)==38
        assert {r['angle_deg'] for r in responses if r['angle_deg'] is not None}==set(range(0,180,5))
        assert {r['loading'] for r in responses if r['angle_deg'] is None}=={
            'Equibiaxial_0.5percent','Engineering_shear_1percent'}
        assert all(r['design']==design and r['skin_E_MPa']==skin and
                   r['adhesive_E_MPa']==adhesive and r['geometry_scenario']=='Filled' and
                   r['mesh_h_mm']==1.7 for r in responses)
        rows.extend(responses)
    with (ROOT/'output/All_Directional_Responses.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=rows[0]);writer.writeheader();writer.writerows(rows)
    directional=[r for r in rows if r['angle_deg'] is not None]
    options=[]
    for design,adhesive in itertools.product(['Uniform','Single','Graded'],[.05,.1,.5]):
        selected=[r for r in directional if r['design']==design and r['adhesive_E_MPa']==adhesive]
        assert len(selected)==108
        option=dict(design=design,adhesive_E_MPa=adhesive)
        for name,key in METRICS.items():
            worst=max(selected,key=lambda r:r[key])
            option[f'worst_{name}']=worst[key]
            option[f'worst_{name}_case']=dict(skin_E_MPa=worst['skin_E_MPa'],angle_deg=worst['angle_deg'])
        options.append(option)
    for option in options:
        option['sampled_Pareto_nondominated']=not any(
            all(other[f'worst_{name}']<=option[f'worst_{name}'] for name in METRICS) and
            any(other[f'worst_{name}']<option[f'worst_{name}'] for name in METRICS)
            for other in options if other is not option)
    summary=dict(material_configurations=27,basis_cases=81,directional_responses=len(directional),
                 additional_biaxial_shear_responses=len(rows)-len(directional),
                 options=options,scope='Filled-contact, medium mesh; sampled extrema; refinement not yet evaluated')
    (ROOT/'output/Tradeoff_Summary_Medium.json').write_text(json.dumps(summary,indent=2))
    return summary


if __name__=='__main__':
    print(json.dumps(summarize(),indent=2))
