"""General Bravais-cell + fractional-basis constructor. No named-material solver paths.

Coordinates and cell vectors in Angstrom; only the exact previously admitted
WorldSpec periodic model is emitted. Prototype seeds are AI choices outside
this module, not hardcoded in the physics adapter.
"""
import math
import re
from .io import digest

_FCC = ((0, .5, .5), (.5, 0, .5), (.5, .5, 0))
_BCC = ((-.5, .5, .5), (.5, -.5, .5), (.5, .5, -.5))
_CUBIC = ((1, 0, 0), (0, 1, 0), (0, 0, 1))
_LATTICE = {'fcc_primitive': _FCC, 'bcc_primitive': _BCC,
            'simple_cubic': _CUBIC}
_Z = {symbol: idx+1 for idx, symbol in enumerate(
    ('H','He','Li','Be','B','C','N','O','F','Ne','Na','Mg','Al','Si','P','S','Cl','Ar'))}


def _vector(frac, vectors):
    return [sum(float(frac[i]) * vectors[i][j] for i in range(3)) for j in range(3)]


def min_periodic_separation(cell, atoms, image_range=2):
    """Preflight screening only; actual ASE periodic neighbor check is authoritative.

    Enumerates translations in [-image_range,+image_range]^3 for small prototype
    cells; never claims global correctness on arbitrary skewed lattices.
    """
    if not atoms:
        raise ValueError('EMPTY_BASIS')
    best = float('inf')
    for i, x in enumerate(atoms):
        for j, y in enumerate(atoms):
            for u in range(-image_range, image_range+1):
                for v in range(-image_range, image_range+1):
                    for w in range(-image_range, image_range+1):
                        if i == j and u == v == w == 0:
                            continue
                        delta = [
                            y[k] - x[k] + u*cell[0][k] + v*cell[1][k] + w*cell[2][k]
                            for k in range(3)]
                        dist = math.sqrt(sum(t*t for t in delta))
                        if dist < best:
                            best = dist
    return best


def from_prototype(proposal):
    """Take AI-supplied prototype, return a generic, domain-bounded WorldSpec.

    proposal: {'id','bravais','lattice_a_angstrom','basis':[{'element',
    'fractional'}], 'rationale', 'prediction', 'falsifier'}.
    """
    for k in ('id','bravais','lattice_a_angstrom','basis','rationale','prediction','falsifier'):
        if k not in proposal:
            raise ValueError('MISSING_PROPOSAL_FIELD:'+k)
    if proposal['bravais'] not in _LATTICE:
        raise ValueError('BRAVAIS_NOT_SUPPORTED')
    identifier = proposal['id']
    if not isinstance(identifier, str) or not re.fullmatch(r'[A-Za-z0-9._-]{1,100}', identifier):
        raise ValueError('INVALID_ID')
    a = proposal['lattice_a_angstrom']
    if type(a) not in (int, float) or not math.isfinite(a) or not 2.0 <= a <= 12.0:
        raise ValueError('OUT_OF_BOUNDED_LATTICE_PARAMETER')
    if not all(isinstance(proposal[k],str) and len(proposal[k].strip())>=10
               for k in ('rationale','prediction','falsifier')):
        raise ValueError('MISSING_SCIENTIFIC_INTENT')
    basis = proposal['basis']
    if not isinstance(basis,list) or not (1<=len(basis)<=4):
        raise ValueError('OUT_OF_BOUNDED_BASIS')
    cell = [[float(a*x) for x in row] for row in _LATTICE[proposal['bravais']]]
    atoms = []
    ne = 0
    for item in basis:
        if not isinstance(item,dict) or set(item)!={'element','fractional'}:
            raise ValueError('INVALID_BASIS_ENTRY')
        sym = item['element']
        frac = item['fractional']
        if sym not in _Z or not isinstance(frac,list) or len(frac)!=3 or any(
            type(v) not in (int,float) or not math.isfinite(v) or not 0.0<=v<1.0 for v in frac):
            raise ValueError('UNSUPPORTED_ELEMENT_OR_FRACTIONAL_COORDINATE')
        ne += _Z[sym]
        atoms.append({'element':sym,'xyz_angstrom':_vector(frac,cell)})
    if ne>30 or ne%2:
        raise ValueError('UNSUPPORTED_ELECTRON_NUMBER_OR_CLOSED_SHELL_PARITY')
    if len({tuple(round(x,12) for x in item['fractional']) for item in basis})!=len(basis):
        raise ValueError('DUPLICATE_FRACTIONAL_SITE')
    mindist = min_periodic_separation(cell,[p['xyz_angstrom'] for p in atoms])
    if mindist<.35:
        raise ValueError('CLOSE_PERIODIC_NUCLEI')
    spec = {
        'version':'QW-WORLDSPEC-0.1',
        'object_id':identifier,
        'epistemic_mode':'GROUNDED',
        'matter':{'type':'periodic_cell', 'periodic':True, 'atoms':atoms,
                  'charge':0,'spin_2S':0,'cell_angstrom':cell,
                  'source':'QW-PERIODIC02 AI-authored prototype; geometry is a proposal'},
        'physics':{'engine':'pyscf-pbc','method':'RKS','basis':'cc-pvdz','xc':'PBE',
                   'observables':['energy']},
        'experiment':{'action':'single_point'}
    }
    return {'spec':spec,'sha256':digest(spec),'preflight_nearest_distance_A':mindist,
            'electron_count':ne,'geometry_screening':'LOCAL_FINITE_IMAGE_ONLY_ASE_NOT_RUN'}
