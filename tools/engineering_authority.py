#!/usr/bin/env python3
"""Fail-closed EngineeringAuthorityEnvelope verifier; never grants business authority."""
import fnmatch,pathlib,json
from datetime import datetime, timezone
FORBIDDEN={'visibility_change','branch_protection_change','force_push','history_rewrite','credential_admin','permission_escalation','owner_change','policy_downgrade','action_runtime_bypass','external_write','repository_delete','archive_change','release_destructive'}
def validate(e,operation,path=''):
 if not isinstance(e,dict) or e.get('status')!='ACTIVE' or e.get('consumed'): return False,'ENVELOPE_INACTIVE'
 if e.get('approved_by')!='GEV' or e.get('repository')!='HouseNet-Projects/house-net': return False,'OWNER_OR_REPOSITORY_MISMATCH'
 if operation in FORBIDDEN or operation not in e.get('allowed_operations',[]): return False,'OPERATION_NOT_AUTHORIZED'
 try:
  expires=datetime.fromisoformat(e['expires_at'].replace('Z','+00:00'))
  if expires.tzinfo is None: expires=expires.replace(tzinfo=timezone.utc)
  if expires <= datetime.now(timezone.utc): return False,'ENVELOPE_EXPIRED'
 except (KeyError,ValueError): return False,'INVALID_EXPIRATION'
 if path and not any(fnmatch.fnmatch(path,p) or path.startswith(p.rstrip('/')+'/') for p in e.get('allowed_paths',[])): return False,'PATH_OUT_OF_SCOPE'
 return True,'AUTHORIZED'
def load(path): return json.loads(pathlib.Path(path).read_text())
