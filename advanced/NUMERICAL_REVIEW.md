# Numerical review and acceptance requirements

The purpose of this extension is to improve the scientific usefulness of the same multilayer biosensor design comparison. Adding a large parameter matrix is insufficient if the assembly solves do not satisfy local equilibrium.

## Findings from actual retained fields

- `verification/existing_field_equilibrium_audit.json` audits the 19 earlier linear assembly results and the available exploratory affine-perimeter fields. For the earlier 19 cases, the L2 norm of force output on free displacement DOFs divided by that on constrained DOFs ranges from 0.0006835 to 0.1925774. These are equilibrium residual measures, not stress-error bounds.
- The original PaStiX affine-perimeter pilot failed direct 45-degree tensor superposition: relative displacement error 0.1335312, force error 0.0101001, stress error 0.0018840, and strain error 0.0013171. It is excluded from final design analysis.
- The installed PaStiX binary reports mixed precision and does not expose the attempted mixed-precision environment override in the tested linear path. A binary string inspection found no PASTIX_MIXED_PRECISION setting. Upstream current source supports that setting, but its behavior must not be assumed for this executable.
- The alternate symmetric PARDISO assembly pilot also has excessive free-DOF residuals: approximately 1.3566 for XX and 1.6826 for YY. Its small homogeneous benchmarks pass; those benchmarks alone do not establish assembly accuracy. It is excluded from final design analysis. The incomplete direct45 PARDISO trial was deliberately stopped after these failures were identified.

## Energy-check correction

The solver's NALL force output can include residuals on free DOFs. Summing one half of u dot RF over every DOF includes those residuals and can make an inaccurate solve appear energy-consistent. The revised check uses only prescribed-DOF reactions for external work. Contributions at free DOFs are recorded separately and must be small. The total-force sum is retained as a consistency check, not proof of local equilibrium.

## Revised acceptance requirements

1. Solver execution completes at final load time 1 with no errors, and the requested solver appears in its log.
2. Homogeneous cube normal/shear stress and strain tensors match analytical plane-stress solutions for nu=0.30 and 0.49. Direct mixed-load cube solves agree with tensor superposition.
3. Free-DOF relative force residual is below 1e-5; prescribed-DOF external work agrees with integrated strain energy within 5e-4; force and moment sums and prescribed displacements pass their separate checks.
4. Full-assembly direct 45-degree loading agrees with the three independent basis solutions to relative field error below 2e-5 before directional response envelopes are accepted.
5. New comparison metrics are checked on refined meshes, with measured changes reported rather than represented as rigorous error bounds.
6. Interface pointwise tractions are diagnostic unless interface recovery and refinement justify quantitative conclusions. Material calibration, electrical behavior, adhesion strength, comfort, and clinical outcomes remain outside the proven results.

The current pilot uses the SPOOLES solver in Ubuntu 22.04's CalculiX 2.17 package under WSL. Both official Windows SPOOLES executables crashed on the full assembly (exit code 3221225477), despite passing the small benchmarks. They are not accepted assembly results. All eight homogeneous/direct-mixed verification cases pass the revised energy and free-DOF residual checks with the Linux solver. Independent scikit-fem comparisons also pass for elastic contrasts 10, 392500, and 1570000 at nu=0.49. The highest ratio covers the largest gold/adhesive modulus contrast in the selected material grid; its relative displacement discrepancy is 1.13e-7. The verification cubes use common Poisson ratio 0.49 and are numerical comparisons, not additional biosensor material configurations. Full-assembly acceptance must be established from its own outputs; a running solver is not a passed test.

## Verified linear defect correction

The Linux backend passed the Uniform and Single supplied-contact basis cases and their direct mixed-load comparisons, but the Graded XX case initially had free-DOF relative residual 0.0426040. A zero-prescribed-displacement correction with negative residual nodal loads reduced the residual to 1.56699e-7 in one solve; the revised energy check is 4.30e-9. This numerical correction preserves the original linear FE equations and physical inputs. It does not relax any acceptance threshold.

`residual_refinement.py` retains the initial fields/checks and correction input decks, logs, and field-construction history. `verify_refinement.py` labels its injected perturbation as a manufactured numerical-error verification problem, not research data: verified cube fields plus 0.02 times a separately solved point-load field. One correction recovers displacement, force, stress, and strain to relative error below 9e-10. A separate point-load cube confirms that the reported free-node force equals internal force, including the applied load, as required for the field-sum correction.

The batch invokes up to three correction steps on a failed local-equilibrium case, stops on divergence or a remaining failure, and directly validates mixed loading for every material configuration. Corrected fields are identified explicitly in their checks and retained alongside uncorrected outputs.
