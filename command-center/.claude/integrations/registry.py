# -*- coding: utf-8 -*-
"""INTEGRATION REGISTRY — every external/live source Deputy may READ, declared before it is trusted.
A connected system is an UNTRUSTED data source until certified (certify_integrations.py): DECLARED → CONFIGURED → CONNECTED →
VERIFIED_READ → RELIABLE_READ. Authority is CONFIGURED here (FACT_AUTHORITY), never assumed: "live" does not mean "correct".
Mission 4: write_ops is empty for every integration by construction; adapters expose fixed read operations only."""
import pathlib
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent

REQUIRED_FIELDS = ("integration_id", "system", "purpose", "auth", "data_accessible", "classification", "authority", "freshness", "owner_role",
                   "read_ops", "write_ops", "required_certification_ops", "availability", "failure_behavior", "adapter", "critical", "expected_identity", "unblock", "machine_dependency")

# Integrity pin of the fixed read-only Outlook reader (sha256 of outlook_read.ps1). The adapter refuses a modified reader.
OUTLOOK_READER_SHA256 = "8e599a14b7877dc5365587053112e1f7e3318e79c3d6b14ff9397507b5d1246c"

# persist=False → CONFIDENTIAL payloads (mail previews, calendar descriptions) live only in process memory with a ttl; never written to disk (audit finding 1)
_NO_FRESHNESS_RULE = {"max_age_seconds": None, "cache_ttl_seconds": 300, "persist": False, "rule": "UNDEFINED — the Business Operating Model defines no acceptable age for this data; freshness is reported (retrieved_at, LIVE/CACHED/STALE), never judged"}

INTEGRATIONS = {
 "INT-TASKS": {
  "integration_id": "INT-TASKS", "system": "Command-center task register (Tasks.xlsx)", "purpose": "Canonical open/overdue/due-today/waiting/blocked tasks with owner, deadline, status, comment (completion evidence).",
  "auth": {"mechanism": "local workspace file access", "secrets": []}, "data_accessible": ["tasks (id, title, status, owner, due, comment)"], "classification": "CONFIDENTIAL",
  "authority": {"rank": 4, "name": "ACTIVE_REGISTER", "business_source": "S09", "note": "Tasks.xlsx remains canonical for task status unless the Business Model says otherwise"},
  "freshness": {"max_age_seconds": 14 * 24 * 3600, "cache_ttl_seconds": 30, "persist": True, "rule": "skill registry source_policy: tracker older than 14 days → STALE_SOURCE (acknowledged, not silent); persisted cache expires hard after 30s"},
  "owner_role": "Վաճառքի և գործառնական ղեկավար (Gev) — hand-edited register", "read_ops": {"tasks.list": {"kind": "task", "params": ["open_only", "status", "owner"]}}, "write_ops": [], "required_certification_ops": ["tasks.list"],
  "availability": "whenever the workspace is mounted", "failure_behavior": "file missing → UNAVAILABLE; header drift → SCHEMA_CHANGED (fail closed, no partial parse)",
  "adapter": "adapter_tasks", "critical": True, "expected_identity": {"path": "Tasks.xlsx", "sheet": "ԱՌԱՋԱԴՐԱՆՔՆԵՐ"}, "unblock": None, "machine_dependency": None},
 "INT-OL-CAL": {
  "integration_id": "INT-OL-CAL", "system": "Outlook desktop calendar (MAPI, signed-in Windows profile)", "purpose": "Today's and upcoming meetings: time, title, participants, location, description preview, online link — for the Daily Brief, meeting preparation, deadline awareness and schedule conflicts.",
  "auth": {"mechanism": "Outlook desktop session of the signed-in Windows user, read through the fixed PowerShell reader outlook_read.ps1 (integrity-pinned); no token, no password handled by Deputy", "secrets": []},
  "data_accessible": ["calendar items of the default calendar (all stores enumerated by probe)"], "classification": "CONFIDENTIAL",
  "authority": {"rank": 4, "name": "LIVE_SYSTEM", "business_source": None, "note": "authoritative for meeting time/participants ONLY as configured in FACT_AUTHORITY"},
  "freshness": dict(_NO_FRESHNESS_RULE), "owner_role": "Gev (mailbox owner)", "read_ops": {"calendar.events": {"kind": "meeting", "params": ["from", "to", "limit"]}}, "write_ops": [], "required_certification_ops": ["calendar.events"],
  "availability": "only while classic Outlook is running on this PC in the same Windows session", "failure_behavior": "Outlook not reachable → UNAVAILABLE (last successful read reported); reader modified → READ_ONLY_VIOLATION; wrong mailbox → WRONG_TENANT; pwsh missing → TOOL_UNAVAILABLE",
  "adapter": "adapter_outlook", "critical": True, "expected_identity": {"mailbox_domain": "housenet.am"}, "unblock": "classic Outlook running and signed in as the owner on this PC (New Outlook has no MAPI/COM surface)",
  "machine_dependency": "classic Outlook desktop session signed in as the owner (Windows, same user session, pwsh)"},
 "INT-OL-MAIL": {
  "integration_id": "INT-OL-MAIL", "system": "Outlook desktop mailbox (MAPI, signed-in Windows profile)", "purpose": "Read/search permitted mail (Inbox, Sent): unanswered requests, commitments, waiting-for, decisions requested, follow-ups, escalations, meeting context — extracted as CANDIDATE_OPEN_LOOP, never as permanent truth.",
  "auth": {"mechanism": "same Outlook session as INT-OL-CAL via outlook_read.ps1 (read-only; never marks read, moves, deletes or sends)", "secrets": []},
  "data_accessible": ["message headers + short body preview (≤600 chars); no attachments; folders Inbox/Sent"], "classification": "CONFIDENTIAL",
  "authority": {"rank": 2, "name": "EVIDENCE", "business_source": None, "note": "mail is evidence of a request/promise — below the task register and below live systems of record"},
  "freshness": dict(_NO_FRESHNESS_RULE), "owner_role": "Gev (mailbox owner)", "read_ops": {"mail.list": {"kind": "message", "params": ["folder", "since", "limit", "unread_only"]}, "mail.search": {"kind": "message", "params": ["query", "since", "limit", "folder"]}}, "write_ops": [], "required_certification_ops": ["mail.list", "mail.search"],
  "availability": "as INT-OL-CAL", "failure_behavior": "as INT-OL-CAL; body previews are never persisted outside the short-lived cache in .claude/state",
  "adapter": "adapter_outlook", "critical": False, "expected_identity": {"mailbox_domain": "housenet.am"}, "unblock": "as INT-OL-CAL",
  "machine_dependency": "classic Outlook desktop session signed in as the owner (Windows, same user session, pwsh)"},
 "INT-B24": {
  "integration_id": "INT-B24", "system": "Bitrix24 CRM (REST)", "purpose": "Leads, deals, stages, owners, CRM tasks and activities — the system where the real sales pipeline and operational tasks live (SYS-B24).",
  "auth": {"mechanism": "inbound webhook (per-user REST code) or OAuth app token with READ scopes (crm, task, user); GET-only client with a fixed method allowlist", "secrets": ["webhook_url"]},
  "data_accessible": ["crm.deal.list/fields", "crm.lead.list", "crm.status.list (stages)", "crm.activity.list", "tasks.task.list", "user.get", "profile"], "classification": "CONFIDENTIAL",
  "authority": {"rank": 4, "name": "LIVE_SYSTEM_OF_RECORD", "business_source": "SYS-B24 (S03/S04/S07/S14)", "note": "system of record for deal stage and CRM tasks; NOT for activations/billing status (MikroBill)"},
  "freshness": dict(_NO_FRESHNESS_RULE), "owner_role": "UNKNOWN (Bitrix24 admin — Business Model: SYS-B24 owner UNKNOWN)",
  "read_ops": {"crm.deals": {"kind": "deal", "params": ["filter", "select", "limit"]}, "crm.leads": {"kind": "lead", "params": ["filter", "select", "limit"]}, "crm.stages": {"kind": "stage", "params": ["entity_id"]}, "crm.activities": {"kind": "activity", "params": ["filter", "limit"]},
               "tasks.list": {"kind": "b24task", "params": ["filter", "limit"]}, "users": {"kind": "user", "params": ["filter"]}, "identity": {"kind": "identity", "params": []}}, "write_ops": [],
  "required_certification_ops": ["identity", "crm.deals", "crm.stages", "tasks.list"],
  "availability": "portal reachable over HTTPS with a valid read-scoped token", "failure_behavior": "no token → NOT_CONFIGURED; expired/invalid token → AUTH_FAILED; insufficient scope → PERMISSION_DENIED; QUERY_LIMIT_EXCEEDED → RATE_LIMITED (DEGRADED); 5xx/network → UNAVAILABLE; non-JSON → MALFORMED_RESPONSE; missing 'result' → SCHEMA_CHANGED; paged 'next' → partial=True; portal host ≠ configured → WRONG_TENANT",
  "adapter": "adapter_bitrix24", "critical": False, "expected_identity": {"portal_domain": "housenet.bitrix24.ru", "note": "expected tenant (Gev, 2026-09-12); live identity is verified from the provider after configuration, never assumed"},
  "unblock": "Gev (or the Bitrix24 admin) creates an INBOUND WEBHOOK with read permissions only (CRM, Tasks, Users) and stores it OUTSIDE Git: ~/.command-center/integrations/INT-B24.json {\"webhook_url\": \"https://<portal>.bitrix24.<tld>/rest/<user>/<code>/\", \"portal_domain\": \"<portal>.bitrix24.<tld>\"}; then python .claude/integrations/integration.py certify",
  "machine_dependency": None},
 "INT-MB": {
  "integration_id": "INT-MB", "system": "MikroBill billing", "purpose": "Subscriber/customer counts, activations, disconnects, tariffs, statuses, balances/revenue, service state, churn indicators — the source of truth for billing (S11).",
  "auth": {"mechanism": "UNKNOWN — no API/DB interface inventoried yet (Open-questions #7, U04)", "secrets": ["dsn_or_api_url", "token_or_password"]}, "data_accessible": ["UNKNOWN until the interface is inventoried"], "classification": "CONFIDENTIAL",
  "authority": {"rank": 5, "name": "SOURCE_OF_TRUTH_BILLING", "business_source": "SYS-MB (S04/S07/S11)", "note": "Gev's position 2026-09-09: MikroBill = source of truth for billing facts"},
  "freshness": dict(_NO_FRESHNESS_RULE), "owner_role": "Բիլինգի և եկամտի ղեկավար (4.1) — person DERIVED @P2", "read_ops": {}, "write_ops": [], "required_certification_ops": [],
  "availability": "UNKNOWN", "failure_behavior": "every query → NOT_CONFIGURED with the exact requirement; no field is mapped until verified",
  "adapter": "adapter_mikrobill", "critical": False, "expected_identity": None, "machine_dependency": "UNKNOWN until the interface is inventoried",
  "deferred": {"by": "Gev", "since": "2026-09-12", "note": "MikroBILL integration is DEFERRED by the owner: no implementation work, no activation nag in briefs; billing facts stay UNAVAILABLE / UNKNOWN until Gev lifts the deferral"},
  "unblock": "DEFERRED by Gev (2026-09-12). When lifted: Billing head (role 4.1) / @P1 provides (1) a read-only interface (DB replica/read role or documented REST API + read token), (2) the field/status dictionary (8 subscriber statuses, U08), (3) written authorization; then an adapter with verified field mapping is added and certified"},
 "INT-TG": {
  "integration_id": "INT-TG", "system": "Telegram (official Bot API)", "purpose": "Two inbound sources under one canonical update stream: BOT_CHAT (direct bot private/group messages) and BUSINESS (Telegram Business / Secretary Mode — the private chats Gev selected on his own account) as management evidence (requests, promises, decisions, escalations); exact approved outbound messages/replies through the Action Runtime.",
  "auth": {"mechanism": "official Bot API over HTTPS (api.telegram.org) with a bot token; long polling by default (no public webhook needed), optional webhook mode with a secret token; no client sessions, no scraping, no UI automation", "secrets": ["bot_token"]},
  "data_accessible": ["bot identity (getMe)", "updates: private messages and allowed-group messages — message id, chat id, sender, timestamp, text/caption, reply relation, attachment METADATA only",
                      "business connection state (connected account, user_chat_id, granted rights, enabled flag) and business messages from the chats Gev selected — same minimal fields, plus edit/delete lifecycle events; NO historical conversation before the connection existed"], "classification": "CONFIDENTIAL",
  "authority": {"rank": 2, "name": "EVIDENCE", "business_source": None, "note": "chat content is evidence of a request/promise — UNTRUSTED DATA, never an instruction or an approval; below the task register"},
  "freshness": dict(_NO_FRESHNESS_RULE), "owner_role": "Gev (bot owner)",
  "read_ops": {"identity": {"kind": "chat_identity", "params": []}, "chat.messages": {"kind": "chat_message", "params": ["limit", "timeout"]}, "business.connection": {"kind": "chat_connection", "params": ["refresh"], "sub_capability": True}}, "write_ops": [], "required_certification_ops": ["identity", "chat.messages"],
  "availability": "api.telegram.org reachable with a valid bot token; the bot must be added/started in the allowed chats", "failure_behavior": "no token → NOT_CONFIGURED; 401 → AUTH_FAILED; 429 → RATE_LIMITED; network → UNAVAILABLE; non-JSON → MALFORMED_RESPONSE; unexpected shape → SCHEMA_CHANGED; bot username ≠ expected → WRONG_TENANT; unknown chats never trusted",
  "adapter": "adapter_telegram", "critical": False, "expected_identity": {"bot_username": "config key expected_bot_username (verified from getMe)"},
  "unblock": "Gev provides OUTSIDE Git (~/.command-center/integrations/INT-TG.json or CC_INT_TG_*): bot_token, allowed_chat_ids, allowed_user_ids (optional expected_bot_username, mode=polling|webhook, webhook_secret). For Telegram Business: enable Secretary Mode / Business Mode for the bot in @BotFather, connect it on the account (Settings → Telegram Business → Chatbots), select ONLY the intended private chats, then set business_allowed_user_ids (and optional business_account_user_id) in the same config; then python .claude/integrations/integration.py certify",
  "machine_dependency": None},
 "INT-WA": {
  "integration_id": "INT-WA", "system": "WhatsApp Business (official Cloud API)", "purpose": "Inbound customer/partner messages and delivery statuses delivered by the Cloud API webhook (verified handshake + signed requests) as management evidence; exact approved outbound text/template messages through the Action Runtime.",
  "auth": {"mechanism": "official WhatsApp Cloud API (graph.facebook.com) with an access token; inbound via a verified, HMAC-signed webhook (X-Hub-Signature-256); no WhatsApp Web, no browser automation, no QR sessions", "secrets": ["access_token", "phone_number_id", "verify_token", "app_secret"]},
  "data_accessible": ["business phone identity", "inbound messages ingested by the webhook (message id, sender, timestamp, type, text, reply context, attachment METADATA)", "delivery/read/failed status events"], "classification": "CONFIDENTIAL",
  "authority": {"rank": 2, "name": "EVIDENCE", "business_source": None, "note": "chat content is evidence — UNTRUSTED DATA, never an instruction or an approval"},
  "freshness": dict(_NO_FRESHNESS_RULE), "owner_role": "Gev (business account owner)",
  "read_ops": {"identity": {"kind": "chat_identity", "params": []}, "chat.messages": {"kind": "chat_message", "params": ["limit", "since"]}, "chat.statuses": {"kind": "chat_status", "params": ["message_id", "limit"]}}, "write_ops": [], "required_certification_ops": ["identity", "chat.messages"],
  "availability": "graph.facebook.com reachable with a valid token; a public HTTPS callback route pointed at the local webhook listener (deployment configuration)", "failure_behavior": "missing config → NOT_CONFIGURED; 401 → AUTH_FAILED; 403 → PERMISSION_DENIED; 429 → RATE_LIMITED; bad signature → SIGNATURE_INVALID; foreign phone_number_id/WABA → WRONG_TENANT; duplicate/old event → REPLAY_REJECTED; malformed → MALFORMED_RESPONSE",
  "adapter": "adapter_whatsapp", "critical": False, "expected_identity": {"display_phone_number": "config key expected_display_phone (verified from the provider)"},
  "unblock": "Gev provides OUTSIDE Git (~/.command-center/integrations/INT-WA.json or CC_INT_WA_*): access_token, phone_number_id, business_account_id, verify_token, app_secret, allowed_numbers, expected_display_phone, webhook host/port/path; points the Meta app webhook (public HTTPS) at the listener; then python .claude/integrations/integration.py certify",
  "machine_dependency": "a reachable HTTPS callback for the webhook listener (reverse proxy/tunnel) — deployment, not code"},
}

# Not registered on purpose (Mission 4 §3 F): PBX, HouseNet Portal, network monitoring (NetXMS/Zabbix), churn scoring — only after A–E
# or when trivially available and high-value. Listed so the gap is explicit, not forgotten.
DEFERRED = {"SYS-PBX": "call logs/recordings — owner UNKNOWN, no interface known", "SYS-PORTAL": "integration bridge — @P4/@P1's team, no read access granted",
            "SYS-NET": "NetXMS/Zabbix outages — NOC specialist (2.13) → CTO, no read access granted", "SYS-CHURN": "weekly save-list — file export only (S05), already a business-model source"}

# FACT AUTHORITY — explicit precedence per fact type. Tiers are ordered lists; sources in the SAME tier that disagree → SOURCE_CONFLICT
# (never merged); a higher tier wins over a lower tier while every observation is kept. Missing fact type → AUTHORITY_UNDEFINED (no guess).
FACT_AUTHORITY = {
 "meeting_time":         {"tiers": [["INT-OL-CAL"], ["INT-TASKS"], ["INT-OL-MAIL"], ["S07", "S08"]], "src": ["S15"], "note": "live calendar > task register note > mail mention > old chat note"},
 "meeting_participants": {"tiers": [["INT-OL-CAL"], ["INT-OL-MAIL"]], "src": ["S15"]},
 # TASK AUTHORITY IS SCOPED (audit finding 3): the management register and Bitrix-native CRM tasks are DIFFERENT record scopes.
 # Tasks.xlsx never outranks Bitrix for a Bitrix-native task and Bitrix never outranks the register for a register task; a link
 # between the two keeps both statuses side by side (reconcile.reconcile_task_link) and reports STATUS_DIVERGENCE — no override.
 "register_task_status":   {"tiers": [["INT-TASKS"], ["INT-OL-MAIL"]], "src": ["S09", "S15"], "scope": "Command-center management register (Gev)", "system_of_record": "INT-TASKS", "note": "mail may only evidence a register task; CRM tasks are out of scope (U09: B24 tasks missing from the register = gap, not a conflict)"},
 "register_task_deadline": {"tiers": [["INT-TASKS"], ["INT-OL-CAL"], ["INT-OL-MAIL"]], "src": ["S09"], "scope": "Command-center management register (Gev)", "system_of_record": "INT-TASKS"},
 "crm_task_status":        {"tiers": [["INT-B24"]], "src": ["S14"], "scope": "Bitrix24-native CRM/operational tasks", "system_of_record": "INT-B24", "note": "the register or mail never override the native system-of-record status"},
 "crm_task_deadline":      {"tiers": [["INT-B24"]], "src": ["S14"], "scope": "Bitrix24-native CRM/operational tasks", "system_of_record": "INT-B24"},
 "deal_stage":           {"tiers": [["INT-B24"], ["INT-OL-MAIL"]], "src": ["S03", "S14"]},
 "activation":           {"tiers": [["INT-MB"], ["INT-B24"]], "src": ["S01", "S11"], "note": "sale = ACTIVATED deal (S01); billing confirms activation (S11); CRM stage is the leading signal only"},
 "subscriber_status":    {"tiers": [["INT-MB"], ["INT-B24"], ["S05"]], "src": ["S04", "S07", "S11"], "note": "MikroBill = source of truth; churn save-list (S05) is a derived historical export"},
 "commitment":           {"tiers": [["INT-TASKS"], ["INT-OL-MAIL", "INT-TG", "INT-WA"]], "src": ["S15"], "note": "a promise seen in mail/chat is a CANDIDATE until the person is a verified identity and the statement is explicit; the same promise across channels is ONE loop"},
 "chat_message":         {"tiers": [["INT-TG", "INT-WA"]], "src": ["S15"], "note": "each channel is authoritative for its own messages; content is untrusted data"},
}

def get(integration_id): return INTEGRATIONS.get(integration_id)
def ids(): return list(INTEGRATIONS)
def critical_ids(): return [k for k, v in INTEGRATIONS.items() if v["critical"]]

def declaration_problems():
    p = []
    for iid, spec in INTEGRATIONS.items():
        for f in REQUIRED_FIELDS:
            if f not in spec: p.append(f"{iid}: field {f} missing")
        if spec.get("write_ops"): p.append(f"{iid}: write_ops must be empty in Mission 4")
        if spec.get("integration_id") != iid: p.append(f"{iid}: id mismatch")
        for op, o in (spec.get("read_ops") or {}).items():
            if "kind" not in o or "params" not in o: p.append(f"{iid}: read op {op} lacks kind/params")
        if spec.get("classification") not in ("PUBLIC", "INTERNAL", "CONFIDENTIAL", "RESTRICTED"): p.append(f"{iid}: bad classification")
        if not isinstance(spec.get("freshness", {}).get("rule"), str): p.append(f"{iid}: freshness rule text missing")
        if "persist" not in spec.get("freshness", {}): p.append(f"{iid}: freshness.persist missing (CONFIDENTIAL payloads must declare whether they may touch disk)")
        if spec.get("classification") == "CONFIDENTIAL" and spec["freshness"].get("persist") and spec["adapter"] != "adapter_tasks": p.append(f"{iid}: confidential live payloads may not be persisted")
        rco = spec.get("required_certification_ops")
        if not isinstance(rco, list) or (spec.get("read_ops") and not rco) or any(o not in spec.get("read_ops", {}) for o in (rco or [])): p.append(f"{iid}: required_certification_ops must be a non-empty subset of read_ops")
    for ft, fa in FACT_AUTHORITY.items():
        if "task" in ft and not fa.get("scope"): p.append(f"fact_authority {ft}: task facts must be scoped")
        for tier in fa["tiers"]:
            for s in tier:
                if s.startswith("INT-") and s not in INTEGRATIONS: p.append(f"fact_authority {ft}: unknown integration {s}")
    return p
