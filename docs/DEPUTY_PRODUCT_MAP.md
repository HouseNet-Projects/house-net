# Deputy product map / Deputy-ի արտադրանքային քարտեզ

This map describes the product in business terms first. Technical ownership is listed after the product diagrams.

## 1. Product relationship map

```mermaid
flowchart TD
    OWNER[Owner\nsees / asks / decides / approves]
    DEPUTY[Deputy\ncontinuous operating partner]
    CONV[Conversations\ncontext and intent]
    WORK[Work\noutcomes and next steps]
    COMMIT[Commitments\nOwner owes / others owe / delegated]
    PEOPLE[People and entities\nidentity + confidence]
    ATTENTION[Attention and priorities\nwhat matters now]
    EVIDENCE[Evidence and observations\nsource + freshness + provenance]
    APPROVAL[Approval\nexact effect + risk + fingerprint]
    ACTION[Action Runtime\nexecute + verify]
    REPORTS[Reports\nmanagement intelligence]
    DOCS[Documents\nfinished artifacts]
    MEMORY[(Durable memory / Store)]
    SOURCES[Business systems\nTasks · Outlook · Telegram · Bitrix · WhatsApp · MikroBILL]

    OWNER <--> DEPUTY
    DEPUTY <--> CONV
    DEPUTY --> WORK
    DEPUTY --> COMMIT
    DEPUTY --> PEOPLE
    DEPUTY --> ATTENTION
    SOURCES --> EVIDENCE
    EVIDENCE --> DEPUTY
    DEPUTY <--> MEMORY
    DEPUTY --> REPORTS
    DEPUTY --> DOCS
    DEPUTY --> APPROVAL
    APPROVAL --> ACTION
    ACTION --> SOURCES
    ACTION --> EVIDENCE
    WORK --> ATTENTION
    COMMIT --> ATTENTION
```

Հայերեն՝ Owner-ը շփվում է մեկ Deputy-ի հետ, իսկ Deputy-ը կապում է Conversations, Work, Commitments, People, Attention, Evidence, Reports, Documents և արտաքին Business systems-ը։

## 2. Operating loop

```mermaid
flowchart LR
    O[Observe source event]
    N[Normalize + dedupe]
    C[Retrieve current context]
    R[Reason with Claude]
    W[Update Work / commitments / memory]
    P[Prepare report / draft / action]
    S[Surface Home / Inbox / Work / chat]
    D[Owner decides / edits / approves]
    X[Action Runtime executes]
    V[Independent verify]
    F[Follow through]
    O --> N --> C --> R --> W --> P --> S --> D --> X --> V --> F --> O
```

**Important:** internal preparation does not wait for approval. Approval starts at the material external mutation boundary.

Հայերեն՝ ներքին պատրաստումը հաստատում չի պահանջում։ Հաստատումը սկսվում է այն պահին, երբ Deputy-ը պատրաստվում է նյութական արտաքին փոփոխություն կատարել։

## 3. User → Deputy → business systems

```mermaid
sequenceDiagram
    participant Owner
    participant Deputy
    participant Claude
    participant Store
    participant Systems as Business systems
    participant Runtime as Action Runtime

    Owner->>Deputy: ask / follow up / review Home
    Deputy->>Store: retrieve conversation, Work, commitments, people
    Deputy->>Systems: read certified current evidence
    Deputy->>Claude: bounded relevant context
    Claude-->>Deputy: analysis, tool requests, recommendation or prepared work
    Deputy->>Store: persist Work, commitment, evidence or artifact
    Deputy-->>Owner: answer, limitation, decision or action candidate
    Owner->>Deputy: approve / edit / reject
    Deputy->>Runtime: exact approved action
    Runtime->>Systems: governed external mutation
    Systems-->>Runtime: result
    Runtime->>Systems: independent verification/read-back
    Runtime-->>Deputy: verified / failed / result unknown
    Deputy->>Store: update outcome and follow-through
```

## 4. Approval and execution

```mermaid
flowchart TD
    PREP[Deputy prepares exact action]
    SHOW[Show target, effect, risk, content and evidence]
    CHOICE{Owner choice}
    EDIT[Edit material field]
    INVALIDATE[Invalidate old fingerprint/token]
    REPREP[Prepare new exact candidate]
    APPROVE[Approve exact current candidate]
    REJECT[Reject and retain decision]
    EXEC[Action Runtime]
    VERIFY[Independent verify]
    UNKNOWN[RESULT_UNKNOWN\nreconcile before retry]
    FOLLOW[Update Work and continue]
    PREP --> SHOW --> CHOICE
    CHOICE --> EDIT --> INVALIDATE --> REPREP --> SHOW
    CHOICE --> APPROVE --> EXEC --> VERIFY --> FOLLOW
    CHOICE --> REJECT
    EXEC --> UNKNOWN --> VERIFY
```

## 5. Product surfaces

```mermaid
flowchart LR
    HOME[Home\noperating view]
    CHAT[Deputy\nconversation]
    INBOX[Inbox\nattention + approvals + notifications]
    WORK[Work\noutcomes]
    REPORTS[Reports\nmanagement outputs]
    DOCS[Documents\nartifacts]
    SETTINGS[Settings\nconfiguration + diagnostics]
    HOME <--> CHAT
    HOME <--> INBOX
    CHAT <--> WORK
    CHAT --> REPORTS
    CHAT --> DOCS
    INBOX <--> WORK
    REPORTS --> DOCS
    SETTINGS -. diagnostics .- HOME
```

## 6. Conceptual ownership map

| Product concept | Meaning | Current canonical implementation owner |
|---|---|---|
| Conversation | durable multi-turn interaction | `conversation_store.py` |
| Observation | source event/fact | registered integration adapters + Store |
| Evidence | provenance-backed support | Store + source adapters |
| Person/entity | identity link with confidence | Store / people capability |
| Work | durable outcome | `work_orchestrator.py` |
| Commitment | obligation and follow-up | `commitments.py` |
| Decision | durable choice/rationale | `decisions.py` |
| Attention | prioritised situation | alerts/attention state |
| Approval | exact Owner authority | `actions.py` |
| Action | external mutation candidate/execution | `actions.py` |
| Artifact | generated document/report | `document_exports.py` |
| Source/integration | declared capability and health | `registry.py` + `health.py` |

## 7. Truth labels

- **CONFIRMED / LIVE:** directly observed in current OCI runtime.
- **IMPLEMENTED / NOT LIVE-CERTIFIED:** code/tests exist; current host evidence is missing.
- **DESIGNED / INTENDED:** product behavior defined by architecture/governance but not universal live proof.
- **PARTIAL:** usable with a declared limitation.
- **BLOCKED / NEEDS SETUP:** external credential, callback or runtime dependency is missing.
- **FUTURE / PROPOSED:** not represented as current capability.
