"""Refine nominal architectures, supplied-contact control, and sampled worst cases."""
import csv,json
from model import ROOT,BASIS
from run_study import case,direct_gate
from postprocess import analyze
from summarize import summarize,METRICS


def targets():
    summarize()  # Fails until the full accepted material matrix has been analyzed.
    configs={('Supplied','Uniform',.2,.1)}
    configs.update(('Filled',d,.2,.1) for d in ['Uniform','Single','Graded'])
    with (ROOT/'output/All_Directional_Responses.csv').open(newline='') as f:
        rows=[r for r in csv.DictReader(f) if r['angle_deg']]
    for metric in METRICS.values():
        worst=max(rows,key=lambda r:float(r[metric]))
        configs.add(('Filled',worst['design'],float(worst['skin_E_MPa']),float(worst['adhesive_E_MPa'])))
    return sorted(configs)


def main():
    configs=targets()
    (ROOT/'output/Refinement_Targets.json').write_text(json.dumps(configs,indent=2))
    completed=[]
    for geometry,design,skin,adhesive in configs:
        for mode in BASIS:
            case(1.2,design,skin,adhesive,mode,geometry=geometry)
        direct_gate(1.2,geometry=geometry,design=design,skin=skin,adhesive=adhesive)
        analyze(1.2,design,skin,adhesive,geometry)
        completed.append((geometry,design,skin,adhesive))
        (ROOT/'progress_refinement.json').write_text(json.dumps(dict(
            completed_configurations=completed,planned_configurations=configs),indent=2))
    direct_gate(1.2,geometry='Filled')
    print('REFINEMENT COMPLETE',len(configs),flush=True)


if __name__=='__main__':
    main()
