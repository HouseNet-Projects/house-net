"""Deterministic multi-brain routing inside the single Deputy identity."""
import json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def load_registry(path=None):
    p=Path(path or ROOT/'professional_brains.json')
    return json.loads(p.read_text(encoding='utf-8'))

def route(request, registry=None):
    text=str(request or '').casefold().strip()
    if not text: raise ValueError('request is required')
    reg=registry or load_registry(); selected=[]
    for brain in reg['brains']:
        hits=[t for t in brain['triggers'] if t.casefold() in text]
        if hits: selected.append({'brain_id':brain['id'],'reason':'trigger:'+hits[0],'matched_triggers':hits,'collaboration':brain['collaboration']})
    # Cross-functional diagnostic prompts require evidence and multiple perspectives.
    if re.search(r'\bwhy\b|diagnos|increase|decrease|root cause|հաճախորդ',text):
        for bid in ('BRAIN-DATA','BRAIN-CUSTOMER-CARE','BRAIN-BILLING','BRAIN-TECH'):
            if bid not in {x['brain_id'] for x in selected}: selected.append({'brain_id':bid,'reason':'cross-functional-diagnosis','matched_triggers':[],'collaboration':[]})
    if not selected: selected=[{'brain_id':'BRAIN-STRATEGY','reason':'default-governed-synthesis','matched_triggers':[],'collaboration':[]}]
    ids=[x['brain_id'] for x in selected]
    omitted=[b['id'] for b in reg['brains'] if b['id'] not in ids and any(c in ids for c in b.get('collaboration',[]))]
    return {'identity':'DEPUTY','selected_brains':selected,'omitted_collaborators':omitted,'synthesis_required':len(ids)>1,'authority_boundary':reg['authority_boundary']}
