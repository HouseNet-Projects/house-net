# -*- coding: utf-8 -*-
"""SENSITIVE OVERLAY — EVIDENCE PAYLOADS (CONFIDENTIAL, local only): subscriber-derived aggregates, verbatim chat quotes and
source payload notes that the core must not carry. Core cites source ids; the payload lives here."""
OVERLAY_DATA = True

EVIDENCE = [
 {"id": "EV-01", "src": ["S05"], "kind": "subscriber_derived_aggregate", "payload": {"scored_on": "2026-09-09", "rows": 30, "bands": {"SEVERE": 9, "HIGH": 21}, "areas": {"Էջմիածին": 17, "Արմավիր": 12, "Նորապատ": 1}, "agreement": {"MONTHLY": 29, "POSTPAID_CORPORATE": 1}, "fees_amd": {"7000": 17, "6000": 11, "5500": 2}, "top_drivers": ["No yearly agreement", "Outages in the area (8–9)", "Irregular payment rhythm", "Days since the last payment"], "criteria": "score ≥70, hot signals ≥3, coverage ≥60%, limit 50", "note": "rank, not probability — uncalibrated"}},
 {"id": "EV-02", "src": ["S07"], "kind": "chat_quote", "payload": {"who": "@P1", "when": "2026-09-07 16:14–16:15", "text": "մեր հանդիպման ժամանակ 4 բան էի ուզել, որից մեկը բիզնեսի համար կրիտիկական էր … ստացել եմ մենակ staff-ի կտորը, 11 օրվա մեջ", "meaning": "trust/credibility pressure on delivery"}},
 {"id": "EV-03", "src": ["S07"], "kind": "chat_quote", "payload": {"who": "@P1", "when": "2026-09-07 17:16–17:17", "text": "արի ժամկետ դնենք ամեն ինչի վրա, շատ կարճ ժամկետներ … 5 շաբթի ինձ ներկայացրեք /ոչ թե գեներացրեք/ կոնկրետ սաղ ուղղություններով ստրատեգիա", "meaning": "strategy demanded for Thursday with short deadlines"}},
 {"id": "EV-04", "src": ["S07"], "kind": "chat_quote", "payload": {"who": "@P1", "when": "2026-09-07 17:58", "text": "ակտիվների քանակը իջնում ա խոսքի 300-ով, հետո հելնում … կարա՞ իրոք տենց դադար լինի ժամանակավոր", "meaning": "the ±300 active-subscriber anomaly (U01 candidate)"}},
 {"id": "EV-05", "src": ["S08"], "kind": "chat_quote", "payload": {"who": "@P1", "when": "2026-09-09 12:36", "text": "churnը կանգնացնելու համար մենք ինչ որ retentionի flow ունենք, որը @P6-ի վրա էր փակվում. դա էլ @P3-ի վրա փակի ու էս դոքում արտացոլի", "meaning": "retention flow ownership moved from @P6 to @P3 (C02)"}},
 {"id": "EV-06", "src": ["S08"], "kind": "chat_quote", "payload": {"who": "Gev", "when": "2026-09-09 12:41–12:44", "text": "դրա զանգերը պետքա տելեի վրա գնա մինչև ռիթենշն մասնագետ ունենանք, ու ոչ թե զադաչա, այլ ամենօրյա գործ … տելեի ավագի ու @P5-ի միջոցով, սիստեմ անպայման", "meaning": "Gev's operating position on retention calls and tracking (C02/C03)"}},
 {"id": "EV-07", "src": ["S07"], "kind": "chat_quote", "payload": {"who": "@P1", "when": "2026-09-07 17:14", "text": "պինգ պոնգը էն ա որ ինձ ասում ես որ @P2-ն մեկա չի կարանալու, հետո իրան բան ես հանձնարարում, ու 10 օր հետո պարզվում ա որ չի կարա", "meaning": "capability warning about @P2 for technical specs"}},
 {"id": "EV-08", "src": ["S08"], "kind": "chat_quote", "payload": {"who": "@P1", "when": "2026-09-09 12:38", "text": "@P2-ի պահով հաշվի առ որ եքա լոադ ենք ազատելու", "meaning": "@P2 overload — reconciliation move"}},
 {"id": "EV-09", "src": ["S07"], "kind": "chat_quote", "payload": {"who": "@P1", "when": "2026-09-07 17:16", "text": "սա հաստատված ա … ստեղ վաճառքն ա ամենաշատ օpexը, դրա հետ ես օկ եմ", "meaning": "staffing plan approved; sales is the largest opex"}},
 {"id": "EV-10", "src": ["S07"], "kind": "chat_quote", "payload": {"who": "@P1", "when": "2026-09-08 22:03", "text": "մի հատ վաղը հասկացի ինչի՞ մեր տեսուչները ծրագրով չեն օգտվում … միանգամից կարաս ասես որ վաղվանից փակում ես դոստուպը սաղի", "meaning": "inspectors not using the billing system; access to be closed"}},
]

# source payload notes that identify people or carry confidential content (core sources.json keeps only ids/paths/authority)
SOURCE_PAYLOADS = {
 "S01": {"approval_evidence": "@P1 2026-09-07 17:16 «սա հաստատված ա»", "contains": "salaries per role, payroll scenarios, bonus fund"},
 "S02": {"owner_note": "sent 09-05 as final, each head to OK their part (due 09-11)", "contains": "29 JD cards"},
 "S03": {"author": "Gev (+@P3 expected)", "contains": "cost/investment/payback figures (CV-01…CV-11)"},
 "S04": {"sent_by": "@P1 2026-09-07 17:21", "author_of_initial_proposals": "@P2", "contains": "roadmap"},
 "S05": {"producer": "@P1 2026-09-09 13:07", "contains": "30 subscriber rows with names, logins, phones, balances — PII (RESTRICTED); never extracted beyond EV-01 aggregates"},
 "S06": {"producer": "@P1's team", "contains": "12 churn signals with weights (image)"},
 "S07": {"participants": "@P1 ↔ Gev", "contains": "raw WhatsApp export; voice messages missing"},
 "S08": {"participants": "@P1 ↔ Gev", "contains": "raw WhatsApp export"},
 "S09": {"owners_column": "@P2, @P5, @P1, team, Gev", "contains": "15 live tasks with people"},
 "S10": {"contains": "25 open questions naming @P1…@P8"},
 "S11": {"contains": "delivery schedule naming @P2, all heads"},
 "S12": {"contains": "44 verbatim asks of @P1 (historical)"},
}
