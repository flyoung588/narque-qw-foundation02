"""Expose new controls to inherited real-model Explorer. No automatic model calls."""
import json
from router import digest
from live_fabric01.runtime import FabricExplorer
from world01.session import filehash
from .model import DOMAIN,SCHEMA,system,QUALIFICATION
class CoupledExplorer(FabricExplorer):
 def _observe(self,ident):
  if self.world.store.load(ident)['payload'].get('schema')!=SCHEMA:return super()._observe(ident)
  from live_fabric01.fabric import require
  require(len(self.j.query('ReadReserved'))<self.j.events()[0]['data']['reads_max'],'READ_BUDGET_EXHAUSTED');self.j.append('ReadReserved',{'state':ident,'science_jobs':0});o=self.world.observe(ident);self._record(o,o['source_execution']['source_execution_kind']);return o
 def context(self):
  c=super().context();c['connected_workers'][DOMAIN]='core03_live.worker.execute via inherited LiveFabric';c['core03_controls']=system().allowed();c['core03_qualification']=QUALIFICATION
  c['core03_state_semantics']={'shape':[2,255],'measure':'sum channels |chi|^2 dR','pulse_clock':'absolute physical time; new pulse starts at returned state time','energy':'Driven energy includes recorded input work','conversion_to_effective_2ket':'FORBIDDEN','old_hydrogen_geometry_authority':'UNCHANGED'}
  g={}
  if self.execution.grant_path and filehash(self.execution.grant_path)==self.execution.grant_sha256:g=json.loads(self.execution.grant_path.read_text())
  if g.get('release')=='QW-LIVE-CORE03-01' and g.get('status')=='HUMAN_GRANTED' and g.get('decision_mode')=='REAL_GATEWAY_MODEL':c['resources']['new_science_jobs']=max(0,g['max_new_jobs']-len(self.execution.j.query('ExecutionReserved')))
  c['rules']+=["A field plan is not work-free; report energy and work together.","Do not reinterpret chi[2,N] as a two-dimensional electronic ket."]
  return c
