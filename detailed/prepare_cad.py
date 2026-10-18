from pathlib import Path
import gmsh,json,time,re
root=Path(__file__).parent;start=time.time()
gmsh.initialize();gmsh.option.setNumber('General.Terminal',1);gmsh.option.setNumber('General.NumThreads',4)
gmsh.model.occ.importShapes(str(root/'sources/biosensor_original.step'));gmsh.model.occ.synchronize()
original=gmsh.model.getEntities(3)
names=re.findall(r"MANIFOLD_SOLID_BREP\('([^']*)'",(root/'sources/biosensor_original.step').read_text())
print('Starting conformal fragmentation',len(original),flush=True)
out,mapping=gmsh.model.occ.fragment(original,[]);gmsh.model.occ.synchronize()
membership={}
for i,items in enumerate(mapping):
    for dim,tag in items:
        if dim==3:membership.setdefault(tag,[]).append(i+1)
report=[]
for tag,origins in membership.items():
    report.append(dict(tag=tag,original_bodies=origins,original_names=[names[i-1] for i in origins],volume_mm3=gmsh.model.occ.getMass(3,tag),bbox_mm=gmsh.model.getBoundingBox(3,tag)))
gmsh.write(str(root/'sources/conformal.brep'))
(root/'sources/fragment_inventory.json').write_text(json.dumps(report,indent=2))
print(json.dumps(dict(volumes=len(report),elapsed=time.time()-start,overlap=[a for a in report if len(a['original_bodies'])>1]),indent=2),flush=True)
gmsh.finalize()
