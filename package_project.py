from pathlib import Path
import hashlib,json,zipfile
ROOT=Path(__file__).parent
files=[]
for pattern in ['*.py','*.ps1','requirements.txt','README.md','*_run.log']:
    files.extend(ROOT.glob(pattern))
for folder in ['sources','results','output/figures']:
    files.extend(p for p in (ROOT/folder).rglob('*') if p.is_file())
for name in ['Biosensor_Proceeding.docx','Biosensor_Proceeding.pdf','Manuscript_Text.txt','paper_statistics.json']:
    files.append(ROOT/'output'/name)
files=sorted(set(files))
manifest={str(p.relative_to(ROOT)).replace('\\','/'):{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files}
(ROOT/'output/Package_Manifest.json').write_text(json.dumps(manifest,indent=2))
files.append(ROOT/'output/Package_Manifest.json')
target=ROOT/'output/Biosensor_Reproducibility_Package.zip'
with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in files:z.write(p,p.relative_to(ROOT))
with zipfile.ZipFile(target) as z:
    assert z.testzip() is None
    assert 'output/Biosensor_Proceeding.docx' in z.namelist()
    assert 'results/metrics.csv' in z.namelist()
print(json.dumps({'package':str(target),'files':len(files),'size_MB':round(target.stat().st_size/1e6,2),'sha256':hashlib.sha256(target.read_bytes()).hexdigest()},indent=2))
