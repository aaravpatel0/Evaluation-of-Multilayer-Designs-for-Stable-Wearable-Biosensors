"""Unsmeared skin/adhesive interface traction estimates from displacement gradients."""
import numpy as np

EDGE_PAIRS = [(0,1),(1,2),(2,0),(0,3),(1,3),(2,3)]


def interface_geometry(points, cells, regions):
    corners = cells[:, :4]
    faces = np.vstack([corners[:,f] for f in ([0,1,2],[0,1,3],[0,2,3],[1,2,3])])
    owners = np.tile(np.arange(len(cells)),4)
    unique, first, inverse, count = np.unique(np.sort(faces,axis=1), axis=0,
                                            return_index=True, return_inverse=True, return_counts=True)
    sums = np.bincount(inverse,weights=owners,minlength=len(unique)).astype(np.int64)
    a = owners[first]; b = sums-a
    paired = count == 2
    group = np.where(paired & (((regions[a] == 1) & (regions[np.minimum(b,len(cells)-1)] == 2)) |
                               ((regions[a] == 2) & (regions[np.minimum(b,len(cells)-1)] == 1))))[0]
    assert len(group) > 0
    a, b = a[group], b[group]
    skin = np.where(regions[a] == 1,a,b)
    adhesive = np.where(regions[a] == 2,a,b)
    face = unique[group]; xyz = points[face]
    normal = np.cross(xyz[:,1]-xyz[:,0],xyz[:,2]-xyz[:,0])
    area = .5*np.linalg.norm(normal,axis=1)
    normal /= (2*area[:,None])
    centers = points[corners].mean(axis=1)
    normal *= np.where(np.sum(normal*(centers[adhesive]-centers[skin]),axis=1)<0,-1,1)[:,None]
    assert np.all(area > 0)
    return dict(face=face,skin_element=skin,adhesive_element=adhesive,normal=normal,area_mm2=area)


def strain_at(points, cells, displacement, elements, barycentric):
    """Small-strain tensor at arbitrary barycentric points of straight-sided C3D10s."""
    vertices = points[cells[elements,:4]]
    A = np.concatenate((np.ones((*vertices.shape[:2],1)),vertices),axis=2)
    gradL = np.linalg.inv(A)[:,1:,:].transpose(0,2,1)
    gradN = [(4*barycentric[:,i,None]-1)*gradL[:,i] for i in range(4)]
    gradN.extend(4*(barycentric[:,i,None]*gradL[:,j]+barycentric[:,j,None]*gradL[:,i])
                 for i,j in EDGE_PAIRS)
    gradN = np.stack(gradN,axis=1)
    gradient = np.einsum('nki,nkj->nij',displacement[cells[elements]],gradN)
    return np.column_stack((gradient[:,0,0],gradient[:,1,1],gradient[:,2,2],
                            .5*(gradient[:,0,1]+gradient[:,1,0]),
                            .5*(gradient[:,0,2]+gradient[:,2,0]),
                            .5*(gradient[:,1,2]+gradient[:,2,1])))


def stress_from_strain(strain, E, nu=.49):
    stress = E/(1+nu)*strain
    stress[:,:3] += (E*nu/((1+nu)*(1-2*nu))*strain[:,:3].sum(axis=1))[:,None]
    return stress


def traction(stress, normal):
    x,y,z = normal.T
    a,b,c,d,e,f = stress.T
    return np.column_stack((a*x+d*y+e*z,d*x+b*y+f*z,e*x+f*y+c*z))


def surface_stress(points,cells,displacement,geometry,side,E):
    elements = geometry[f'{side}_element']
    # A face centroid has barycentric coordinate 1/3 at its three vertices and zero opposite.
    bary = np.zeros((len(elements),4))
    for i in range(4):
        bary[:,i] = np.any(cells[elements,i,None] == geometry['face'],axis=1)/3
    assert np.max(abs(bary.sum(axis=1)-1)) < 1e-12
    return stress_from_strain(strain_at(points,cells,displacement,elements,bary),E)


def verify(points,cells,regions):
    geometry = interface_geometry(points,cells,regions)
    tensor = np.array([[.01,.003,-.002],[.003,-.004,.001],[-.002,.001,-.003]])
    displacement = points @ tensor.T
    expected = np.array([.01,-.004,-.003,.003,-.002,.001])
    strain = strain_at(points,cells,displacement,geometry['adhesive_element'],
                       np.full((len(geometry['face']),4),.25))
    err = float(np.max(abs(strain-expected)))
    assert err < 1e-8,err
    exact = stress_from_strain(expected[None,:].copy(),.1)[0]
    actual = surface_stress(points,cells,displacement,geometry,'adhesive',.1)
    terr = float(np.max(abs(actual-exact)))
    assert terr < 1e-8,terr
    assert np.max(abs(np.linalg.norm(geometry['normal'],axis=1)-1)) < 1e-12
    return dict(interface_faces=len(geometry['face']),area_mm2=float(geometry['area_mm2'].sum()),
                affine_strain_max_error=err,interface_stress_max_error_MPa=terr),geometry
