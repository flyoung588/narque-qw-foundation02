# QW-INTERACTIVE-01 incremental runtime

`world.Store` persists immutable content-addressed states; `world.apply` maps
explicit actions to new WorldSpecs. `world.transition` saves the candidate and
intent before calling the inherited independent solver supervisor. A failed
result cannot erase the parent. The public `runtime.run_stage` binds a separately
frozen Work decision to its first observation and action. It is not an AI model.

Run local synthetic tests (no PySCF import):
`python -m unittest interactive01.test_software -v`

Cloud execution is **not yet authorized**. SCOPE prevents science until a new
Human approval and exact request hash are bound. Stage 1 measures the proposed
MgO state. Stage 2 has no request yet: current Work AI must read Job 1, select an
action or STOP, and freeze a separate request. The offline runner never invents
the next action. Operator must audit prior run/attempt count before each manual
dispatch; code alone cannot establish Human authorship or remote once-only use.

Action bounds: displacement at most 0.05 Angstrom, or positive deformation F
with ||F-I||_2 <=0.02, explicit fixed_cartesian/preserve_fractional. Composition,
charge, spin, theory, basis, k mesh and numerical settings are unchanged. PBC
energy only; analytic periodic forces, stress, dynamics and optimization absent.
Finite structural energy differences are not forces or stability proofs.

Every cloud job uses one independent solver invocation. Existing KRKS diagnostics
retain occupations, Tr(DS), realspace electron integral, residuals, GDF paths and
raw arrays. Different realized GDF/grid settings must be disclosed in comparison.
No extra SCF is silently allocated for warnings. Failure stops, no automatic retry.
