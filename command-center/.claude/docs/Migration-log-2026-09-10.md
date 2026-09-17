# Migration log — 2026-09-10 (Daily check → Command-center contract)

| From | To | Why | Status |
|---|---|---|---|
| `Առաջադրանքներ.xlsx` | `Tasks.xlsx` | live task register (single canonical) | MOVED_EARLIER |
| `ՕՐԱԳԻՐ.md` | `Journal.md` | daily journal | MOVED_EARLIER |
| `ԱՆԵԼԻՔՆԵՐ.md` | `Actions.md` | internal to-dos | MOVED_EARLIER |
| `01_Ընթացիկ/Վաճառքի կարճաժամկետ ռազմավարություն.docx` | `01_Active/Sales/Sales-strategy-2026-09-09.docx` | docx title 'ՎԱՃԱՌՔԻ ԿԱՐՃԱԺԱՄԿԵՏ ՌԱԶՄԱՎԱՐՈՒԹՅՈՒՆ · Փուլ 1 D2D/telesales' — active sales work; date = file date | MOVED_EARLIER |
| `01_Ընթացիկ/save-list (2).xlsx` | `01_Active/Sales/Churn-save-list-2026-09-09.xlsx` | sheets Provenance + Save list: churn-risk ranked save list scored 2026-09-09; '(2)' was a download duplicate suffix | MOVED_EARLIER |
| `01_Ընթացիկ/HouseNet_Billing_Roadmap_v2_2026-09-07.docx` | `01_Active/Systems/Billing-roadmap-v2-2026-09-07.docx` | docx 'HouseNet Billing Department Տարեկան Roadmap 2026' v2 — Systems | MOVED_EARLIER |
| `01_Ընթացիկ/JD_v1.1_2026-09-05.docx` | `01_Active/People/Job-descriptions-v1.1-2026-09-05.docx` | docx 'ՀԱՍՏԻՔՆԵՐԻ ՆԿԱՐԱԳՐՈՒԹՅՈՒՆՆԵՐ' (JD in progress) — People | MOVED_EARLIER |
| `04_WhatsApp/ՀԱՐՑԵՐ_բաց.md` | `01_Active/Operations/Open-questions.md` | open questions register (active) | MOVED_EARLIER |
| `03_Ավարտված/Հաստիքացուցակ_2026-09-07.xlsx` | `02_Reference/People/Staffing-plan-2026-09-07.xlsx` | approved staffing plan, still authoritative → Reference | MOVED_EARLIER |
| `01_Ընթացիկ/Գրաֆիկ_2026-09-09.xlsx` | `03_Completed/Delivery-schedule-2026-09-09.xlsx` | generated schedule sent 2026-09-09 — finished deliverable | MOVED_EARLIER |
| `01_Ընթացիկ/Գրաֆիկ_2026-09-09_WhatsApp.txt` | `03_Completed/Delivery-schedule-whatsapp-2026-09-09.txt` | WhatsApp text of the sent schedule | MOVED_EARLIER |
| `04_WhatsApp/Բնօրինակներ/2026-09-09_@P1` | `04_Sources/Whatsapp/@P1-2026-09-09` | original WhatsApp export | MOVED_EARLIER |
| `04_WhatsApp/Բնօրինակներ/2026-09-09_@P1_ցերեկ` | `04_Sources/Whatsapp/@P1-2026-09-09-afternoon` | second export the same day (ցերեկ = afternoon) | MOVED_EARLIER |
| `01_Ընթացիկ/WhatsApp Image 2026-09-09 at 12.47.22.jpeg` | `04_Sources/Screenshots/Churn-risk-signals-2026-09-09.jpeg` | Journal: churn-risk signal list image → raw screenshot | MOVED_EARLIER |
| `02_Արխիվ/2026-09-09_սևագրեր/run.py` | `05_Archive/Drafts-2026-09-09/run.py` | legacy updater | MOVED_EARLIER |
| `02_Արխիվ/2026-09-09_սևագրեր/ԱՌԱՋԱԴՐԱՆՔՆԵՐ_8թերթ_ավտոմատ_հին.xlsx` | `05_Archive/Drafts-2026-09-09/Task-workbook-8-sheet-2026-09-09.xlsx` | old 8-sheet task workbook | MOVED_EARLIER |
| `02_Արխիվ/2026-09-09_սևագրեր/ԳԱԴՈՒԿՅԱՆԻ_ՊԱՀԱՆՋՆԵՐԸ.md` | `05_Archive/Drafts-2026-09-09/@P1-requirements-2026-09-09.md` | draft requirements | MOVED_EARLIER |
| `02_Արխիվ/2026-09-09_սևագրեր/ԳՐԱՖԻԿԻ_ՀԱՐՑԵՐ.md` | `05_Archive/Drafts-2026-09-09/Schedule-questions-2026-09-09.md` | answered schedule questions | MOVED_EARLIER |
| `02_Արխիվ/2026-09-09_սևագրեր/ԹԱՐՄԱՑՆԵԼ.bat` | `05_Archive/Drafts-2026-09-09/update.bat` | legacy one-click updater | MOVED_EARLIER |
| `02_Արխիվ/ԳԱԴՈՒԿՅԱՆԻ_ՊԱՀԱՆՋՆԵՐԸ_քո-լրացրածը_2026-09-09.xlsx` | `05_Archive/Drafts-2026-09-09/@P1-requirements-annotated-2026-09-09.xlsx` | annotated requirements workbook, superseded by Tasks.xlsx | MOVED_EARLIER |
| `02_Արխիվ/2026-09-10_skill_registry_v1/registry_132_2026-09-10.json` | `05_Archive/Skill-registry-v1-2026-09-10/registry_132_2026-09-10.json` | pre-audit registry | MOVED_EARLIER |
| `04_WhatsApp/README.md` | `05_Archive/Legacy-whatsapp-2026-09-09/Whatsapp-readme-2026-09-09.md` | superseded 8-sheet workflow description | MOVED_EARLIER |
| `04_WhatsApp/ՕԳՆԱԿԱՆ_դերը.md` | `.claude/docs/Role.md` | role card | MOVED_EARLIER |
| `04_WhatsApp/ՕԳՆԱԿԱՆ_JD.md` | `.claude/docs/Job-description.md` | 53-section charter | MOVED_EARLIER |
| `.claude/skills/registry_audit_2026-09-10.md` | `.claude/docs/Registry-audit-2026-09-10.md` | documentation | MOVED_EARLIER |
| `04_WhatsApp/գործիքներ/տվյալներ.py` | `.claude/tools/task_registry_data.py` | task/people/question data for the legacy workbook + schedule | MOVED_EARLIER |
| `04_WhatsApp/գործիքներ/կառուցել.py` | `.claude/tools/build_task_workbook.py` | builds the legacy 8-sheet workbook | MOVED_EARLIER |
| `04_WhatsApp/գործիքներ/գրաֆիկ.py` | `.claude/tools/build_delivery_schedule.py` | builds the outgoing delivery schedule | MOVED_EARLIER |
| `04_WhatsApp/գործիքներ/ոճ.py` | `.claude/tools/xlsx_style.py` | shared openpyxl styling | MOVED_EARLIER |
| `04_WhatsApp/գործիքներ/պահանջներ.py` | `.claude/tools/build_requirements_workbook.py` | builds the requirements workbook | MOVED_EARLIER |
| `04_WhatsApp/գործիքներ/պահանջներ_տվյալներ.py` | `.claude/tools/requirements_data.py` | requirements data | MOVED_EARLIER |
| `.claude/brief.py` | `.claude/hooks/brief.py` | SessionStart hook | MOVED_EARLIER |
| `.claude/skills/test_skills.py` | `.claude/tests/test_skills.py` | tests out of runtime | MOVED_EARLIER |
| `.claude/skills/test_hardening.py` | `.claude/tests/test_hardening.py` | tests out of runtime | MOVED_EARLIER |
| `.claude/skills/test_store.py` | `.claude/tests/test_store.py` | tests out of runtime | MOVED_EARLIER |
| `.claude/skills/test_failclosed.py` | `.claude/tests/test_failclosed.py` | tests out of runtime | MOVED_EARLIER |
| `.claude/skills/test_enforcement.py` | `.claude/tests/test_enforcement.py` | tests out of runtime | MOVED_EARLIER |
| `.claude/skills/evals.py` | `.claude/tests/evals.py` | evals out of runtime | MOVED_EARLIER |
| `.claude/skills/testing.py` | `.claude/tests/testing.py` | test helper | MOVED_EARLIER |
| `.claude/skills/state` | `.claude/state` | runtime state out of runtime (completed by hand after the first run aborted here) | MOVED_EARLIER |
| `00_ԳՑԻՐ_ԱՅՍՏԵՂ/_ԿԱՐԴԱ.md + 04_WhatsApp/ՄՈՒՏՔ.md` | `00_Inbox/Input.md` | merged: inbox note + controlled text-drop (content preserved, English canonical name) | MERGED |
| `04_WhatsApp/Բնօրինակներ` | `None` | emptied legacy directory removed | REMOVED |
| `04_WhatsApp/գործիքներ` | `None` | emptied legacy directory removed | REMOVED |
| `04_WhatsApp` | `None` | emptied legacy directory removed | REMOVED |
| `00_ԳՑԻՐ_ԱՅՍՏԵՂ` | `None` | emptied legacy directory removed | REMOVED |
| `01_Ընթացիկ` | `None` | emptied legacy directory removed | REMOVED |
| `02_Արխիվ/2026-09-09_սևագրեր` | `None` | emptied legacy directory removed | REMOVED |
| `02_Արխիվ/2026-09-10_skill_registry_v1` | `None` | emptied legacy directory removed | REMOVED |
| `02_Արխիվ` | `None` | emptied legacy directory removed | REMOVED |
| `03_Ավարտված` | `None` | emptied legacy directory removed | REMOVED |
| `.claude/skills/__pycache__` | `None` | emptied legacy directory removed | REMOVED |
