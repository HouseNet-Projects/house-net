"""Validated durable work graph contract; persistence remains the canonical Store."""
import datetime, hashlib
TYPES=('GOAL','STRATEGY','ROADMAP','INITIATIVE','ACTION_PLAN','TASK','CHECKPOINT','EVIDENCE','VERIFIED_COMPLETION')
STATUSES=('PROPOSED','APPROVED','PLANNED','READY','IN_PROGRESS','BLOCKED','COMPLETED','VERIFIED')
def _id(kind,title): return f'{kind}-{hashlib.sha256((kind+"|"+title).encode()).hexdigest()[:12]}'
def create_node(kind,title,*,owner='UNKNOWN',status='PROPOSED',parent_id=None,source=None,brains=None,approval='NOT_REQUIRED',evidence=None):
 if kind not in TYPES: raise ValueError('invalid work object type')
 if not str(title).strip() or not str(owner).strip(): raise ValueError('title and accountable owner are required')
 if status not in STATUSES: raise ValueError('invalid work status')
 if approval not in ('NOT_REQUIRED','PENDING','APPROVED','REJECTED'): raise ValueError('invalid approval state')
 return {'id':_id(kind,title),'type':kind,'title':title,'owner':owner,'status':status,'parent_id':parent_id,'source':source,'brains':list(brains or []),'approval':approval,'evidence':evidence,'created_at':datetime.date.today().isoformat()}
def validate_graph(nodes):
 ids=set(); errors=[]
 for n in nodes:
  if n.get('id') in ids: errors.append('duplicate work object id')
  ids.add(n.get('id'))
  if n.get('type') not in TYPES: errors.append('invalid work object type')
  if not n.get('owner') or n.get('owner')=='UNKNOWN': errors.append(f'owner required: {n.get("id")}')
  if n.get('parent_id') and n['parent_id'] not in ids: errors.append(f'parent missing: {n.get("id")}')
  if n.get('status') in ('COMPLETED','VERIFIED') and not n.get('evidence'): errors.append(f'completion evidence required: {n.get("id")}')
  if n.get('type')=='TASK' and n.get('approval')=='APPROVED' and n.get('status')=='COMPLETED' and not n.get('evidence'): errors.append('approved task cannot complete without evidence')
 return errors
