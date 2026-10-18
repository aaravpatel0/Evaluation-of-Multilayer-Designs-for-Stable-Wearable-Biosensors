"""Resume the verified study sequentially; stop on any failed numerical gate.

Run only when no other study driver is active. The manuscript is deliberately
separate so its final tables, figures, and page layout receive human-readable QA.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def run(label, *arguments):
    print('START', label, flush=True)
    subprocess.run([sys.executable, *arguments], cwd=ROOT.parent, check=True)
    print('COMPLETE', label, flush=True)


def main():
    # Reference controls are prerequisites for the revised skin metric.
    for geometry in ['Supplied', 'Filled']:
        for h in [1.7, 1.2]:
            for mode in ['XX', 'YY', 'XY']:
                directory = ROOT/'references'/f'{geometry}_h{h:g}_{mode}'
                record = json.loads((directory/'checks.json').read_text())
                assert record['checks_schema'] == 2 and record['accepted']
                assert (directory/'fields.npz').is_file()
    run('early fine-mesh control', '-c',
        "import sys; sys.path.insert(0,'advanced'); "
        "from run_study import direct_gate; from postprocess import analyze; "
        "direct_gate(1.2,geometry='Filled'); "
        "analyze(1.2,'Uniform',.2,.1,'Filled')")
    for script in ['run_expanded.py', 'reanalyze.py', 'summarize.py',
                   'run_refinement.py', 'finalize_analysis.py',
                   'plot_geometry.py', 'plot_results.py']:
        run(script, str(ROOT/script))
    print('VERIFIED ANALYSIS AND FIGURES COMPLETE; manuscript QA remains.', flush=True)


if __name__ == '__main__':
    main()
