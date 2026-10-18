"""Geometric interface comparison from shared mesh facets; no simulated pressure implied."""
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from matplotlib.cm import ScalarMappable
from model import ROOT,PROJECT
from interface import interface_geometry


def main():
    output=ROOT/'output/figures';output.mkdir(parents=True,exist_ok=True)
    results=[]
    for scenario,path in [('Supplied',PROJECT/'detailed/meshes/h1.7/mesh.npz'),
                          ('Filled',ROOT/'meshes/filled/h1.7/mesh.npz')]:
        mesh=np.load(path)
        geo=interface_geometry(mesh['points'],mesh['cells'],mesh['region'])
        xy=mesh['points'][geo['face']].mean(axis=1)[:,:2]
        density,x,y=np.histogram2d(xy[:,0],xy[:,1],bins=np.arange(-20,21,1),weights=geo['area_mm2'])
        assert abs(density.sum()-geo['area_mm2'].sum())<1e-6
        results.append((scenario,density,float(geo['area_mm2'].sum())))
    vmax=np.ceil(max(r[1].max() for r in results)*10)/10
    cmap=plt.get_cmap('viridis').copy();cmap.set_bad('white')
    norm=Normalize(0,vmax)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':8})
    fig,axes=plt.subplots(1,2,figsize=(3.6,2.05),sharex=True,sharey=True)
    for ax,(scenario,density,area) in zip(axes,results):
        ax.imshow(np.ma.masked_equal(density.T,0),origin='lower',extent=(-20,20,-20,20),
                  cmap=cmap,norm=norm,interpolation='nearest')
        ax.set_title(('Supplied CAD' if scenario=='Supplied' else 'Gap-filled')+f'\nA = {area:.1f} mm²',fontsize=8)
        ax.set_xticks([-20,0,20]);ax.set_yticks([-20,0,20]);ax.tick_params(labelsize=7)
        ax.set_xlabel('x (mm)',fontsize=8)
    axes[0].set_ylabel('y (mm)',fontsize=8)
    fig.subplots_adjust(left=.15,right=.76,bottom=.18,top=.81,wspace=.18)
    colorbar=fig.colorbar(ScalarMappable(norm=norm,cmap=cmap),cax=fig.add_axes([.81,.23,.035,.46]))
    colorbar.set_label('Shared area / projected area',fontsize=7)
    colorbar.ax.tick_params(labelsize=7)
    fig.savefig(output/'Contact_Geometry.png',dpi=350,bbox_inches='tight')
    fig.savefig(output/'Contact_Geometry.pdf',bbox_inches='tight')
    plt.close(fig)
    (output/'Contact_Geometry_Provenance.json').write_text(json.dumps(dict(
        global_mesh_size_mm=1.7,bin_width_mm=1,
        shared_surface_areas_mm2={r[0]:r[2] for r in results},
        color='Actual shared triangle areas accumulated by projected face centroid, divided by 1 mm2 bin area',
        limitation='Geometric surface-area density, not pressure, adhesion strength, or a measured device contact map'),indent=2))


if __name__=='__main__':
    main()
