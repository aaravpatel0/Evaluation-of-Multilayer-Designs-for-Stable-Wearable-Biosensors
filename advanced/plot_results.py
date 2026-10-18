"""Final quantitative figures from complete accepted data only."""
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.colors import Normalize,to_rgba
from matplotlib.cm import ScalarMappable
from model import ROOT,PROJECT,BASIS
from postprocess import coefficients,von_mises
from interface import interface_geometry

COLORS={'Uniform':'#374b67','Single':'#157b8c','Graded':'#b55f30'}
MATERIAL={1:'#d6b49a',2:'#c9be94',31:'#94cec4',32:'#b0c5df',33:'#9cb5d5',4:'#485567',5:'#2c9890',6:'#2c9890',7:'#2c9890',8:'#2c9890',9:'#d7a521',10:'#76678f',11:'#d7a521',12:'#697282',13:'#e3b52e',14:'#f0c33e',15:'#237e82'}
OUT=ROOT/'output/figures'


def save(fig,name):
    fig.savefig(OUT/(name+'.png'),dpi=350,bbox_inches='tight')
    fig.savefig(OUT/(name+'.pdf'),dpi=350,bbox_inches='tight')
    plt.close(fig)


def directional():
    fig,ax=plt.subplots(figsize=(3.6,2.65))
    for design,color in COLORS.items():
        profiles=[]
        for skin in [.1,.2,.5]:
            p=ROOT/'output'/f'WSL_h1.7_Filled_{design}_S{skin:g}_A0.1_responses.json'
            rows=[r for r in json.loads(p.read_text()) if r['angle_deg'] is not None]
            profiles.append([100*r['wire_p95_absolute_principal_strain'] for r in rows])
        angles=np.arange(0,181,5)
        a=np.array(profiles);a=np.column_stack((a,a[:,0]))
        ax.fill_between(angles,a.min(axis=0),a.max(axis=0),color=color,alpha=.15,linewidth=0)
        ax.plot(angles,a[1],color=color,label=design,lw=1.4)
    ax.set(xlabel='Extension direction θ (degrees)',ylabel='Wire strain, 95th percentile (%)',xticks=[0,45,90,135,180])
    ax.legend(frameon=False,ncol=3,loc='upper center',fontsize=7)
    fig.tight_layout(pad=.7);save(fig,'Directional_Wire_Strain')


def tradeoffs(summary):
    marker={.05:'o',.1:'s',.5:'^'}
    fig,axes=plt.subplots(2,1,figsize=(3.6,3.6),sharex=True)
    for option in summary['options']:
        kwargs=dict(marker=marker[option['adhesive_E_MPa']],s=42,
                    facecolors=COLORS[option['design']],edgecolors='black' if option['sampled_Pareto_nondominated'] else '#bbbbbb',
                    linewidths=1.1 if option['sampled_Pareto_nondominated'] else .5)
        axes[0].scatter(100*option['worst_wire'],option['worst_skin'],**kwargs)
        axes[1].scatter(100*option['worst_wire'],100*option['worst_adhesive'],**kwargs)
    axes[0].set_ylabel('Worst skin disturbance / 1%')
    axes[1].set_ylabel('Worst adhesive distortion (%)')
    axes[1].set_xlabel('Worst wire strain, 95th percentile (%)')
    for design,color in COLORS.items():
        axes[0].plot([],[],marker='o',linestyle='none',color=color,label=design)
    axes[0].legend(frameon=False,ncol=3,fontsize=7)
    for E,m in marker.items():
        axes[1].plot([],[],marker=m,linestyle='none',color='#777777',label=f'{E:g} MPa')
    axes[1].legend(frameon=False,ncol=3,fontsize=7)
    fig.tight_layout(pad=.6);save(fig,'Mechanical_Tradeoffs')


def assembly():
    mesh=np.load(ROOT/'meshes/filled/h1.2/mesh.npz');p,c,r=mesh['points'],mesh['cells'],mesh['region']
    rows=json.loads((ROOT/'output/WSL_h1.2_Filled_Uniform_S0.2_A0.1_responses.json').read_text())
    worst=max((a for a in rows if a['angle_deg'] is not None),key=lambda a:a['wire_p95_absolute_principal_strain'])
    coef=coefficients(worst['angle_deg'])
    paths=[ROOT/'runs'/f'WSL_h1.2_Filled_Uniform_S0.2_A0.1_{mode}/fields.npz' for mode in BASIS]
    fields=[np.load(path) for path in paths]
    u=sum(a*f['displacement'] for a,f in zip(coef,fields))
    stress=sum(a*f['stress'] for a,f in zip(coef,fields))
    vm=von_mises(stress).mean(axis=1)
    # Exterior of the displayed union; shared material interfaces are not duplicated.
    ids=np.where(r!=16)[0];corners=c[ids,:4]
    faces=np.vstack([corners[:,f] for f in ([0,1,2],[0,1,3],[0,2,3],[1,2,3])])
    unique,first,count=np.unique(np.sort(faces,axis=1),axis=0,return_index=True,return_counts=True)
    faces=unique[count==1];owners=np.tile(ids,4)[first[count==1]]
    az,el=np.deg2rad([-62,37])
    camera=np.array([[-np.sin(az),np.cos(az),0],[-np.sin(el)*np.cos(az),-np.sin(el)*np.sin(az),np.cos(el)],
                     [np.cos(el)*np.cos(az),np.cos(el)*np.sin(az),np.sin(el)]])
    fig=plt.figure(figsize=(3.6,3.6));norm=Normalize(0,5);cmap=plt.get_cmap('inferno')
    for panel,scale in enumerate([0,10]):
        ax=fig.add_axes([.015,.54 if not panel else .075,.81,.38])
        tri=(p+scale*u)[faces]@camera.T;order=np.argsort(tri[:,:,2].mean(axis=1))
        colors=np.array([to_rgba(MATERIAL[int(region)]) for region in r[owners]])
        electronic=(r[owners]>=4)&(r[owners]<=15)
        if panel: colors[electronic]=cmap(norm(vm[owners[electronic]]))
        ax.add_collection(PolyCollection(tri[order,:,:2],facecolors=colors[order],edgecolors='none',antialiased=False,rasterized=True))
        xy=tri[:,:,:2].reshape(-1,2)
        ax.set(xlim=(xy[:,0].min()-1,xy[:,0].max()+1),ylim=(xy[:,1].min()-1,xy[:,1].max()+1),aspect='equal')
        ax.set_axis_off()
    fig.text(.02,.965,'(a) Sensor on the modeled skin; cover hidden',fontsize=8)
    fig.text(.02,.50,f'(b) 1% directional extension, θ = {worst["angle_deg"]:g}°',fontsize=8)
    fig.text(.02,.015,'Displacement enlarged ×10; skin/supports retain material colors',fontsize=6.6)
    cb=fig.colorbar(ScalarMappable(norm=norm,cmap=cmap),cax=fig.add_axes([.86,.15,.025,.22]),extend='max')
    cb.set_label('von Mises stress (MPa)',fontsize=7);cb.ax.tick_params(labelsize=7)
    save(fig,'Assembly_On_Skin')
    (OUT/'Assembly_On_Skin_Provenance.json').write_text(json.dumps(dict(
        scenario='Filled',mesh_h_mm=1.2,design='Uniform',skin_E_MPa=.2,adhesive_E_MPa=.1,
        angle_deg=worst['angle_deg'],displacement_scale=10,stress_range_MPa=[0,5],
        stress_measure='Element mean integration-point von Mises stress after tensor superposition',
        hidden_regions=[16],source_cases=[str(path.relative_to(PROJECT)) for path in paths]),indent=2))


def main():
    summary=json.loads((ROOT/'output/Final_Study_Summary.json').read_text())
    OUT.mkdir(exist_ok=True)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':8,'axes.spines.top':False,'axes.spines.right':False})
    directional();tradeoffs(summary);assembly()


if __name__=='__main__':
    main()
