"""Device-free reference on exactly the same skin elements and quadrature ordering."""
import json
import numpy as np
from model import ROOT,PROJECT,BASIS,write_deck,execute,parse_and_check


def main():
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
