from pathlib import Path
import numpy as np,json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from matplotlib.collections import PolyCollection
from run_ccx import ROOT,NAMES
import plotly.graph_objects as go
OUT=ROOT/'output';OUT.mkdir(exist_ok=True);FIG=OUT/'figures';FIG.mkdir(exist_ok=True)
COLORS={1:'#d6b49a',2:'#c9be94',31:'#94cec4',32:'#b0c5df',33:'#9cb5d5',4:'#485567',5:'#2c9890',6:'#2c9890',7:'#2c9890',8:'#2c9890',9:'#d7a521',10:'#76678f',11:'#d7a521',12:'#697282',13:'#e3b52e',14:'#f0c33e',15:'#237e82',16:'#b9c1cc'}
def exterior(c):
    faces=np.vstack([c[:,[0,1,2]],c[:,[0,1,3]],c[:,[0,2,3]],c[:,[1,2,3]]]);faces=np.sort(faces,axis=1);unique,counts=np.unique(faces,axis=0,return_counts=True);return unique[counts==1]
def main():
    dat=np.load(ROOT/'meshes/h2.5/mesh.npz');p,c,r=dat['points'],dat['cells'],dat['region'];surfaces={int(region):exterior(c[r==region,:4]) for region in sorted(set(r))}
    fig,ax=plt.subplots(figsize=(3.65,3.5));triangles=[];owners=[]
    for region,faces in surfaces.items():
        if region in range(4,16):triangles.append(p[faces]);owners.extend([region]*len(faces))
    tris=np.vstack(triangles);owners=np.array(owners);order=np.lexsort((owners,np.round(tris[:,:,2].mean(axis=1),6)))
    ax.add_collection(PolyCollection(tris[order,:,:2],facecolors=[COLORS[int(a)] for a in owners[order]],edgecolors='none'))
    positions={9:(4,14),11:(-12,12),10:(15,5),12:(-5,-14),13:(9.5,-5.5),14:(9.5,-1.5),15:(0,0),5:(5,-5),6:(-5,5),7:(-5,-5),8:(5,5)}
    for region,xy in positions.items():ax.text(*xy,str(region),fontsize=7,ha='center',va='center',color='black',bbox=dict(facecolor='white',alpha=.75,edgecolor='none',pad=.4))
    ax.annotate('4: ABS housing',xy=(-6,0),xytext=(-19,-8),fontsize=7,arrowprops=dict(arrowstyle='-',lw=.6))
    ax.set_xlim(-20,20);ax.set_ylim(-18,20);ax.set_aspect('equal');ax.set_xlabel('x (mm)',fontsize=8);ax.set_ylabel('y (mm)',fontsize=8);ax.tick_params(labelsize=7);ax.spines[['top','right']].set_visible(False);fig.tight_layout(pad=.4)
    fig.savefig(FIG/'CAD_Assembly.png',dpi=350,bbox_inches='tight');plt.close(fig)
    viewer=go.Figure()
    for region,faces in surfaces.items():
        used=np.unique(faces);verts=p[used];ff=np.searchsorted(used,faces)
        visible=True if region in range(4,16) or region==33 else 'legendonly'
        viewer.add_trace(go.Mesh3d(x=verts[:,0],y=verts[:,1],z=verts[:,2],i=ff[:,0],j=ff[:,1],k=ff[:,2],name=f'{region}: {NAMES[region]}',color=COLORS[region],opacity=1 if region in range(4,16) else .22,visible=visible,flatshading=False,showlegend=True,hovertemplate=f'{NAMES[region]}<br>x=%{{x:.2f}} mm<br>y=%{{y:.2f}} mm<br>z=%{{z:.2f}} mm<extra></extra>'))
    viewer.update_layout(title='Original STEP biosensor assembly — toggle layers in the legend',scene=dict(xaxis_title='x (mm)',yaxis_title='y (mm)',zaxis_title='z (mm)',aspectmode='data'),margin=dict(l=0,r=0,t=60,b=0),height=800,legend=dict(font=dict(size=12)))
    viewer.write_html(OUT/'Biosensor_3D_Viewer.html',include_plotlyjs=True,full_html=True)
    (OUT/'Component_Index.json').write_text(json.dumps({str(k):v for k,v in NAMES.items()},indent=2));print('Viewer and cutaway figure created',flush=True)
if __name__=='__main__':main()
