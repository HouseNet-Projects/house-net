# Deputy in one page / Deputy-ը մեկ էջում

## What it is / Ի՞նչ է սա

**Deputy is HouseNet’s persistent operating partner.** It watches the Owner’s approved operating world, connects evidence across business systems, remembers Work and commitments, prepares reports/documents/drafts/actions, and keeps following through. It is not a generic chat window: its job is to keep operating work alive between conversations.

Հայերեն՝ **Deputy-ը HouseNet-ի մշտական օպերացիոն գործընկերն է**․ այն դիտարկում է Owner-ի թույլատրված աշխատանքային միջավայրը, կապում է տարբեր համակարգերի evidence-ը, հիշում է Work-ն ու commitments-ը, պատրաստում է հաշվետվություններ, փաստաթղթեր, draft-եր և action candidates, և շարունակում է հետևել աշխատանքին։

## Why it matters / Ինչու է պետք

Without Deputy, the Owner must repeatedly check mail, Telegram, calendar, Bitrix and Tasks; remember promises; chase delegated work; prepare reports; and manually update systems. Deputy replaces repeated checking with one governed operating context.

Deputy’s value is operational:

- fewer lost commitments;
- less cross-system checking;
- clearer ownership and waiting states;
- faster management decisions;
- faster report/document preparation;
- controlled external actions with verification;
- continuity when the Owner is away.

## How it works / Ինչպես է աշխատում

```text
Observe → Understand → Correlate → Remember → Prioritise → Prepare
→ Surface → Owner decides/approves → Execute → Verify → Follow through
```

- **Observe:** registered sources provide current evidence.
- **Understand:** Claude reasons over relevant context.
- **Remember:** Store preserves conversations, Work, commitments, people, decisions and artifacts.
- **Prepare:** Deputy creates internal Work and exact external action candidates.
- **Approve:** Owner approves, edits or rejects material external changes.
- **Execute/verify:** Action Runtime performs and verifies the exact approved action.

## What it can do today / Այսօր ինչ կարող է անել

**CONFIRMED / LIVE on OCI:**

- core API, Store, worker, Action Runtime and Claude Max provider;
- Tasks register reads;
- Outlook Mail and Calendar reads through the Windows Classic Outlook bridge;
- Telegram reads;
- Bitrix24 reads;
- bilingual Home, Deputy, Inbox, Work, Reports, Documents and Settings surfaces;
- persistent conversations, Work/commitment state and document generation;
- exact approval/fingerprint protection and fail-closed action states.

**PARTIAL (needs setup):**

- WhatsApp: requires Meta Cloud API credentials and HTTPS webhook;
- MikroBILL: explicitly deferred and unavailable;
- Outlook/CRM/Telegram external writes: governed paths exist, but each live write requires its own safe certification;
- full OCI browser walkthrough and destructive restore certification remain evidence gaps.

## What it must never do / Ինչ երբեք չպետք է անի

- silently send a message or mutate CRM/calendar/task/customer data;
- treat an inbound message as Owner approval;
- turn an inference into a source fact;
- retry an uncertain external write blindly;
- claim an unavailable integration is ready;
- expose provider JSON, secrets or technical internals in normal UX;
- replace the source system of record.

## The daily Owner journey / Owner-ի ամենօրյա օգտագործումը

1. **Home:** see priorities, attention, changes and prepared work.
2. **Deputy:** ask a question or continue a matter with context.
3. **Work:** understand outcome, owner, blocker and next step.
4. **Inbox:** review exact prepared actions and approve/edit/reject.
5. **Reports/Documents:** inspect finished management outputs.
6. **Settings:** check integrations, provider and technical diagnostics.

## Current readiness / Ներկա readiness

Repository main and OCI deployed SHA: `b4157bae72b84c3af4ba30a9ff59fc3ccc836027`. OCI `/readiness`: **READY**. Product runtime: **AVAILABLE**. Business data: **4 of 6 available**; WhatsApp needs setup and MikroBILL is PARTIAL (Owner-deferred; unavailable). Public-repository confidential-data exposure is intentionally outside this product document’s remediation scope.

**Counting note / Հաշվարկի նշում:** The runtime denominator is six registered IDs: Tasks, Outlook Mail, Outlook Calendar, Telegram, Bitrix24 and MikroBILL. Mail and Calendar are separate sources sharing one bridge. WhatsApp is not in that denominator because it is not registered in the runtime health model; it remains **BLOCKED / NEEDS SETUP** separately. The captured OCI aggregate was **4 of 6 available**; per-source state and qualifiers remain authoritative.
