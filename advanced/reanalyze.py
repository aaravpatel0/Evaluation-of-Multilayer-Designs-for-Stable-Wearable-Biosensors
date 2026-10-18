"""Rebuild medium-mesh metrics using matched bare-skin FE references."""
import itertools
from postprocess import analyze
from summarize import summarize


def main():
    for design in ['Uniform','Single','Graded']:
        analyze(1.7,design,.2,.1,'Supplied')
    for design,skin,adhesive in itertools.product(['Uniform','Single','Graded'],[.1,.2,.5],[.05,.1,.5]):
        analyze(1.7,design,skin,adhesive,'Filled')
    summarize()


if __name__=='__main__':
    main()
