"""Controlled gap-filled adhesive scenario; original electronics and skin do not move."""
import argparse, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.append(str(ROOT.parent/'detailed'))
from mesh_assembly import build

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--h',type=float,default=1.7)
    parser.add_argument('--wire',type=float,default=.14)
    args=parser.parse_args()
    build(args.h,args.wire,contact_fill_mm=.01,dest_root=ROOT/'meshes/filled')
