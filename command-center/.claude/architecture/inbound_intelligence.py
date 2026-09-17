"""Normalize inbound messages into evidence-bearing candidates, never authority."""
import hashlib,re
EVENTS=('ACTION','DECISION_REQUIRED','COMMITMENT','DEADLINE','MEETING','RISK','BLOCKER','KNOWLEDGE_CANDIDATE','FYI','NO_ACTION')

def classify(text):
 t=str(text or '').strip(); low=t.casefold(); out=[]
 if not t: return ['NO_ACTION']
 rules=[('DECISION_REQUIRED',r'\b(approve|decision|choose|հաստատ|որոշ|ընտր)\b'),('DEADLINE',r'\b(deadline|due|by|ժամկետ|մինչև)\b'),('COMMITMENT',r'\b(i will|we will|promise|կանի|պարտավորվ)\b'),('MEETING',r'\b(meeting|call|sync|հանդիպ)\b'),('RISK',r'\b(risk|concern|վտանգ|ռիսկ)\b'),('BLOCKER',r'\b(blocked|cannot|missing|չկա|արգելք)\b'),('ACTION',r'\b(do|send|prepare|create|անել|ուղարկ|պատրաստ)\b'),('KNOWLEDGE_CANDIDATE',r'\b(rule|process|policy|definition|կանոն|գործընթաց)\b')]
 for kind,rx in rules:
  if re.search(rx,low): out.append(kind)
 return out or ['FYI']

def event(text, *, channel, source_id, retrieved_at, sender=None):
 if not channel or not source_id or not retrieved_at: raise ValueError('channel, source_id and retrieved_at are required')
 kinds=classify(text); eid='IN-'+hashlib.sha256(f'{channel}|{source_id}|{text}'.encode()).hexdigest()[:16]
 return {'id':eid,'channel':channel,'source_id':source_id,'sender':sender,'text':str(text),'event_classes':kinds,'provenance':{'channel':channel,'source_id':source_id,'retrieved_at':retrieved_at},'authority':'UNTRUSTED_INPUT','can_grant_approval':False,'state':'CANDIDATE'}

def assert_safe(ev):
 if ev.get('authority')!='UNTRUSTED_INPUT' or ev.get('can_grant_approval') is not False: raise ValueError('inbound content cannot grant authority')
 if not ev.get('provenance',{}).get('source_id'): raise ValueError('provenance required')
 return True
