# Advanced study in progress

This separate extension preserves the supplied sixteen-body geometry and the three equal-thickness support architectures. It does not overwrite the earlier manuscript or simulation results.

## Planned questions and decision metrics

1. Does support-design ranking depend on the direction of prescribed skin extension?
2. Does a material choice remain favorable across assumed skin stiffnesses?
3. Do reduced wire strains trade off against higher skin disturbance or adhesive-interface loading?

The planned factorial inputs are support architecture (Uniform, Single, Graded), adhesive modulus (0.05, 0.10, 0.50 MPa), and skin modulus (0.10, 0.20, 0.50 MPa). These are analyst-selected sensitivity levels, not a patient population or probability distribution. Geometry, package surrogates, and perfect bonding remain fixed.

Three independent linear kinematic basis problems prescribe epsilon_xx, epsilon_yy, and engineering gamma_xy on the projected outer contour of the skin through its thickness, with out-of-plane motion free except one reference displacement. The contour includes the rounded footprint; filleted edge nodes projected inside the contour remain free. Tensor fields, rather than scalar stresses or percentiles, will be combined to reconstruct directional extension. The same constrained degrees of freedom are used for every basis problem. Directional extension includes nominal transverse contraction at nu=0.49. Perimeter kinematics represent controlled fixtures rather than a particular anatomical site.

All reported cases must pass execution, final-load, force/moment balance, and internal-versus-external energy checks. A homogeneous cube checks the analytical strain and stress tensors, shear convention, and energies. Direct mixed-loading solves must check tensor-field superposition. Selected refined meshes will assess the sensitivity of new decision metrics.

Metrics will include wire stress and principal strain, area-weighted skin–adhesive traction estimates without smoothing across materials, and the volume-weighted RMS perturbation of skin strain relative to a homogeneous skin reference. Interface metrics do not predict detachment without experimentally established strength/toughness. Skin disturbance is a mechanical metric, not a comfort, irritation, injury, or clinical-performance prediction.

## Audited geometric issue and controlled comparison

The supplied skin has a broad planar top at z=2.00 mm. The adhesive has a broad planar underside at z=2.01 mm, leaving a 10 micrometre gap. Contact in the supplied geometry is restricted to textured shared surfaces: 93.9964 mm2 on the h=1.7 mesh. This is distinct from the roughly 1600 mm2 adhesive footprint.

`mesh_contact.py` creates an explicit alternative by extruding the broad planar adhesive underside down by 0.01 mm and fusing that extension into the adhesive. It does not move or replace the skin, electronics, wires, or support partitions, and does not extend the textured protrusion tips. The filled adhesive adds 15.62998 mm3 before fragmentation. Its accepted h=1.7 mesh has 267146 quadratic tetrahedra, 412220 nodes, positive Jacobians, and 1659.0357 mm2 of shared skin–adhesive surface (including texture). Area exceeds projected footprint because it includes nonplanar features. This is a specified manufactured-contact scenario, not a correction asserted to describe the real device.

The main material/direction matrix will use the explicitly filled scenario, with the supplied-contact geometry retained as a sensitivity comparison. No outcomes from these two scenarios will be pooled or silently relabeled.

## Numerical pilot findings and acceptance gate

The original affine-perimeter pilot using the bundled PaStiX default mixed precision passed force and energy checks but failed a direct mixed-load comparison: relative displacement discrepancy 0.1335, stress discrepancy 0.001884, and strain discrepancy 0.001317. These outputs are exploratory and are excluded from final design ranking. This shows why force balance and energy balance alone are insufficient acceptance tests for these stiffness contrasts.

Setting `PASTIX_MIXED_PRECISION=0` did not change the precision reported by this particular binary on the tested linear path. An alternate symmetric PARDISO trial passed small benchmarks but failed assembly-level free-DOF equilibrium checks and is also excluded. That diagnostic trial used an existing Intel oneMKL runtime supplied with ANSYS Student's Lumerical installation; it did not run an ANSYS structural simulation. Neither that runtime nor its rejected fields are required for the accepted backend.

The current backend is Ubuntu 22.04's `calculix-ccx` package (2.17-3), running the SPOOLES solver under WSL. Both Windows SPOOLES builds crashed on the large assembly and were replaced by the Linux build, not treated as completed solves. Runs execute in a native Linux directory and copy completed outputs to the project in bulk. The eight analytical/direct-mixed cube cases and independent high-contrast quadratic comparisons pass the revised checks. Full-assembly direct superposition remains a separate gate before accepting directional envelopes.

Recovered pointwise traction mismatch between the skin and adhesive sides exceeded 100% in the unaccepted mixed-precision pilot. Such traction estimates are diagnostic only unless further accuracy and refinement checks support them; they will not automatically be treated as validated interface-load predictions. Adhesive strain-energy measures and skin-strain perturbation offer additional, explicitly mechanical comparison metrics.

## Reproduction sequence in this environment

Install the Python packages in `requirements.txt`. The accepted backend additionally needs WSL with an Ubuntu 22.04 installation and its `calculix-ccx` package. `BIOSENSOR_WSL_DISTRO` can override the distribution name; `BIOSENSOR_WSL_RUN_ROOT` can override the native temporary run directory. The Windows backend switches are retained for diagnostic provenance and do not constitute accepted replacement solvers.

```powershell
python advanced/verify_basis.py
python advanced/verify_independent.py
python advanced/verify_refinement.py
python detailed/mesh_assembly.py --h 1.7 --wire .14
python detailed/mesh_assembly.py --h 1.2 --wire .10
python advanced/mesh_contact.py --h 1.7 --wire .14
python advanced/mesh_contact.py --h 1.2 --wire .10
python advanced/verify_meshes.py
python advanced/bare_skin_reference.py
python advanced/run_study.py --phase pilot
python advanced/run_expanded.py
python advanced/reanalyze.py
python advanced/summarize.py
python advanced/run_refinement.py
python advanced/finalize_analysis.py
python advanced/plot_geometry.py
python advanced/plot_results.py
# Only after complete numerical acceptance and figure review:
python advanced/build_manuscript.py
./advanced/normalize_word_layout.ps1
# Review every rendered PDF page before packaging:
python advanced/package_research.py
```

The expanded runner first verifies the supplied-geometry direct gate, evaluates all three supplied-contact architectures at nominal materials, verifies the filled-geometry direct gate, and then evaluates its 27 material configurations with three basis loads each. Each configuration receives its own direct 45-degree mixed-load validation. This is 90 medium-mesh basis cases plus 30 direct validation cases. Verified residual-correction solves may be required in addition; they are numerical auxiliary solves, not new physical cases. Refined-mesh checks and the final new manuscript remain subsequent steps. The script stops at a remaining numerical failure; it does not silently relax acceptance to finish the matrix.

The residual-correction path is documented in [NUMERICAL_REVIEW.md](NUMERICAL_REVIEW.md) and tested by `verify_refinement.py`, which includes the point-load semantics test. Run that verification after `verify_basis.py` before a fresh extended batch. No manufactured verification data are used as biosensor-study results.

The independent quadratic comparison covers modulus ratios 10, 392500, and 1570000 at Poisson ratio 0.49. It checks displacement and volume-weighted element-mean stress/strain tensors against scikit-fem. The largest ratio matches the extreme gold/adhesive modulus ratio in the material grid. All three comparisons pass with relative discrepancies below 1.2e-7. These are numerical benchmark comparisons, not physical calibration or pointwise error bounds for the actual assembly.

The skin-disturbance metric in the final analysis uses a device-free finite-element reference on exactly the same textured skin elements and quadrature points. A homogeneous affine reference alone would also include effects of the textured geometry. `bare_skin_reference.py` builds the matched references, and `reanalyze.py` rebuilds all medium-mesh response profiles. The final summarizer rejects the earlier affine-reference profiles. Since Poisson ratio is fixed and reference loading is purely prescribed displacement, multiplying the homogeneous bare-skin modulus by a scalar leaves its strain field unchanged; the reference therefore serves every effective skin modulus in the grid.

For corrected cases, `fields.npz` contains the accepted field sum, while the base `job.dat`/`job.frd` retains the initial uncorrected solve. Use the NPZ fields together with `checks.json` and `residual_refinement_history.json` for accepted plots; do not treat the initial FRD as the corrected solution. Raw correction inputs and outputs remain under each case's `correction_*` folders.

For a compute-first resume, `run_expanded.py --defer-analysis` completes verified FE cases without response-profile generation. Follow it with `bare_skin_reference.py` and `reanalyze.py`, then the refinement and finalization stages above. Do not launch a second driver while an existing study process is live.

After all twelve bare-skin references and the verification prerequisites exist, `python advanced/run_pipeline.py` sequences an early fine-mesh nominal control, the complete medium-mesh study, response reconstruction, refinement, final checks, and figures. It stops on a failed command and deliberately leaves manuscript construction and page inspection separate. Cached accepted cases are reused on a subsequent resume.

The fine filled-contact model exceeded the WSL allocation of approximately 15.4 GiB RAM plus 4 GiB swap during its first factorization. That attempt was terminated by the kernel and is not an accepted solve. Its execution record and log are retained in `failed_memory_attempt_001` under the affected case. A task-owned 12 GiB temporary swapfile at `/var/tmp/biosensor-advanced.swap` was then enabled in Ubuntu-22.04 for the retry, leaving the existing swap allocation intact. The fine nominal Uniform configuration subsequently passed all four solves and its direct superposition gate. This changes available memory, not the model or numerical gates. Before later large solves, `model.py` re-enables this existing task-owned file if WSL has restarted; it does not create files or change persistent system settings. The temporary file can be disabled and removed after all solvers finish. See `verification/memory_recovery.json` in the retained numerical records.

After the final manuscript has passed layout inspection, `python advanced/package_research.py` builds size-limited research archives and verifies every archived file against its SHA256. The package index distinguishes all accepted-case inputs and records from selected retained field arrays. The selected fields cover the fine nominal filled Uniform assembly, all twelve bare-skin controls, and every corrected assembly case's initial/accepted arrays with its raw correction DAT outputs. This preserves evidence for inspecting the correction sums. Other assembly arrays are reproducible from their retained decks. The packager requires the completed summary and a six to eight page final PDF, and excludes provisional response profiles from unrelated solver trials.

The proposed scope remains a computational mechanical design study. Material calibration, hidden chip internals, electrical drift, fatigue, and human outcomes are not invented. Advanced here means stronger questions, multiaxial boundary conditions, uncertainty exploration, and better verification; a favorable design result is not guaranteed.
