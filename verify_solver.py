"""Assembled homogeneous patch and plane-strain tension benchmark."""
import numpy as np, json
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import spsolve
from simulation import Bmat,constit,OUT,verify

def benchmark():
    nx,ny=8,4; p=np.array([(x,y) for y in np.linspace(0,1,ny+1) for x in np.linspace(0,2,nx+1)])
    c=[]
    for j in range(ny):
        for i in range(nx):
            k=j*(nx+1)+i;c.append([k,k+1,k+nx+2,k+nx+1])
    c=np.array(c); ed=(2*c[:,:,None]+np.arange(2)).reshape(-1,8); E,nu=1.,.49; dd,dv,_,_=constit(E,nu);kes=[]
    for ids in c:
        xy=p[ids]; ke=np.zeros((8,8))
        for xi in [-1/np.sqrt(3),1/np.sqrt(3)]:
            for eta in [-1/np.sqrt(3),1/np.sqrt(3)]:
                b,j=Bmat(xy,xi,eta);ke+=b.T@dd@b*j
        b,j=Bmat(xy,0,0);ke+=b.T@dv@b*j*4;kes.append(ke)
    K=coo_matrix((np.array(kes).ravel(),(np.repeat(ed,8,axis=1).ravel(),np.tile(ed,(1,8)).ravel())),shape=(2*len(p),)*2).tocsr()
    def run(fixed,values):
        u=np.zeros(2*len(p));u[fixed]=values;free=np.setdiff1d(np.arange(len(u)),fixed);u[free]=spsolve(K[free][:,free],-K[free][:,fixed]@u[fixed]);return u
    boundary=np.where((p[:,0]==0)|(p[:,0]==2)|(p[:,1]==0)|(p[:,1]==1))[0]; fixed=(2*boundary[:,None]+np.arange(2)).ravel()
    exact=np.column_stack((.01*p[:,0]+.003*p[:,1],-.002*p[:,1]+.004*p[:,0])).ravel();u=run(fixed,exact[fixed]);patch=np.max(abs(u-exact))
    left=np.where(p[:,0]==0)[0];right=np.where(p[:,0]==2)[0];fixed=np.r_[2*left,2*right,1];values=np.r_[np.zeros(len(left)),np.full(len(right),.02),0.];u=run(fixed,values)
    analytical=np.column_stack((.01*p[:,0],-nu/(1-nu)*.01*p[:,1])).ravel(); reaction=(K@u)[2*right].sum(); expected=E/(1-nu**2)*.01
    result={**verify(), 'assembled_affine_displacement_error_mm':float(patch),'uniaxial_displacement_error_mm':float(np.max(abs(u-analytical))),'uniaxial_reaction_N':float(reaction),'analytical_reaction_N':expected,'reaction_relative_error':float(abs(reaction-expected)/expected)}
    assert patch<1e-10 and result['reaction_relative_error']<1e-9
    (OUT/'verification.json').write_text(json.dumps(result,indent=2));print(result)
if __name__=='__main__':benchmark()
