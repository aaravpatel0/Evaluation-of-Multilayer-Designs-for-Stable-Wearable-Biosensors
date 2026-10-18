"""Sequential resumable basis study, with a direct assembly validation gate."""
import argparse, json, time, itertools
import numpy as np
from model import ROOT, PROJECT, BASIS, SOLVER_TAG, BACKEND, write_deck, execute, parse_and_check


def case(h, design, skin, adhesive, mode, loading=None, geometry='Supplied'):
    prefix='' if geometry=='Supplied' else f'{geometry}_'
    dest = ROOT/'runs'/f'{SOLVER_TAG}_h{h:g}_{prefix}{design}_S{skin:g}_A{adhesive:g}_{mode}'
    mesh=PROJECT/f'detailed/meshes/h{h:g}/mesh.npz' if geometry=='Supplied' else ROOT/f'meshes/filled/h{h:g}/mesh.npz'
    write_deck(dest, mesh,
               BASIS[mode] if loading is None else loading,
               design=design, skin_E=skin, adhesive_E=adhesive,geometry_scenario=geometry)
    fresh=execute(dest)
    if fresh or not (dest/'fields.npz').exists() or not (dest/'checks.json').exists():
        parse_and_check(dest)
    checks = json.loads((dest/'checks.json').read_text())
    if checks.get('checks_schema')!=2:
        checks=parse_and_check(dest)
    assert checks['accepted']
    assert checks['relative_energy_error'] < 5e-4
    print('COMPLETED', dest.name, json.dumps(checks), flush=True)
    return dest


def direct_gate(h=1.7,geometry='Supplied'):
    basis = [case(h, 'Uniform', .2, .1, mode,geometry=geometry) for mode in BASIS]
    coef = np.array([.255, .255, 1.49])
    direct = case(h, 'Uniform', .2, .1, 'Direct45', .01*coef,geometry=geometry)
    data = np.load(direct/'fields.npz')
    errors = {}
    for key in ['displacement', 'forces', 'stress', 'strain']:
        prediction = sum(a*np.load(path/'fields.npz')[key] for a,path in zip(coef,basis))
        target = data[key]
        errors[key] = float(np.linalg.norm(prediction-target)/np.linalg.norm(target))
    report = dict(mesh_h_mm=h, design='Uniform',geometry_scenario=geometry, coefficients=coef.tolist(),
                  relative_field_errors=errors, tolerance=2e-5,precision='double',execution_backend=BACKEND)
    report['accepted']=bool(max(errors.values()) < report['tolerance'])
    name='assembly_superposition.json' if geometry=='Supplied' else f'assembly_superposition_{geometry}.json'
    (ROOT/'verification'/name).write_text(json.dumps(report, indent=2))
    assert max(errors.values()) < report['tolerance'], report
    print('ASSEMBLY SUPERPOSITION GATE PASSED', json.dumps(report), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--phase', choices=['pilot','factorial'], default='pilot')
    parser.add_argument('--geometry',choices=['Supplied','Filled'],default='Supplied')
    args = parser.parse_args()
    verified = ROOT/'verification/verification_summary.json'
    assert verified.exists(), 'Run verify_basis.py first.'
    direct_gate(geometry=args.geometry)
    if args.phase == 'pilot':
        return
    start = time.time()
    configs = list(itertools.product(['Uniform','Single','Graded'], [.1,.2,.5], [.05,.1,.5]))
    # Nominal material cases first, then the factorial uncertainty/design matrix.
    configs.sort(key=lambda c: (not (c[1] == .2 and c[2] == .1), c))
    completed = []
    for design, skin, adhesive in configs:
        for mode in BASIS:
            dest = case(1.7, design, skin, adhesive, mode,geometry=args.geometry)
            completed.append(dest.name)
            (ROOT/f'progress_{args.geometry}.json').write_text(json.dumps(dict(
                completed=completed, planned_basis_cases=81, elapsed_seconds=time.time()-start), indent=2))
    print('FACTORIAL BASIS STUDY COMPLETE', len(completed), flush=True)


if __name__ == '__main__':
    main()
