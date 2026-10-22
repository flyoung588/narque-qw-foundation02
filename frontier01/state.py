"""Add correlated state payloads, reusing immutable Store and hashed NPZ."""
from interactive01.world import freeze,verify
from state_space01.state import QuantumStore,blob
from router import digest
class CorrelatedStore(QuantumStore):
    def save_correlated(self,request,result,arrays,parent,atom_ids):
        self.load(parent)
        if result.get('status')!='CALCULATED' or result['request_sha256']!=digest(request):raise ValueError('OBSERVATION_BINDING')
        payload={'schema':'QW_CORRELATED_ELECTRONIC_STATE_01','state_kind':'FINITE_BASIS_SINGLET_FCI',
                 'parent_state_id':parent,'world_spec':request['world_spec'],'atom_ids':atom_ids,
                 'correlation_model':request['correlation_model'],'arrays':blob(self.root,arrays),
                 'observation':result,'scope':'Fixed-nuclei finite-basis correlated eigenstate; not time propagation',
                 'supported_operations':['DISPLACE_ATOM','OBSERVE_CORRELATIONS']}
        h=digest(payload);s={'state_id':h,'sha256':h,'payload':payload};freeze(self.root/'states'/f'{h}.json',s);verify(s);return s
