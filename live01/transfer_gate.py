"""Payload-specific external approval, not a model-generated authority flag."""
import pathlib,json,hashlib
from world01.contracts import WorldError

def check_transfer(root):
 r=pathlib.Path(root);a=json.loads((r/'MODEL_TRANSFER_APPROVAL.json').read_text())
 if a.get('status')!='HUMAN_GRANTED_MODEL_TRANSFER' or not a.get('human_approval_reference'):raise WorldError('MODEL_PAYLOAD_TRANSFER_APPROVAL_REQUIRED')
 if a.get('destination')!='Existing official ChatGPT model service' or a.get('model')!='gpt-6.1-sol' or a.get('effort')!='low' or a.get('max_calls')!=6:raise WorldError('MODEL_TRANSFER_SCOPE_MISMATCH')
 m=json.loads((r/'MODEL_PAYLOAD_MANIFEST.json').read_text())
 if a.get('manifest_sha256')!=hashlib.sha256((r/'MODEL_PAYLOAD_MANIFEST.json').read_bytes()).hexdigest():raise WorldError('MODEL_PAYLOAD_MANIFEST_UNAPPROVED')
 for name,h in m['files'].items():
  p=r/name
  if p.is_symlink() or hashlib.sha256(p.read_bytes()).hexdigest()!=h:raise WorldError('MODEL_PAYLOAD_CHANGED')
 return m
