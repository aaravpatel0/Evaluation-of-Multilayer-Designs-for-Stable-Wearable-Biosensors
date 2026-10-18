import simulation as s
import csv,json
rows=list(csv.DictReader((s.OUT/'metrics.csv').open()))
for r in [8,16]:
    for design in s.NAMES:
        for mode in ['Tension','Bending']:
            row=s.solve(design,mode,r,save=True); rows.append(row)
            with (s.OUT/'metrics.csv').open('w',newline='') as f:
                w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
