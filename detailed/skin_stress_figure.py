"""Render the accepted 3D mesh and solved displacement/stress, without invented fields."""
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize, to_rgba
from matplotlib.cm import ScalarMappable
from matplotlib.collections import PolyCollection
from run_ccx import ROOT
from visualize_assembly import COLORS


def surface_with_owners(cells, indices):
    corners = cells[indices, :4]
    faces = np.vstack([corners[:, f] for f in ([0,1,2], [0,1,3], [0,2,3], [1,2,3])])
    faces = np.sort(faces, axis=1)
    unique, first, count = np.unique(faces, axis=0, return_index=True, return_counts=True)
    return unique[count == 1], np.tile(indices, 4)[first[count == 1]]


def main():
    out = ROOT/'output/figures'
    mesh = np.load(ROOT/'meshes/h1.2/mesh.npz')
    p, cells, region = mesh['points'], mesh['cells'], mesh['region']
    run = ROOT/'runs/h1.2_Uniform_Tension_LE_P10000_A0.1'
    fields = np.load(run/'fields.npz')
    u = np.zeros_like(p)
    u[fields['node_id']-1] = fields['displacement']
    eid = fields['element_id']-1
    count = np.bincount(eid, minlength=len(cells))
    stress = np.bincount(eid, weights=fields['vm'], minlength=len(cells))/np.maximum(count, 1)
    # Render only the exterior of the displayed union, avoiding duplicate interface faces.
    exterior, owners = surface_with_owners(cells, np.where(region != 16)[0])
    surfaces = {int(r): (exterior[region[owners] == r], owners[region[owners] == r])
                for r in sorted(set(region)) if r != 16}
    norm = Normalize(0, 5)
    cmap = plt.get_cmap('inferno')
    fig = plt.figure(figsize=(5.6, 6.2))
    az, el = np.deg2rad([-62, 37])
    camera = np.array([[-np.sin(az), np.cos(az), 0],
                       [-np.sin(el)*np.cos(az), -np.sin(el)*np.sin(az), np.cos(el)],
                       [np.cos(el)*np.cos(az), np.cos(el)*np.sin(az), np.sin(el)]])
    for panel, scale in enumerate([0, 10]):
        ax = fig.add_axes([.03, .55 if panel == 0 else .095, .80, .38])
        xyz = p + scale*u
        triangles, colors = [], []
        for r, (faces, owners) in surfaces.items():
            triangles.append(xyz[faces])
            if panel and 4 <= r <= 15:
                assert np.all(count[owners] > 0)
                colors.extend(cmap(norm(stress[owners])))
            else:
                colors.extend([to_rgba(COLORS[r])]*len(faces))
        projected = np.vstack(triangles) @ camera.T
        order = np.argsort(projected[:, :, 2].mean(axis=1))
        ax.add_collection(PolyCollection(projected[order, :, :2], facecolors=np.array(colors)[order],
                                        edgecolors='none', antialiased=False, rasterized=True))
        # Equal millimetre scales in the orthographic image; no artificial thickness scaling.
        xy = projected[:, :, :2].reshape(-1, 2)
        ax.set_xlim(xy[:,0].min()-2, xy[:,0].max()+2)
        ax.set_ylim(xy[:,1].min()-2, xy[:,1].max()+2)
        ax.set_aspect('equal')
        ax.set_axis_off()
        if not panel:
            fig.text(.03, .965, '(a) Sensor assembly on the skin slab', fontsize=13)
            fig.text(.03, .52, 'Skin: tan   Supports: blue   Wires / traces: gold\n'
                     'Top cover hidden to reveal the components', fontsize=12)
        else:
            a = np.array([36,-26,2]) @ camera.T
            b = np.array([43,-26,2]) @ camera.T
            ax.annotate('', xy=b[:2], xytext=a[:2], annotation_clip=False,
                        arrowprops=dict(arrowstyle='->', color='#bc252a', lw=1.6, clip_on=False))
            fig.text(.03, .47, '(b) Loaded assembly: electronic-body stress', fontsize=13)
            fig.text(.03, .025, 'Left skin edge fixed; right skin edge: +0.60 mm in x\n'
                     '1% extension over 60 mm; displacement enlarged ×10', fontsize=12)
    cb = fig.colorbar(ScalarMappable(norm=norm, cmap=cmap),
                      cax=fig.add_axes([.87, .16, .025, .24]), extend='max')
    cb.set_label('von Mises stress (MPa)', fontsize=11)
    cb.ax.tick_params(labelsize=11)
    fig.savefig(out/'Sensor_On_Skin_3D.png', dpi=350, facecolor='white')
    fig.savefig(out/'Sensor_On_Skin_3D.pdf', dpi=350, facecolor='white')
    plt.close(fig)
    (out/'Sensor_On_Skin_3D_Provenance.json').write_text(json.dumps(dict(
        case=str(run.relative_to(ROOT)), mesh='h1.2', displacement_display_scale=10,
        stress_measure='Adjacent element mean of four integration-point von Mises values',
        stress_color_range_MPa=[0,5], stress_saturated_above_MPa=5,
        hidden_regions=[16], skin_and_supports='Nominal material colors; stress not shown',
        rendering='Orthographic projection of corner-node surface triangles; no cross-material stress smoothing'), indent=2))


if __name__ == '__main__':
    main()
