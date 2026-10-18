from pathlib import Path
import gmsh,json
root=Path(__file__).parent
gmsh.initialize();gmsh.option.setNumber('General.Terminal',0)
gmsh.model.occ.importShapes(str(root/'sources/biosensor_original.step'))
gmsh.model.occ.synchronize();out=[]
for dim,tag in gmsh.model.getEntities(3):
    out.append(dict(tag=tag,label=gmsh.model.getEntityName(dim,tag),volume_mm3=gmsh.model.occ.getMass(dim,tag),center_mm=gmsh.model.occ.getCenterOfMass(dim,tag),bbox_mm=gmsh.model.getBoundingBox(dim,tag),surfaces=len(gmsh.model.getBoundary([(dim,tag)]))))
(root/'sources/cad_inventory.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2));gmsh.finalize()
