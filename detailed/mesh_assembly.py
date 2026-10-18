"""Conforming quadratic mesh of all sixteen supplied STEP bodies.
Interpenetrating ABS stem takes precedence over skin adhesive and PDMS.
Internal cuts partition the original 1 mm PDMS for equal-thickness controls.
"""
from pathlib import Path
import gmsh,numpy as np,json,re,time,argparse
root=Path(__file__).parent
def build(h=2.5,wire=.20):
    start=time.time();dest=root/'meshes'/f'h{h:g}';dest.mkdir(parents=True,exist_ok=True)
    gmsh.initialize();gmsh.option.setNumber('General.NumThreads',1);gmsh.option.setNumber('General.Terminal',1)
    gmsh.model.occ.importShapes(str(root/'sources/biosensor_original.step'));gmsh.model.occ.synchronize();original=gmsh.model.getEntities(3)
    names=re.findall(r"MANIFOLD_SOLID_BREP\('([^']*)'",(root/'sources/biosensor_original.step').read_text())
    planes=[(2,gmsh.model.occ.addRectangle(-40,-40,z,80,80)) for z in [2.56,2.81]]
    out,mapping=gmsh.model.occ.fragment(original,planes);gmsh.model.occ.synchronize();membership={}
    for i,items in enumerate(mapping[:16]):
        for dim,tag in items:
            if dim==3:membership.setdefault(tag,[]).append(i+1)
    # A volume with two origins is physical overlap, not a second stacked element.
    groups={};audit=[]
    for tag,origins in membership.items():
        owner=4 if 4 in origins else origins[0];z=gmsh.model.occ.getCenterOfMass(3,tag)[2]
        region=owner if owner!=3 else (31 if z<2.56 else 32 if z<2.81 else 33)
        groups.setdefault(region,[]).append(tag)
        audit.append(dict(volume=tag,owner=owner,origins=origins,region=region,volume_mm3=gmsh.model.occ.getMass(3,tag)))
    boundary={abs(t) for d,t in gmsh.model.getBoundary(gmsh.model.getEntities(3),combined=False) if d==2}
    unused=[(d,t) for d,t in gmsh.model.getEntities(2) if t not in boundary]
    gmsh.model.occ.remove(unused);gmsh.model.occ.synchronize()
    for region,tags in groups.items():
        gmsh.model.addPhysicalGroup(3,tags,region);gmsh.model.setPhysicalName(3,region,names[region-1] if region<30 else f'PDMS_partition_{region}')
    gmsh.option.setNumber('Mesh.MeshSizeMin',.035);gmsh.option.setNumber('Mesh.MeshSizeMax',h)
    gmsh.option.setNumber('Mesh.MeshSizeFromCurvature',8);gmsh.option.setNumber('Mesh.MeshSizeFromPoints',0);gmsh.option.setNumber('Mesh.MeshSizeExtendFromBoundary',0)
    wire_surfaces=[abs(t) for region in [13,14] for v in groups.get(region,[]) for d,t in gmsh.model.getBoundary([(3,v)])]
    gmsh.model.mesh.field.add('Distance',1);gmsh.model.mesh.field.setNumbers(1,'FacesList',wire_surfaces);gmsh.model.mesh.field.setNumber(1,'Sampling',30)
    gmsh.model.mesh.field.add('Threshold',2);gmsh.model.mesh.field.setNumber(2,'InField',1);gmsh.model.mesh.field.setNumber(2,'SizeMin',wire);gmsh.model.mesh.field.setNumber(2,'SizeMax',h);gmsh.model.mesh.field.setNumber(2,'DistMin',.2);gmsh.model.mesh.field.setNumber(2,'DistMax',2.0);gmsh.model.mesh.field.setAsBackgroundMesh(2)
    gmsh.option.setNumber('Mesh.Algorithm3D',1);gmsh.option.setNumber('Mesh.Optimize',1)
    gmsh.model.mesh.generate(3);gmsh.model.mesh.optimize('Netgen');gmsh.option.setNumber('Mesh.SecondOrderLinear',1);gmsh.model.mesh.setOrder(2)
    node_tags,xyz,_=gmsh.model.mesh.getNodes();p=np.array(xyz).reshape(-1,3);all_cells=[];regions=[];element_tags=[]
    for region,vols in sorted(groups.items()):
        for v in vols:
            types,tags,nodes=gmsh.model.mesh.getElements(3,v)
            for et,ts,ns in zip(types,tags,nodes):
                assert et==11,et
                conn=np.array(ns,dtype=np.int64).reshape(-1,10)[:,[0,1,2,3,4,5,6,7,9,8]]
                all_cells.append(conn);regions.extend([region]*len(conn));element_tags.extend(ts)
    c=np.vstack(all_cells);used=np.unique(c);order=np.argsort(node_tags);idx=order[np.searchsorted(node_tags[order],used)];p=p[idx];c=np.searchsorted(used,c)
    for k,(a,b) in enumerate([(0,1),(1,2),(2,0),(0,3),(1,3),(2,3)]):assert np.max(np.linalg.norm(p[c[:,4+k]]-(p[c[:,a]]+p[c[:,b]])/2,axis=1))<1e-6
    qual=gmsh.model.mesh.getElementQualities(element_tags,'minSICN');det=gmsh.model.mesh.getElementQualities(element_tags,'minDetJac')
    bad=np.where(np.array(det)<=0)[0];print('Jacobian audit',float(min(det)),len(bad), 'regions',np.array(regions)[bad][:30],flush=True)
    gmsh.write(str(dest/'candidate.msh'))
    np.savez_compressed(dest/'candidate.npz',points=p,cells=c,region=np.array(regions),jacobian=np.array(det),quality=np.array(qual))
    assert min(det)>0
    np.savez_compressed(dest/'mesh.npz',points=p,cells=c,region=np.array(regions))
    gmsh.option.setNumber('Mesh.MshFileVersion',4.1);gmsh.write(str(dest/'assembly.msh'))
    report=dict(h_mm=h,wire_size_mm=wire,nodes=len(p),elements=len(c),dofs=3*len(p),minimum_quality=float(min(qual)),minimum_jacobian=float(min(det)),elapsed_seconds=time.time()-start,fragments=audit,part_names=names)
    (dest/'mesh_audit.json').write_text(json.dumps(report,indent=2));gmsh.finalize();print(json.dumps({k:v for k,v in report.items() if k not in ['fragments','part_names']},indent=2));return dest
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--h',type=float,default=2.5);a.add_argument('--wire',type=float,default=.2);args=a.parse_args();build(args.h,args.wire)
