# QW-NEXT: finite repair, then periodic matter extension

Historical W1, Foundation02 and02R observations/failed runs/STOP/qualifications remain unchanged. New files do not make old failed runs successful.

## Finite cloud recovery (authorization required)

One standard Ubuntu15min Job only. Same W1 base digest and PySCF/NumPy/SciPy pins. Exactly two import-only children differ only in RLIMIT_DATA512MiB vs inherited limit; no molecular build/SCF in these probes. Import-stage results can support only an import-stage association. They cannot prove that the same limit caused every historical SIGSEGV. The inherited-limit probe must pass before one frozen HF1.10 request is attempted. No cloud retry or environment scan.

The real science child does not set a new process DATA/AS cap. It preserves the outer1GiB/1CPU/no-swap/no-network cgroup and independent process supervision. Stage logs START, IMPORT, MOLECULE_BUILD, SCF_START/END, GRADIENT_START/END are flushed to disk. No physical geometry/prediction is reselected. The frozen request bytes and source observation hash remain the02R originals. Failure stops this tranche. A numeric comparison is not a W3 qualification without current AI interpretation of actual returned physics.

## Selected next module: periodic matter construction / PySCF-PBC

`qw_next.periodic_world` extends the same WorldSpec envelope with `matter.type=periodic_cell`, lattice in Angstrom and explicit3D periodicity. It does not reinterpret an ASE geometry as a quantum wavefunction. `WorldSpec.next.schema.json` is a compatible structural union; runtime checks narrow admission further. Old molecule validation and history remain intact.

Current bounded implementation: neutral spin-zero periodic cells, elementsH..Ar,1..4atoms/<=30 all electrons, gamma-only all-electron RKS/PBE/cc-pVDZ with Gaussian density fitting/weigend and Becke level1. ASE constructs and checks periodic nuclear distances. Cells and coordinates can receive bounded affine scaling, preserving fractional positions. No material is hardcoded and no material candidate is the default input. No automatic parameter scan/relaxation/dynamics. CLI requires user WorldSpec: `python -m qw_next.periodic_world spec.json out` in a separately admitted solver process. The direct solver also fails closed without the resource cgroup.

This source has NOT physically run. Cell/basis/grid/k-mesh convergence, resources, periodic ASE backend construction and force/stress remain unverified. Only energy is implemented; forces/stress deliberately refused. Metallic occupations, charged cells, nonzero spin, lower-dimensional/slab corrections, k-mesh sampling, dynamics and macroscopic stability are out of this first adapter. Runtime basis availability is checked by PySCF and cannot be presumed for every element from schema inclusion alone. Errors remain OUT_OF_MODEL_DOMAIN/PHYSICALLY_INVALID/ENGINE_UNAVAILABLE/UNVERIFIED/BLOCKED, never physical success.

Energy reference is neutral periodic BO/PBE per specified cell, NOT interchangeable with molecular RHF/cc-pVDZ absolute totals. No projection from a Gaussian molecular wavefunction to a periodic density is assumed. This remains the PySCF code family, not W2 independent engine proof. No periodic scientific calculation is included in the requested single W3 cloud Job.

Software QA: stdlib structural constraints/strain/comparison-blocking/stage persistence only. No PySCF/ASE backend run or invented material energy. Sources: https://pyscf.org/user/pbcgto.html ; https://pyscf.org/user/pbc/scf.html ; https://pyscf.org/user/pbc/df.html . The architecture manifest and candidate-priority rationale are preserved in this tranche's capability map, without altering the overall design.
