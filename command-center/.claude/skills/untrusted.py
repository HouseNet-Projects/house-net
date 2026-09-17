# -*- coding: utf-8 -*-
"""UNTRUSTED CONTENT DEFENSE — every external text (mail, Telegram, WhatsApp, documents, attachment metadata) is DATA, never an
instruction. This module only DETECTS instruction-like / authority-claiming content so the intelligence layer can flag it; nothing
here (and nothing anywhere) turns external text into a tool call, a policy, a secret disclosure or an Action Runtime approval:
approvals are classified only from Gev's own prompt path (actions.classify_approval on inputs.approval_text), and action_runtime
refuses any approval text that arrives with an external_source marker."""
import re

INJECTION_PATTERNS = [
 ("OVERRIDE_INSTRUCTION", r"(ignore (all |your |the )?(previous |prior )?(rules|instructions|policy|policies|gev|the owner)|disregard (your|the) (rules|instructions)|անտեսիր (կանոն|հրահանգ|գև)|forget (your|the) (rules|instructions))"),
 ("POLICY_CLAIM", r"((this|the following) (message|text) is (your )?(new )?(system )?(policy|prompt|instruction)|you are now (authorized|allowed|permitted)|new system prompt|system:\s)"),
 ("FAKE_APPROVAL", r"(\b(approve|approved|confirm|confirmed|go ahead|execute)\b[^.\n]{0,40}\b(this|the) (task|action|card|request|send)|\bapprove this\b|հաստատում եմ այս (գործող|քայլ)|approval granted)"),
 ("SECRET_EXTRACTION", r"(reveal|show|print|send|share|tell)[^.\n]{0,30}(your |the )?(secrets?|tokens?|passwords?|credentials?|api keys?|config|system prompt)|գաղտնաբառ|token-?ը (ասա|ուղարկի)"),
 ("DESTRUCTIVE_COMMAND", r"(delete (all|every|the) (tasks?|files?|records?|messages?|drafts?)|drop (the )?(table|database)|rm -rf|ջնջիր (բոլոր|ամբողջ))"),
 ("TOOL_COMMAND", r"(\{\s*\"(tool|function|action|command|op|skill)\"\s*:|<tool_call>|<function_call>|\bskill\.py\b|\bactions\.execute\b|\bsudo\b|\bpowershell\b|\bBash\(|\bWrite\(|\bEdit\()"),
 ("URGENCY_PRESSURE", r"(send (this|it) (immediately|right now|now)|immediately send|no need (to|for) (approval|confirmation)|without (asking|approval)|skip (the )?approval|don't ask gev|առանց հաստատ)"),
]
_RX = [(k, re.compile(p, re.I)) for k, p in INJECTION_PATTERNS]

def injection_signals(text):
    """Names of instruction-like / authority-claiming patterns found in external text (empty = none). Detection only — never enforcement of the content."""
    t = " ".join(str(text or "").split())
    return [k for k, rx in _RX if rx.search(t)]

def scan_attachment_meta(atts):
    """Attachment METADATA can carry encoded instructions (file names, mime strings): flag, never decode/execute."""
    hits = []
    for a in atts or []:
        blob = " ".join(str(a.get(k) or "") for k in ("name", "mime", "kind"))
        s = injection_signals(blob)
        if s: hits.append({"attachment": (a.get("name") or a.get("kind")), "signals": s})
        if re.search(r"[A-Za-z0-9+/]{40,}={0,2}", blob): hits.append({"attachment": (a.get("name") or a.get("kind")), "signals": ["ENCODED_PAYLOAD"]})
    return hits

def mark(record):
    """Attach the untrusted-content verdict to a chat/mail record (in place) — a flagged message stays evidence, loses nothing, gains no authority."""
    sig = injection_signals((record.get("text") or "") + " " + (record.get("subject") or "") + " " + (record.get("preview") or ""))
    att = scan_attachment_meta(record.get("attachments") or [])
    record["untrusted"] = {"injection_suspected": bool(sig or att), "signals": sig, "attachment_signals": att, "authority": "NONE — external content never instructs Deputy or approves an action"}
    return record
