"""Device-free reference on exactly the same skin elements and quadrature ordering."""
import json,argparse,hashlib
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from model import ROOT,PROJECT,BASIS,write_deck,execute,parse_and_check


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--prepare-only',action='store_true');args=parser.parse_args()
    reports=[]
    for scenario,base in [('Supplied',PROJECT/'detailed/meshes'),('Filled',ROOT/'meshes/filled')]:
        for h in [1.7,1.2]:
            mesh=np.load(base/f'h{h:g}/mesh.npz')
            skin_elements=np.where(mesh['region']==1)[0]
            cells=mesh['cells'][skin_elements]
            used=np.unique(cells)
            path=ROOT/'meshes'/f'bare_{scenario}_h{h:g}.npz'
            np.savez_compressed(path,points=mesh['points'][used],cells=np.searchsorted(used,cells),
                                region=np.ones(len(cells),dtype=int),original_node_ids=used,
                                original_element_ids=skin_elements)
            remapped=np.searchsorted(used,cells)
            graph=coo_matrix((np.ones(9*len(cells),dtype=np.int8),(np.repeat(remapped[:,0],9),remapped[:,1:].ravel())),shape=(len(used),len(used))).tocsr()
            count,_=connected_components(graph,directed=False)
            assert count==1
            assert np.array_equal(used[remapped],cells)
            reports.append(dict(scenario=scenario,h_mm=h,nodes=len(used),elements=len(cells),
                                connected_components=count,source_mesh_sha256=hashlib.sha256((base/f'h{h:g}/mesh.npz').read_bytes()).hexdigest()))
            (ROOT/'verification/bare_mesh_mapping.json').write_text(json.dumps(reports,indent=2))
            if args.prepare_only:
                print('PREPARED',scenario,h,len(used),len(cells),flush=True)
                continue
            for mode,loading in BASIS.items():
                dest=ROOT/'references'/f'{scenario}_h{h:g}_{mode}'
                write_deck(dest,path,loading,homogeneous=True,skin_E=.2,nu=.49,geometry_scenario='Bare_'+scenario)
                fresh=execute(dest)
                if fresh or not (dest/'fields.npz').exists():
                    parse_and_check(dest)
                check=json.loads((dest/'checks.json').read_text())
                assert check['accepted']
                print('BARE SKIN REFERENCE',scenario,h,mode,json.dumps(check),flush=True)


if __name__=='__main__':
    main()
