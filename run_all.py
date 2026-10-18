"""Rebuild computations, validation, figures and manuscript. PDF export uses Word separately."""
import subprocess,sys
from pathlib import Path
root=Path(__file__).parent
for script in ['simulation.py','refine.py','controls.py','verify_solver.py','audit_results.py','build_paper.py']:
    print('Running',script,flush=True)
    subprocess.run([sys.executable,str(root/script)],cwd=root,check=True)
