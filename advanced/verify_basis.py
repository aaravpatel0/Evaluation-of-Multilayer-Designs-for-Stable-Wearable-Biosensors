"""Analytical all-tensor cube tests and direct mixed-load superposition verification."""
import json
import numpy as np
import gmsh
from model import ROOT, BASIS, write_deck, execute, parse_and_check


def main():
    out = ROOT/'verification'; out.mkdir(exist_ok=True)
    gmsh.initialize(); gmsh.option.setNumber('General.Terminal', 0)
    gmsh.model.occ.addBox(-.5, -.5, 0, 1, 1, 1); gmsh.model.occ.synchronize()
    gmsh.option.setNumber('Mesh.MeshSizeMax', .4)
    gmsh.option.setNumber('Mesh.MeshSizeMin', .4)
    gmsh.model.mesh.generate(3)
    gmsh.option.setNumber('Mesh.SecondOrderLinear', 1); gmsh.model.mesh.setOrder(2)
    nodes, xyz, _ = gmsh.model.mesh.getNodes()
    _, _, connectivity = gmsh.model.mesh.getElements(3)
    raw = np.array(connectivity[0]).reshape(-1, 10)[:,[0,1,2,3,4,5,6,7,9,8]]
    order = np.argsort(nodes); p = np.array(xyz).reshape(-1,3)[order]
    c = np.searchsorted(nodes[order], raw)
    gmsh.finalize()
    mesh_path = out/'cube.npz'
    np.savez_compressed(mesh_path, points=p, cells=c, region=np.ones(len(c), dtype=int))
    report = []
    for nu in [.3, .49]:
        fields = []
        for name, loading in BASIS.items():
            dest = out/f'nu{nu}_{name}'
            write_deck(dest, mesh_path, loading, homogeneous=True, skin_E=1, nu=nu)
            execute(dest); checks = parse_and_check(dest)
            data = np.load(dest/'fields.npz')
            exx, eyy, gamma = loading
            exact_s = np.array([(exx+nu*eyy)/(1-nu*nu), (eyy+nu*exx)/(1-nu*nu), 0,
                                gamma/(2*(1+nu)), 0, 0])
            exact_e = np.array([exx, eyy, -nu/(1-nu)*(exx+eyy), .5*gamma, 0, 0])
            stress_error = float(np.max(abs(data['stress']-exact_s)))
            strain_error = float(np.max(abs(data['strain']-exact_e)))
            assert stress_error < 2e-7 and strain_error < 2e-7, (stress_error,strain_error)
            report.append(dict(nu=nu, basis=name, stress_max_absolute_error_MPa=stress_error,
                               strain_max_absolute_error=strain_error, **checks))
            fields.append({key: data[key] for key in ['stress','strain','displacement','forces']})
        # Uniaxial principal extension at 45 degrees, with nominal transverse contraction.
        coefficients = np.array([.5*(1-nu), .5*(1-nu), 1+nu])
        mixed = .01*coefficients
        dest = out/f'nu{nu}_direct45'
        write_deck(dest, mesh_path, mixed, homogeneous=True, skin_E=1, nu=nu)
        execute(dest); checks = parse_and_check(dest)
        direct = np.load(dest/'fields.npz')
        errors = {}
        for key in fields[0]:
            prediction = sum(coef*field[key] for coef,field in zip(coefficients, fields))
            errors[key] = float(np.linalg.norm(prediction-direct[key])/max(np.linalg.norm(direct[key]),1e-30))
            assert errors[key] < 2e-5, (key, errors[key])
        report.append(dict(nu=nu, mode='direct_45_degrees', relative_superposition_errors=errors, **checks))
    (out/'verification_summary.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    main()
