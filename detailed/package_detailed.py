from pathlib import Path
import zipfile,json,hashlib
from run_ccx import ROOT
def main():
    project=ROOT.parent;files=[]
    files.extend(ROOT.glob('*.py'));files.extend(ROOT.glob('*.md'));files.extend(ROOT.glob('*.ps1'));files.append(ROOT/'requirements_3d.txt')
    files.append(ROOT/'sources/biosensor_original.step');files.extend((ROOT/'sources').glob('*.json'))
    for mesh in (ROOT/'meshes').glob('h*'):
        files.extend([mesh/'mesh.npz',mesh/'mesh_audit.json'])
    for run in (ROOT/'runs').iterdir():
        if not (run/'metrics.json').exists():
            for name in ['input_metadata.json','execution.json','solver.log','job.cvg','job.sta']:
                if (run/name).exists():files.append(run/name)
            continue
        for name in ['input_metadata.json','execution.json','metrics.json','part_metrics.csv','solver.log','job.sta','job.cvg']:files.append(run/name)
        if run.name.startswith('h1.2_') and 'P10000_A0.1' in run.name:
            files.extend([run/'job.inp',run/'fields.npz'])
    files.extend(p for p in (ROOT/'verification').rglob('*') if p.is_file())
    files.extend(p for p in (ROOT/'output').rglob('*') if p.is_file() and p.suffix not in ['.zip'] and p.name!='Package_Manifest.json')
    files.extend([project/'README.md',project/'README_2D.md',project/'build_paper.py',project/'manuscript_content.py',project/'render_word.ps1',project/'sources/Avestia_Template.docx',project/'sources/artifact.md'])
    files=sorted(set(p for p in files if p.exists()))
    manifest={str(p.relative_to(project)).replace('\\','/'):{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files}
    mp=ROOT/'output/Package_Manifest.json';mp.write_text(json.dumps(manifest,indent=2));files.append(mp)
    target=ROOT/'output/Biosensor_3D_Research_Package.zip'
    with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=4) as z:
        for p in files:z.write(p,p.relative_to(project),compress_type=zipfile.ZIP_STORED if p.suffix=='.npz' else zipfile.ZIP_DEFLATED)
    with zipfile.ZipFile(target) as z:assert z.testzip() is None
    print(json.dumps(dict(path=str(target),size_MB=round(target.stat().st_size/1e6,1),files=len(files)),indent=2))
if __name__=='__main__':main()
