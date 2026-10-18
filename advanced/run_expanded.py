"""Run the pre-specified material matrix, retaining geometric-contact comparison."""
import itertools,json,time,argparse
from model import ROOT,BASIS
from run_study import case,direct_gate
from postprocess import analyze


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--defer-analysis',action='store_true',help='Complete verified FE solves first, then run bare references and reanalyze.py.')
    args=parser.parse_args()
    start=time.time()
    verified=json.loads((ROOT/'verification/independent_high_contrast.json').read_text())
    assert {r['contrast'] for r in verified}=={10.,392500.,1570000.}
    assert all(r['accepted'] and r['independent_displacement_relative_error']<2e-5 for r in verified)
    # Refresh the accepted direct gate using the current checker and cached solves.
    direct_gate(geometry='Supplied')
    completed=[]
    for design in ['Uniform','Single','Graded']:
        for mode in BASIS:
            dest=case(1.7,design,.2,.1,mode,geometry='Supplied')
            completed.append(dest.name)
        direct_gate(geometry='Supplied',design=design)
        if not args.defer_analysis:
            analyze(design=design,geometry='Supplied')
        (ROOT/'progress_expanded.json').write_text(json.dumps(dict(
            completed_basis_cases=completed,elapsed_seconds=time.time()-start,
            phase='supplied_contact_comparison',planned_medium_mesh_basis_cases=90),indent=2))
    direct_gate(geometry='Filled')
    configs=list(itertools.product(['Uniform','Single','Graded'],[.1,.2,.5],[.05,.1,.5]))
    configs.sort(key=lambda c:(not(c[1]==.2 and c[2]==.1),c))
    for design,skin,adhesive in configs:
        for mode in BASIS:
            dest=case(1.7,design,skin,adhesive,mode,geometry='Filled')
            completed.append(dest.name)
        direct_gate(geometry='Filled',design=design,skin=skin,adhesive=adhesive)
        if not args.defer_analysis:
            analyze(design=design,skin=skin,adhesive=adhesive,geometry='Filled')
        (ROOT/'progress_expanded.json').write_text(json.dumps(dict(
            completed_basis_cases=completed,elapsed_seconds=time.time()-start,
            phase='filled_contact_material_matrix',planned_medium_mesh_basis_cases=90),indent=2))
    print('MEDIUM-MESH STUDY COMPLETE; refinement and manuscript remain.',len(completed),flush=True)


if __name__=='__main__':
    main()
