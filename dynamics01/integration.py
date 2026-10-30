"""Explicit additions to existing manifests; no second fabric or database."""
import copy
from router import digest
from world01.contracts import KIND
from world01.fabric import MANIFESTS,manifest
from live_fabric01.fabric import WORKERS
from .model import SCHEMA,MODEL,OPS,OBS
KIND[SCHEMA]=('COMPLEX_2D_COLLINEAR_NUCLEAR_PSI','bohr/Eh/atomic_time')
MANIFESTS['dynamics']=manifest('dynamics','Ordered collinear neutral H3 ground-doublet BO LSTH, COM removed','complex128 psi(x,y), two nuclear distances',OPS,OBS,['full_electronic_state','nonadiabatic_transfer','rotations','asymptotic_scattering_probability','arbitrary_external_field'],'Core01 LSTH single-surface nuclear TDSE; metric kinetic term, optional CAP','Pinned Core01 raw output and source hashes',MODEL['limitations'],'dynamics01.model.transition_arrays','bohr/Eh/atomic_time; 3 separated H reference')
MANIFESTS['dynamics']['evidence_level']='HISTORICAL_REAL_REPLAY_PLUS_OFFLINE_SOFTWARE_INTEGRATION; NEW_LIVE_NOT_EXECUTED'
MANIFESTS['dynamics']['dependencies']={'cloud':'Python3.12 NumPy2.2.6; gfortran only for LSTH preparation; shared runtime dependencies unchanged','local_engine_availability':'saved-Hamiltonian restore and software fixtures; no new H3 propagation authorized'}
WORKERS['dynamics']='dynamics01.worker via existing isolated live_fabric01.worker and outer cgroup'
