import simulation as s
import csv
rows=[]
def keep(row):
    rows.append(row)
    with (s.OUT/'controls.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
for r in [8,16]:
    for design in ['Matched','Reverse']:keep(s.solve(design,'Tension',r,save=True))
for soft in [.05,.2]:
    for design in ['Single','Graded']:keep(s.solve(design,'Tension',8,soft=soft))
for skin in [.1,.4]:
    for design in s.NAMES:keep(s.solve(design,'Tension',8,skin=skin))
