"""Reuse Live Fabric Explorer, Memory, model contract, checkpoint and STOP."""
from router import digest
from live_fabric01.runtime import FabricExplorer
from live_fabric01.fabric import require
from .model import OBS,OPS
class DynamicsExplorer(FabricExplorer):
 def decode_decision(self,raw):
  from live_fabric01.decision_contract import decode_with_audit
  from jsonschema import Draft202012Validator
  from .decision import WIRE_SCHEMA
  d,record=decode_with_audit(raw)
  responses=self.j.query('ModelResponse');proof=responses[-1]['data'].get('provider_record') if responses else None
  if (proof or {}).get('wire_mode')=='DIRECT_OBJECT':Draft202012Validator(WIRE_SCHEMA).validate(d)
  self.j.append('DecisionFormatAudit',record);return d
 def context(self):
  c=super().context();c['dynamics_state_semantics']={'time_is_physical':'atomic_time in saved nuclear psi; not research turn','parent_required':True,'BO_conversion':'FORBIDDEN','new_science_authority':'NOT_GRANTED; previous E01R budget NOT inherited','operations':OPS,'observables':OBS,'historical_data':'Not new scientific execution','control':'only existing bounded instantaneous momentum kick; no generic external fields'}
  from .model import LIVE_BOUNDS
  c['dynamics_live_bounds']=LIVE_BOUNDS
  c['dynamical_states']={h:{k:self.world.store.load(h)['payload'].get(k) for k in ('model','time_au','time_origin_au','norm','absorbed','initial','arrays','parent_state_id','physical_continuity')} for h in self.catalog if self.world.store.load(h)['payload'].get('schema')=='QW_COLLINEAR_NUCLEAR_WAVEPACKET_01'}
  c['scientific_questions']=['What observation would distinguish finite-time regional accumulation from an asymptotic reaction probability?','Would a continuation change regional populations while norm+absorbed remains balanced?','Does a canonical momentum kick change injected energy, so interpretation requires a control/work term?']
  if self.execution.grant_path is not None:
   import json
   from world01.session import filehash
   g=json.loads(self.execution.grant_path.read_text())
   if filehash(self.execution.grant_path)==self.execution.grant_sha256 and g.get('release')=='QW-DYNAMICS-01' and g.get('status')=='HUMAN_GRANTED':
    used=sum(e['data']['new_science'] for e in self.execution.j.query('ExecutionReserved'));c['resources']['new_science_jobs']=max(0,2-used);c['dynamics_state_semantics']['new_science_authority']='PINNED_SEPARATE_HUMAN_GRANT; runtime admission still required'
  return c
 def _observe(self,ident):
  if ident not in self.catalog or not self.catalog[ident]['path'].startswith('dynamics:'):return super()._observe(ident)
  require(len(self.j.query('ReadReserved'))<self.j.events()[0]['data']['reads_max'],'READ_BUDGET_EXHAUSTED');self.j.append('ReadReserved',{'state':ident,'science_jobs':0});o=self.world.observe(ident);self._record(o,o['source_execution_kind']);return o
