# Biosensor project

The expanded study is in [detailed/README.md](detailed/README.md). Its revised proceeding, original-CAD 3D viewer, component results, and numerical audit are in `detailed/output/`. It includes the actual sixteen supplied CAD bodies and uses CalculiX for the 3D structural solves. Use the detailed study for component-level assembly questions. Its assumptions, inputs, and results differ from the earlier 2D screen below.

## Earlier 2D proceeding and reproducible simulation

The manuscript is an eight-page computational study in the official Avestia/JBEB two-column layout. It contains five figures, four tables, seven verified references, and the author list supplied in this chat. The calculations are a new, explicitly specified linear-elastic plane-strain study. They are not a rerun of the old ANSYS or Fusion 360 outputs.

## Open first

- `output/Biosensor_Proceeding.docx`: editable manuscript.
- `output/Biosensor_Proceeding.pdf`: PDF exported directly from Microsoft Word and visually reviewed page by page.
- `results/metrics.csv`: 55 nominal, refinement, and coarse sensitivity solves.
- `results/controls.csv`: 14 compliance-control and material sensitivity solves.
- `results/verification.json` and `results/audit.json`: numerical checks and refinement changes.
- `output/figures/`: high-resolution PNG and vector PDF plots.

## Main result

Under 1% prescribed skin extension, the finest-mesh gold mean von Mises stresses are 1.450668 MPa (uniform PDMS), 0.533523 MPa (single soft buffer), and 0.662378 MPa (graded buffer). Single and graded buffers reduce the mean by approximately 63.2% and 54.3%. This ranking also holds for the specified transverse displacement. The graded pair is not the best isolator in this controlled study. A homogeneous buffer matched to the pair's elementary series shear compliance gives nearly the same mean response.

These are simulated elastic mechanical responses. They do not establish signal stability, electrical drift reduction, fatigue life, delamination resistance, or a device failure threshold.

## Model definition

Units: mm, N, MPa; unit out-of-plane width. Domain length 5 mm; skin thickness 2 mm; support thickness 0.4 mm in every architecture; gold thickness 0.02 mm over x = 0 to 1 mm; encapsulation 0.1 mm. All interfaces are perfectly bonded. Gold modulus 110000 MPa and Poisson ratio 0.34; skin, soft, medium and PDMS moduli are 0.2, 0.1, 0.5 and 1.8 MPa, respectively, with Poisson ratio 0.49.

Left skin edge is fixed. Right skin edge is prescribed +0.05 mm horizontally (with vertical motion fixed), -0.025 mm horizontally (with vertical motion fixed), or -0.05 mm vertically (horizontal motion free). Other boundaries are traction-free. The transverse case is not pure bending. Small-strain linear elasticity cannot represent buckling or nonlinear compression.

Four-node quadrilaterals use full integration of deviatoric stiffness and central integration of volumetric stiffness. Five nominal mesh levels span 50 to 800 elements along the length, with proportional through-thickness refinement. The finest models contain 243200 or 294400 elements. Gold stresses are first averaged over four Gauss points per element and then area-weighted over the gold region. The 95th percentile is an area-weighted element-average quantile, and maxima refer to cell averages, not extrapolated nodal values.

Mean gold stresses change by less than 5% from the penultimate to finest mesh; this is not a rigorous error bound. Upper-tail stresses and mean axial strain converge more slowly. An analytical homogeneous plane-strain tensile reaction and assembled affine patch test are reproduced to floating-point precision. An independent solver comparison and physical calibration are future work.

## Rerun

Use Python 3.12 in an environment with the pinned dependencies:

```powershell
python -m pip install -r requirements.txt
python run_all.py
./render_word.ps1 -InputDocx output/Biosensor_Proceeding.docx -OutputPdf output/Biosensor_Proceeding.pdf
```

The final command needs Microsoft Word on Windows. The computations and DOCX build do not. Runtime depends strongly on sparse linear algebra and available memory; several minutes are expected, with substantially more work on the finest grids. `simulation.py` and `refine.py` must run before `controls.py`, because the nominal CSV is rebuilt at the start. `run_all.py` enforces that order. Sensitivity fields are not saved; nominal and control fields are stored as NPZ files. Refinement runs overwrite the lower-resolution NPZ with the finest fields while retaining every scalar result in CSV.

## Items for author review before submission

1. Supply the corresponding author and email. They were intentionally not guessed. Confirm the institutional postal address if a department-specific address is required.
2. Confirm the venue. The supplied folder contains ICBEB 2026 materials, while JBEB is associated with ICBES. The manuscript uses the official Avestia/JBEB template provisionally. ICBES allows full papers up to eight pages: https://icbes.net/author-guidelines.html. JBEB author instructions: https://www.avestia.com/guidelines/. ICBEB instructions differ: https://www.icbeb.org/SubmissionInstructions.
3. All named authors should review the model change, results, interpretation, and final manuscript. The new controlled study replaces, rather than confirms, the earlier poster's headline numbers. Confirm funding, contributions, conflicts, and prior dissemination for the submission form; none were invented.
4. This session used AI assistance to implement and run the solver, prepare figures, verify references, and draft the manuscript. Authors should independently review the code and claims and provide any disclosure required by the final venue.

No manuscript has been submitted, emailed, or published. No source Drive files were edited.

## Provenance

`sources/manifest.json` lists the retrieved project documents and their original Drive URLs. `sources/Source_Audit.md` explains conflicts between earlier inputs and why their outputs were not pooled. `sources/Avestia_Template.docx` is retained unchanged. Template SHA-256: ead110654087bd99d49605b107bacd12139ef9ad7eecb9f2ca45cbf085f7ead3.

The supplied project design family motivated geometry and material inputs. The manuscript's scientific references support background and numerical methods; they do not serve as experimental calibration of this device.
