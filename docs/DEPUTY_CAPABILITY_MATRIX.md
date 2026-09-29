# Deputy capability matrix / Deputy-ի capability matrix

**Evidence date:** 29 September 2026
**Main/deployed SHA:** `b4157bae72b84c3af4ba30a9ff59fc3ccc836027`
**Important:** “Implemented” is not the same as “live-certified”.

For external writes, the authoritative registry is `command-center/.claude/state/durable/write_certifications.json`. It separates immutable historical proof (`certified_once`) from current host/configuration readiness (`executable_now`); neither state is inferred from documentation alone.

| Capability | User value / Օգտվողի արժեք | Current state | Evidence | Dependencies | Remaining work |
|---|---|---|---|---|---|
| Core Deputy API | One operator entry point and readiness truth | **CONFIRMED / LIVE** | OCI `/health` alive; `/readiness` READY | OCI service | Keep runtime monitored |
| Claude Max reasoning | Broad HouseNet analysis and conversation | **CONFIRMED / LIVE** | Provider reports `claude-code-max`, `claude.ai`, Max, first-party, no API-key fallback | Authenticated Claude Max session | Certify more complex live multi-tool scenarios |
| Persistent conversations | Continue and reopen operating context | **IMPLEMENTED / NOT LIVE-CERTIFIED (live path exists; certification pending)** | Canonical `conversation_store.py`, UI conversation IDs/history, CI coverage | Store | OCI browser evidence for reopen flow |
| Multi-turn context | Follow-ups resolve “that one/previous item” | **IMPLEMENTED / NOT LIVE-CERTIFIED (live path exists; certification pending)** | Context orchestration and conversation tests | Store + provider | Expand live browser/provider evidence |
| General reasoning fallback | Open analytical questions do not require a skill trigger | **IMPLEMENTED / NOT LIVE-CERTIFIED** | Agent loop/context tests and runtime fallback | Claude provider | More live scenario certification |
| Proactive worker | Useful internal work can appear without chat | **CONFIRMED / LIVE** | OCI worker active; latest cycle recorded; proactive tests | Source adapters, Store | Uniform Claude reasoning depth across all sources |
| Source observation | Detect source changes with provenance | **CONFIRMED / LIVE** | Integration adapters, normalization and worker tests | Registered source | More high-volume live cursor evidence |
| Deduplication | Avoid repeated Work/commitments/actions | **IMPLEMENTED / NOT LIVE-CERTIFIED (live path exists; certification pending)** | Idempotency/dedup tests | Store constraints/checkpoints | Broaden cross-source duplicate certification |
| Work outcomes | Track active/waiting/blocked/completed work | **IMPLEMENTED / NOT LIVE-CERTIFIED (live path exists; certification pending)** | Work orchestrator, product Work surface, tests | Store | More live proactive Work evidence |
| Commitment tracking | Distinguish Owner owes/others owe/delegated/FYI | **PARTIAL (implementation exists; live scope limited)** | Commitment extractor/lifecycle tests | Source evidence, identity confidence | More cross-channel live certification |
| Follow-up | Keep unresolved work alive | **PARTIAL (implementation exists; live scope limited)** | Follow-up/proactive tests | Commitments, worker | Certify end-to-end response follow-through |
| Prioritisation | Show why something matters now | **PARTIAL (implementation exists; live scope limited)** | Home/attention logic, operating tests | Current evidence | Broader outcome-quality certification |
| People/entity identity | Connect same person across systems safely | **PARTIAL (implementation exists; live scope limited)** | People capability and confidence/provenance tests | Source identifiers | More real cross-source mappings |
| Decision records | Preserve decision/rationale/review context | **IMPLEMENTED / NOT LIVE-CERTIFIED** | `decisions.py` and Store ownership map | Store | Surface more completely in normal UX |
| Attention queue | Present relevant exceptions and decisions | **IMPLEMENTED / NOT LIVE-CERTIFIED (surface exists; browser certification pending)** | Home/Inbox attention tabs and API | Work/commitments/alerts | Confirm complete OCI browser journey |
| Home | Executive operating view | **CONFIRMED / LIVE** | Product API/UI and prior browser walkthrough | Current Store state | OCI screenshot/browser evidence |
| Deputy chat | Human conversation workspace | **IMPLEMENTED / NOT LIVE-CERTIFIED (live path exists; certification pending)** | Chat UI, provider route, persistence tests | Claude + Store | OCI browser walkthrough and live multi-turn evidence |
| Inbox | Attention, approvals, notifications in one queue | **IMPLEMENTED / NOT LIVE-CERTIFIED (surface exists; browser certification pending)** | Product UI/API, approval tests | Action/alerts state | Browser edit/reprepare certification |
| Work surface | Human outcome view | **IMPLEMENTED / NOT LIVE-CERTIFIED (surface exists; browser certification pending)** | Product UI/API | Work state | Browser evidence |
| Reports | Daily/weekly/monthly/KPI/custom outputs | **PARTIAL (implementation exists; live scope limited)** | Reports route and report tests | Source completeness | Validate each report type against live data |
| Documents | Artifact history/open/download | **IMPLEMENTED / NOT LIVE-CERTIFIED (live path exists; certification pending)** | DOCX/XLSX/PDF generator, stable artifact identity/path tests | Design System, storage | OCI visual/open validation |
| Global search | Find conversations, Work, documents, commitments | **PARTIAL (implementation exists; live scope limited)** | Search route and bounded retrieval | Store/indexed records | Improve Armenian/English retrieval breadth |
| Settings | Configuration and diagnostics | **CONFIRMED / LIVE** | Readiness/integration/system views | Runtime evidence | Browser walkthrough |
| Tasks register | Current management task evidence | **CONFIRMED / LIVE** | OCI certification: 12 records; `INT-TASKS AVAILABLE` | Mounted Tasks.xlsx | Replace fragile spreadsheet in future |
| Outlook Mail read | Mail as evidence for requests/commitments | **CONFIRMED / LIVE** | Windows bridge `/mail`; current read certification | Classic Outlook, bridge, reverse tunnel | Maintain bridge; certify safe write separately |
| Outlook Calendar read | Meeting/deadline context | **CONFIRMED / LIVE** | Windows bridge `/calendar`; current read certification | Classic Outlook, bridge, reverse tunnel | Certify safe calendar write separately |
| Telegram read | Chat evidence and inbound context | **CONFIRMED / LIVE** | Current Telegram read certification | Bot config and allowed chats | Safe write certification where required |
| Telegram write | Approved outbound message | **IMPLEMENTED / NOT LIVE-CERTIFIED** | Action Runtime/write contract and tests | Safe target, provider write evidence | Live safe-target certification |
| Bitrix24 read | Deal/stage/task/identity context | **CONFIRMED / LIVE** | Current OCI Bitrix connected/read certification | Read-scoped webhook | Broaden CRM read correlation |
| Bitrix24 write | Approved CRM update/activity | **IMPLEMENTED / NOT LIVE-CERTIFIED** | Governed capability/action tests | Safe target and verification | Live safe-target certification |
| WhatsApp Business | Official Cloud API source | **BLOCKED / NEEDS SETUP** | Registry declared; readiness missing config | Token, phone ID, verify token, app secret, HTTPS callback | Configure and certify |
| MikroBILL | Billing/revenue source of truth | **PARTIAL (Owner-deferred; unavailable)** | Registry explicitly deferred | Read-only interface, credentials, field dictionary | Lift deferral and inventory |
| Action Runtime | One external mutation boundary | **CONFIRMED / LIVE** | OCI readiness READY; CI action/fail-closed suite | Store, approvals, connector | Safe live write evidence |
| Exact approval | Owner approval bound to action fingerprint | **CONFIRMED / LIVE** | Approval/edit/invalidation tests | Action Store | Browser Edit → reprepare evidence |
| Independent verification | Completion is verified, not assumed | **IMPLEMENTED / NOT LIVE-CERTIFIED (live path exists; certification pending)** | Runtime verification/reconciliation tests | Provider read-back | Per-integration live certification |
| Result unknown/reconcile | No blind retry after uncertain outcome | **IMPLEMENTED / NOT LIVE-CERTIFIED** | Fail-closed/reconciliation tests | Action Runtime | More provider-specific evidence |
| DOCX | Finished branded Word artifact | **IMPLEMENTED / NOT LIVE-CERTIFIED (live path exists; certification pending)** | Generator/parsing tests | Design System | Live visual certification |
| XLSX | Structured workbook | **IMPLEMENTED / NOT LIVE-CERTIFIED (live path exists; certification pending)** | Generator/parsing tests | Design System | Live visual certification |
| PDF | Finished report PDF | **PARTIAL (implementation exists; live scope limited)** | Generator/tests | Unicode-capable PDF runtime | Confirm Armenian rendering in live artifacts |
| Source completeness | Honest partial reports | **IMPLEMENTED / NOT LIVE-CERTIFIED (live path exists; certification pending)** | Health model and report tests | Source health | More mixed-source report evidence |
| Backup | Durable encrypted backup | **CONFIRMED / LIVE** | OCI backup timer active and manifests | Recovery storage | Destructive restore needs key |
| Recovery | Reopen product state after loss | **PARTIAL** | Store/backup/isolated restore mechanics | OCI recovery key | Run destructive restore certification |
| API local auth | Prevent unauthenticated remote exposure | **IMPLEMENTED / NOT LIVE-CERTIFIED** | Localhost default and security tests | Deployment topology | OCI browser/auth walkthrough |
| Markdown safety | Rich answers without XSS | **IMPLEMENTED / NOT LIVE-CERTIFIED** | Sanitizer/adversarial tests | UI renderer | Browser fixture certification |
| Bilingual UI | HY/EN product shell and content | **CONFIRMED / LIVE** | I18N keys, language switching tests, prior browser walkthrough | Translation resources | OCI browser screenshots |
| Light/dark theme | Readable visual modes | **IMPLEMENTED / NOT LIVE-CERTIFIED (live path exists; certification pending)** | UI theme controls/tests | Design System | OCI visual evidence |
| Responsive UI | Narrow/mobile read access | **IMPLEMENTED / NOT LIVE-CERTIFIED** | Responsive CSS and tests | Browser environment | Live mobile walkthrough |
| Public repository privacy | Keep confidential operational data out of public Git | **BLOCKED / NEEDS SETUP (privacy remediation intentionally excluded)** | Owner explicitly excluded this remediation | Separate privacy decision | Not changed in this product documentation task |

**Integration counting model:** The runtime health denominator is six registered source IDs: Tasks, Outlook Mail, Outlook Calendar, Telegram, Bitrix24 and MikroBILL. Outlook Mail and Calendar are separate sources behind one bridge. WhatsApp is outside that denominator because it is not in the runtime registered-source tuple and is therefore shown separately as **BLOCKED / NEEDS SETUP**. The OCI aggregate captured on 29 September 2026 was **4 of 6 available**; this aggregate is retained as evidence and is not silently changed to match the capability-row count.
