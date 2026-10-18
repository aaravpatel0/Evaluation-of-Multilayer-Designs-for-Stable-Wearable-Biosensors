# Source audit and separation of studies

The linked Drive folder was inspected before defining the new computational study. Bounded readable text was retrieved from the files in manifest.json. Images embedded in source documents were not treated as machine-readable raw simulation fields.

## Conflicts affecting reuse of older numbers

- The revised BEB8360 abstract reports maximum displacement values around 0.0011 to 0.0018 mm while describing a prescribed skin displacement of 1 mm. These cannot be whole-model displacement maxima in the same units and load state. They might describe a sensor-only subset or a different result quantity, but the available text does not establish that. The new paper therefore reports gold stress and strain explicitly instead.
- The original bufferless APDL script specifies 0.20 mm PDMS, while the later 'Joel's New ANSYS Stuff' document and corrected abstract describe 0.40 mm for the uniform reference. The new study adopts a controlled 0.40 mm total support for all designs and documents it.
- The APDL scripts prescribe only a bottom-left pin and downward right-skin displacement, enable geometric nonlinearity, and use 1 mm displacement over a 5 mm span. The new study deliberately uses a distributed left-skin clamp and smaller displacements in a linear formulation. It does not claim equivalence to that large-motion boundary-value problem.
- 'ANSYS parameters' and 'Simulation Pictures and Results' contain a TPU-based material set with different moduli, Poisson ratios, and thicknesses. This set is not blended into the new PDMS-based model.
- 'group 24 abstract' describes a separate three-dimensional hyperelastic model and contains legacy mean stresses of 7.82/6.50/6.31 MPa in stretching. Its material labels 'initial yield' and 'incompressibility' do not unambiguously define a Neo-Hookean law with consistent units. Those values are not used as new outputs or calibration targets.
- Prior statements that no sensor deformation occurred, no design approached failure, or small differences were numerical noise lack a reported numerical or experimental basis in the readable summaries. The new manuscript does not repeat them.

## Current computational study

All reported numerical results come from the Python files supplied here. The geometry is a controlled two-dimensional PDMS-family simplification with equal support thickness; it is not the imported STEP geometry or the original three-dimensional model. Material properties are design assumptions inherited from the later project family, not experimentally calibrated constants. Only the current study's means, upper-tail measures, strains, energies, mesh histories, and controlled perturbations appear in the manuscript.

Authorship and affiliation follow the user's supplied order and OPALS designation. A previous source included an email, but the user explicitly said emails would be supplied later, so that older email was not adopted.
