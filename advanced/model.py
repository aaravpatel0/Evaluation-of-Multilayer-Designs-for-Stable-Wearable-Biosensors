"""Verified affine-perimeter 3D basis loads for the original biosensor mesh."""
from pathlib import Path
import sys, json, hashlib, os, subprocess, time, re
import numpy as np

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
sys.path.append(str(PROJECT/'detailed'))
from run_ccx import CCX, properties, lineset
from parse_ccx import blocks

BASIS = {'XX': (.01, 0., 0.), 'YY': (0., .01, 0.), 'XY': (0., 0., .01)}
SOLVER_NAME = os.environ.get('BIOSENSOR_SOLVER','SPOOLES')
assert SOLVER_NAME in ['SPOOLES','PARDISO']
BACKEND=os.environ.get('BIOSENSOR_BACKEND','WSL')
WSL_DISTRO=os.environ.get('BIOSENSOR_WSL_DISTRO','Ubuntu-22.04')
WSL_RUN_ROOT=os.environ.get('BIOSENSOR_WSL_RUN_ROOT','/tmp/biosensor_advanced_cases')
SOLVER_TAG = 'WSL' if BACKEND=='WSL' else ('SPL64' if SOLVER_NAME=='SPOOLES' else 'D64')
CCX_ADVANCED = CCX.with_name('ccx_dynamic_i8.exe' if SOLVER_NAME=='SPOOLES' else 'ccx_dynamic.exe')
SOLVER_CONFIG = {'OMP_NUM_THREADS':'4','MKL_NUM_THREADS':'4',
                 'MKL_INTERFACE_LAYER':'ILP64' if SOLVER_NAME=='SPOOLES' else 'LP64',
                 'CCX_NPROC_RESULTS':'4','OPENBLAS_NUM_THREADS':'4'}
if BACKEND=='WSL':
    SOLVER_CONFIG={'OMP_NUM_THREADS':'4','CCX_NPROC_RESULTS':'4'}
MKL_DIR = Path(os.environ.get('MKL_RUNTIME_DIR',
    'C:/Program Files/ANSYS Inc/ANSYS Student/v261/artemis/LumericalFDTD/bin'))


def affine_displacement(points, loading):
    exx, eyy, gamma = loading
    return np.column_stack((exx*points[:, 0] + .5*gamma*points[:, 1],
                            eyy*points[:, 1] + .5*gamma*points[:, 0]))


def boundary_nodes(points, cells, regions):
    from scipy.spatial import ConvexHull
    skin = np.unique(cells[regions == 1])
    xy = points[skin, :2]
    # This supplied slab has a convex rounded footprint. Constrain its projected
    # outer contour through the thickness, including rounded corners, rather than
    # treating only x/y extrema as the whole perimeter. Filleted top/bottom edge
    # nodes lying inside that contour remain unconstrained.
    hull = ConvexHull(xy)
    on_contour = np.zeros(len(skin), dtype=bool)
    for equation in hull.equations:
        on_contour |= abs(xy @ equation[:2]+equation[2]) < 1e-6
    perimeter = skin[on_contour]
    target = points[skin].min(axis=0)
    pin = int(perimeter[np.argmin(np.linalg.norm(points[perimeter]-target, axis=1))])
    assert len(perimeter) > 8 and pin in perimeter
    return perimeter, pin


def write_deck(dest, mesh_path, loading, design='Uniform', skin_E=.2, adhesive_E=.1,
               homogeneous=False, nu=.49, geometry_scenario='Supplied',verification_contrast=1.,nodal_loads=None):
    dest = Path(dest); dest.mkdir(parents=True, exist_ok=True)
    mesh_path = Path(mesh_path).resolve()
    mesh = np.load(mesh_path)
    p, c, region = mesh['points'], mesh['cells'], mesh['region']
    groups=region if verification_contrast==1 else np.where(p[c[:,:4]].mean(axis=1)[:,0]>0,2,1)
    assert verification_contrast==1 or homogeneous
    perimeter, pin = boundary_nodes(p, c, region)
    prescribed = affine_displacement(p, loading)
    meta = dict(mesh_path=str(mesh_path.relative_to(PROJECT)), design=design,geometry_scenario=geometry_scenario,
                loading=list(loading), skin_E_MPa=skin_E, adhesive_E_MPa=adhesive_E,
                homogeneous=homogeneous, nu=nu, nodes=len(p), elements=len(c),
                perimeter_nodes=len(perimeter), z_reference_node=pin+1,
                mesh_sha256=hashlib.sha256(mesh_path.read_bytes()).hexdigest(),linear_solver=SOLVER_NAME,
                executable_name='/usr/bin/ccx' if BACKEND=='WSL' else CCX_ADVANCED.name)
    meta['execution_backend']=BACKEND
    meta['verification_contrast']=verification_contrast
    meta['has_nodal_loads']=nodal_loads is not None
    with (dest/'job.inp').open('w') as f:
        f.write('*HEADING\nAffine skin perimeter, mm N MPa, linear screening study\n*NODE,NSET=NALL\n')
        for i, xyz in enumerate(p, 1):
            f.write(f'{i},'+','.join(f'{v:.12g}' for v in xyz)+'\n')
        for r in sorted(set(groups)):
            f.write(f'*ELEMENT,TYPE=C3D10,ELSET=PART{r}\n')
            for i in np.where(groups == r)[0]:
                f.write(f'{i+1},'+','.join(str(int(v+1)) for v in c[i])+'\n')
            E, poisson = (skin_E, nu) if homogeneous or r == 1 else properties(r, design, adhesive=adhesive_E)
            if verification_contrast!=1 and r==2:
                E*=verification_contrast
            f.write(f'*MATERIAL,NAME=M{r}\n*ELASTIC\n{E:.12g},{poisson:.12g}\n')
            f.write(f'*SOLID SECTION,ELSET=PART{r},MATERIAL=M{r}\n')
        lineset(f, 'ELSET', 'ALL', np.arange(len(c))+1)
        f.write(f'*STEP\n*STATIC,SOLVER={SOLVER_NAME}\n*BOUNDARY\n')
        for i in perimeter:
            for axis in range(2):
                f.write(f'{i+1},{axis+1},{axis+1},{prescribed[i,axis]:.12g}\n')
        f.write(f'{pin+1},3,3,0.\n')
        if nodal_loads is not None:
            assert nodal_loads.shape==p.shape
            f.write('*CLOAD\n')
            for node,axis in np.argwhere(nodal_loads!=0):
                f.write(f'{node+1},{axis+1},{nodal_loads[node,axis]:.12g}\n')
        f.write('*NODE PRINT,NSET=NALL\nU,RF\n*EL PRINT,ELSET=ALL\nS,E\n*END STEP\n')
    meta['deck_sha256'] = hashlib.sha256((dest/'job.inp').read_bytes()).hexdigest()
    (dest/'input_metadata.json').write_text(json.dumps(meta, indent=2))
    return dest


def execute(dest):
    dest = Path(dest)
    expected = json.loads((dest/'input_metadata.json').read_text())['deck_sha256']
    if (dest/'execution.json').exists():
        old = json.loads((dest/'execution.json').read_text())
        if old.get('job_finished') and old.get('deck_sha256') == expected and old.get('solver_environment') == SOLVER_CONFIG and old.get('execution_backend')==BACKEND and ((dest/'fields.npz').exists() or (dest/'job.dat').exists()):
            return False
    env = os.environ.copy()
    env.update(SOLVER_CONFIG)
    env['PATH']=str(MKL_DIR)+os.pathsep+env.get('PATH','')
    start = time.time()
    if BACKEND=='WSL':
        absolute=dest.resolve().as_posix()
        linux_dest='/mnt/'+absolute[0].lower()+absolute[2:]
        native_dest=WSL_RUN_ROOT+'/'+dest.name+'_'+expected[:12]
        # Fortran's line-by-line output is very slow on the Windows-mounted drive.
        # Solve in native ext4, then copy complete result files back in bulk.
        subprocess.run(['wsl','-d',WSL_DISTRO,'--','mkdir','-p',native_dest],check=True)
        subprocess.run(['wsl','-d',WSL_DISTRO,'--','cp','--',linux_dest+'/job.inp',native_dest+'/job.inp'],check=True)
        command=['wsl','-d',WSL_DISTRO,'--cd',native_dest,'--','env',
                 'OMP_NUM_THREADS=4','CCX_NPROC_RESULTS=4','ccx','-i','job']
    else:
        command=[str(CCX_ADVANCED),'-i','job']
    with (dest/'solver.log').open('w') as f:
        run = subprocess.run(command, cwd=dest, env=env, stdout=f, stderr=subprocess.STDOUT)
    if BACKEND=='WSL':
        for filename in ['job.dat','job.sta','job.cvg','job.frd']:
            subprocess.run(['wsl','-d',WSL_DISTRO,'--','cp','--',native_dest+'/'+filename,linux_dest+'/'+filename],check=True)
    log = (dest/'solver.log').read_text(errors='replace')
    result = dict(returncode=run.returncode, elapsed_seconds=time.time()-start,
                  job_finished='Job finished' in log, deck_sha256=expected,solver_environment=SOLVER_CONFIG,
                  execution_backend=BACKEND,command=command,
                  error_lines=[line for line in log.splitlines() if '*ERROR' in line])
    (dest/'execution.json').write_text(json.dumps(result, indent=2))
    assert result['job_finished'] and not result['error_lines'] and run.returncode == 0, log[-4000:]
    assert SOLVER_NAME in log.upper(),'Requested solver not confirmed in solver log.'
    return True


def read_fields(dest):
    dest = Path(dest)
    meta = json.loads((dest/'input_metadata.json').read_text())
    mesh = np.load(PROJECT/meta['mesh_path'])
    p, c = mesh['points'], mesh['cells']
    with (dest/'job.dat').open(errors='replace') as f:
        final_time = None
        for line in f:
            match = re.search(r'and time\s+([\d.Ee+\-]+)', line)
            if match:
                final_time = float(match[1])
    assert final_time is not None and abs(final_time-1) < 1e-8, final_time
    raw = blocks(dest/'job.dat')
    stress = raw['stresses', 'all']; strain = raw['strains', 'all']
    assert np.array_equal(stress[:, :2], strain[:, :2])
    assert stress.shape == (4*len(c), 8), stress.shape
    order = np.lexsort((stress[:, 1], stress[:, 0]))
    s = stress[order, 2:].reshape(len(c), 4, 6)
    e = strain[order, 2:].reshape(len(c), 4, 6)
    assert np.array_equal(stress[order, 0], np.repeat(np.arange(1, len(c)+1), 4))
    assert np.array_equal(stress[order, 1], np.tile(np.arange(1, 5), len(c)))
    displacement = raw['displacements', 'nall']; force = raw['forces', 'nall']
    assert np.array_equal(displacement[:, 0], np.arange(1, len(p)+1))
    assert np.array_equal(force[:, 0], displacement[:, 0])
    u, reaction = displacement[:, 1:], force[:, 1:]
    return dict(displacement=u,forces=reaction,stress=s,strain=e)


def check_fields(mesh,meta,fields):
    p,c=mesh['points'],mesh['cells']
    u,reaction,s,e=[fields[k] for k in ['displacement','forces','stress','strain']]
    vertices = p[c[:, :4]]
    vol = np.abs(np.linalg.det(vertices[:, 1:]-vertices[:, :1]))/6
    assert min(vol) > 0 and all(np.isfinite(a).all() for a in [s,e,u,reaction])
    # Tensor shear strains are counted twice in sigma:epsilon.
    density = .5*np.sum(s*e*np.array([1,1,1,2,2,2]), axis=2)
    internal = float(np.sum(vol*density.mean(axis=1)))
    perimeter, pin = boundary_nodes(p, c, mesh['region'])
    constrained = np.zeros_like(u,dtype=bool)
    constrained[perimeter,:2] = True; constrained[pin,2] = True
    # RF at free DOFs is a residual, not external work. Including it in the
    # energy sum would make an inaccurate solve appear energy-consistent.
    external = float(.5*np.sum((u*reaction)[constrained]))
    residual_work = float(.5*np.sum((u*reaction)[~constrained]))
    free_residual = np.linalg.norm(reaction[~constrained])/max(np.linalg.norm(reaction[constrained]),1e-30)
    energy_error = abs(internal-external)/max(abs(external), 1e-30)
    force_error = np.linalg.norm(reaction.sum(axis=0))/max(np.linalg.norm(reaction), 1e-30)
    moment = np.cross(p-p.mean(axis=0), reaction)
    moment_error = np.linalg.norm(moment.sum(axis=0))/max(np.linalg.norm(moment), 1e-30)
    bc_error = float(np.max(abs(u[perimeter,:2]-affine_displacement(p,meta['loading'])[perimeter])))
    checks = dict(checks_schema=2,internal_energy_Nmm=internal, external_work_Nmm=external,
                  free_DOF_force_relative_residual=float(free_residual),free_DOF_force_work_Nmm=residual_work,
                  relative_energy_error=energy_error, relative_force_error=float(force_error),
                  relative_moment_error=float(moment_error), maximum_BC_error_mm=bc_error,
                  minimum_element_volume_mm3=float(min(vol)))
    checks['accepted']=bool(energy_error < 5e-4 and free_residual < 1e-5 and force_error < 1e-4 and moment_error < 1e-4 and bc_error < 1e-6)
    return checks


def parse_and_check(dest):
    dest=Path(dest)
    meta=json.loads((dest/'input_metadata.json').read_text())
    mesh=np.load(PROJECT/meta['mesh_path'])
    fields=read_fields(dest)
    checks=check_fields(mesh,meta,fields)
    (dest/'checks.json').write_text(json.dumps(checks,indent=2))
    assert checks['accepted'],checks
    np.savez_compressed(dest/'fields.npz',**fields)
    return checks
