# Detailed three-dimensional biosensor study

This study supersedes the simplified 2D screen for questions about the supplied CAD assembly. It uses the original sixteen-body STEP file, including five generic sensor components, the ABS sensor body, the transmitter, the two routed gold wires, other gold and ABS features, skin, adhesive, PDMS, and the cover.

## Software attribution and accuracy

- Gmsh 4.15.2 imports the STEP solids, fragments overlaps, and produces conforming quadratic tetrahedral meshes.
- CalculiX CrunchiX 2.23 performs the 3D structural simulations using C3D10 elements and PaStiX. This is an established structural finite-element solver, separate from the earlier custom 2D code.
- Python 3.12.14, NumPy 2.3.5, and SciPy 1.18.1 automate inputs and post-process results. scikit-fem 12.0.2 independently assembles verification problems.
- ANSYS was not used to generate the reported 3D results. No claim of ANSYS-equivalent predictive accuracy is made. Numerical verification, mesh sensitivity, and physical calibration are distinct requirements.

The three quadratic meshes contain 210774, 272194, and 374893 tetrahedra and 1037325, 1309173, and 1750458 displacement DOFs. All accepted meshes have positive Jacobians. The full-resolution mesh is a connected assembly. The homogeneous benchmarks reproduce the analytical 0.01 N tensile reaction, and independent scikit-fem displacement fields agree to less than 6e-8 relative error in the three benchmark problems. These checks do not validate the physical material choices.

## Material assumptions

The user confirmed that part numbers and specifications for the generic sensor components and transmitter were unavailable and authorized representative material selection. They remain surrogate assumptions in the manuscript, not identified manufactured materials.

Nominal E in MPa and Poisson ratio:

| Region | E | Poisson ratio | Basis |
|---|---:|---:|---|
| Skin | 0.20 | 0.49 | Representative screening assumption; not a measured anatomical site |
| Adhesive | 0.10 | 0.49 | Unidentified compliant adhesive surrogate |
| PDMS / cover | 1.80 | 0.49 | Representative project-family input; not formulation calibration |
| Soft replacement | 0.10 | 0.49 | Controlled design parameter |
| Medium replacement | 0.50 | 0.49 | Controlled design parameter |
| ABS bodies | 2300 | 0.35 | Representative isotropic ABS; grade unconfirmed |
| Five sensor packages | 10000 | 0.30 | Homogeneous package surrogate; not a resolved bare silicon die |
| Transmitter body | 20000 | 0.30 | Homogeneous stiff-board/package surrogate; no resolved FR-4 layup |
| Gold-labeled features and wires | 78500 | 0.42 | Representative bulk-gold supplier values; actual film/wire grade unconfirmed |

Gold source: https://www.goodfellow.com/usa/gold-pellets-group. PDMS and skin background references are provided in the paper. The package stiffness sweep spans 2000–130000 MPa; adhesive stiffness spans 0.05–0.50 MPa. These are selected sensitivity ranges, not statistical confidence intervals.

## Geometry and interface treatment

The STEP file has a central ABS stem overlapping adhesive by 3.769911 mm³ and PDMS by 12.566371 mm³. Fragmentation assigns the shared volume to ABS rather than double-counting it. The stem remains in the model; it provides a local load path through the support. The original 1 mm PDMS is partitioned into 0.25, 0.25, and 0.50 mm regions for the equal-thickness material comparison. Uniform assigns 1.8 MPa throughout; Single assigns 0.1 MPa to the lower half; Graded assigns 0.1 and 0.5 MPa to its lower quarters, retaining 1.8 MPa in the upper half.

Interfaces are perfectly bonded. Solder joints, internal dies, copper traces, and routing channels are included only where they already exist as explicit CAD geometry; their existence or material identity is not invented. The two supplied gold wire routes are explicit solid regions. No electrical, RF, thermal, biomarker, fatigue, or fracture simulation is claimed.

## Cases

The quantitative study contains 19 converged linear assembly solves: extension for all three supports on all three meshes; transverse displacement and shortening for all supports on the intermediate mesh; two sensor-package stiffness changes; and two adhesive stiffness changes. Three independent/analytical benchmark problems and a small hyperelastic initialization comparison are also provided.

The left skin edge is fixed in all three components. Right skin edge motions are +0.60 mm in x for extension, -0.30 mm in x for shortening, or -0.60 mm in z for the transverse case; other right-edge components remain free. Other external surfaces are traction-free. The transverse case is not pure bending. Linear shortening does not assess buckling or nonlinear compression.

Exploratory nonlinear attempts used W = C10*(I1bar - 3) + (J - 1)^2 / D1, with C10 = E/[4(1+nu)] and D1 = 6*(1-2nu)/E for soft constituents. Zero-displacement and linear-field initializations showed growing assembly equilibrium residuals and were halted without a converged full-load result. Their stress fields are excluded from the quantitative study. The initialization methods agree in the separate small hyperelastic cube, but this does not demonstrate assembly convergence. `output/Nonlinear_Trial_Status.json` records the limitation. Further continuation, calibrated constitutive inputs, and an independent nonlinear reconstruction are required. No finite-deformation accuracy is claimed.

## Files

- `output/Biosensor_Proceeding_3D.docx` and `.pdf`: revised proceeding.
- `output/Biosensor_3D_Viewer.html`: self-contained interactive mesh viewer; toggle regions in its legend.
- `output/All_Component_Results.csv`: component metrics for every completed assembly case.
- `output/Study_Audit.json`: mesh changes, connectivity, and force balance.
- `meshes/h*/mesh.npz`: accepted nodal coordinates, C3D10 connectivity, and material region IDs. Connectivity is in CalculiX/Abaqus tetra10 order.
- `runs/*/job.inp`: actual input decks; `solver.log` and `execution.json` establish execution status; `metrics.json` and `part_metrics.csv` hold scalar results.
- `runs/*/fields.npz`: complete nodal displacements/reactions and electronic-body Gauss-point stress/strain fields. The compact ZIP includes selected finest-mesh extension fields; all case fields remain in the workspace and can be regenerated.
- `verification/`: independent and analytical comparison outputs.
- `output/ANSYS_Comparison/`: a matched linear extension APDL deck generated for later comparison. **It has not been executed in ANSYS.** It requires a suitable MAPDL installation/license and should be reviewed before running.

Stress and strain are taken from integration points, not smoothed nodal FRD values. Means are weighted by undeformed volume; each C3D10 Gauss point receives one quarter of its element volume. Principal-strain metrics are absolute tensor eigenvalue measures. Nonlinear strain is Lagrangian. Maxima are Gauss-point values and are not failure thresholds.

## Reproduce

Install the packages in `requirements_3d.txt` and the official CalculiX Windows executable from https://dhondt.de/calculix_2.23_4win.zip. Extract the archive under `detailed/tools/calculix223/`, preserving its `calculix_2.23_4win` subfolder. The script expects `ccx_static.exe` there. The executable is downloaded from the solver author's official site; it is not included in the compact research ZIP.

From the project root:

```powershell
python detailed/inspect_cad.py
python detailed/prepare_cad.py
python detailed/mesh_assembly.py --h 2.5 --wire .20
python detailed/mesh_assembly.py --h 1.7 --wire .14
python detailed/mesh_assembly.py --h 1.2 --wire .10
python detailed/verify_3d.py
python detailed/verify_warm_start.py
python detailed/run_study.py
python detailed/run_extensions.py
python detailed/visualize_assembly.py
python detailed/build_detailed_paper.py
./render_word.ps1 -InputDocx detailed/output/Biosensor_Proceeding_3D.docx -OutputPdf detailed/output/Biosensor_Proceeding_3D.pdf
```

Allow substantial memory for the largest sparse factorization. Cases should run sequentially. `run_study.py` reuses successfully completed cases and regenerates missing field files when rebuilding from the compact ZIP. `run_extensions.py` runs the four linear material sensitivities by default. The additional `--nonlinear` switch is exploratory and is not part of the verified reproduction path; its current assembly protocol has not converged. The rebuild scripts need the retained template and formatting helpers in the project root, which are included in the ZIP's original directory layout.

## Author review

Confirm the venue and corresponding-author email before submission. All authors should review the changed geometry, assumptions, and conclusions. The 3D assembly results must not be presented as confirmation of the earlier 2D percentages. AI assistance was used to implement the workflow and draft the manuscript; authors should independently review the work and follow the venue's disclosure requirements. No submission or publication has been made.
