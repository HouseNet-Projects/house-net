# BroPS AI Agent OS — Canonical Master Execution Roadmap

**Repository:** `menqstudio/OS`  
**Product:** BroPS AI Agent OS  
**Document type:** Canonical execution roadmap  
**Status:** `ACTIVE — IMPLEMENTATION AUTHORITY`  
**Owner:** Gev  
**Primary implementer:** Claude Code  
**Independent reviewer:** ChatGPT  
**Merge authority:** Owner only  

---

## 0. Purpose

This document is the single execution roadmap for turning the existing BroPS AIOS visual prototype and the Bro governance engine into one secure, usable, production-grade desktop AI Agent OS.

Claude MUST use this roadmap as the implementation sequence.

Claude MUST NOT reinterpret this roadmap as permission to redesign the product architecture, weaken governance, bypass security gates, or merge without Owner approval.

The existing `brops-aios.html` prototype is the primary visual and interaction reference for the UI implementation. It is not disposable inspiration. Its distinctive spatial language, living backgrounds, non-rectangular systems, agent mesh, command reactor, temporal memory field, integration stars, provider sockets, animated task conduits, and futuristic AI-native mood MUST be preserved and evolved into maintainable application code.

---

## 1. Product Definition

BroPS is not a generic dashboard.

BroPS is a command-first AI Agent Operating System where:

1. Gev issues a command.
2. Bro interprets and decomposes the command.
3. The governed engine authorizes or rejects execution.
4. Specialist agents collaborate through explicit routed work.
5. Providers remain infrastructure seats, never authority owners.
6. Every meaningful action produces evidence.
7. Every completed governed action produces an authentic verifiable receipt.
8. The UI exposes real system state rather than decorative fake activity.

The desktop application is the conductor and visual operating surface.

The desktop application MUST NOT own:

- issuer keys;
- lease authority;
- privileged environment secrets;
- final authorization decisions;
- receipt-signing authority.

Those remain under the local governed supervisor / sidecar and Bro engine.

---

## 2. Canonical Product Principles

### 2.1 Command-first

The primary interaction is a command, not menu navigation.

Navigation supports the command lifecycle but does not replace it.

### 2.2 Bro-first orchestration

Users do not manually wire every agent for ordinary work.

Bro selects, routes, consults, delegates, verifies, and presents evidence.

### 2.3 Living system, not static admin UI

The interface MUST visibly communicate:

- active command;
- agent participation;
- agent state;
- handoffs;
- task progress;
- memory recall;
- knowledge retrieval;
- provider health;
- integration activity;
- governance holds;
- receipt verification;
- failure and recovery.

### 2.4 Evidence over claims

The UI MUST never say an action ran, completed, passed, synced, or succeeded without actual runtime evidence.

### 2.5 Fail closed

Missing authorization, invalid receipt, unavailable supervisor, invalid lease, schema mismatch, provider failure, timeout, or verification failure MUST produce a blocked or failed state, never a simulated success.

### 2.6 Visual uniqueness

Every major page MUST have its own spatial composition and identity while remaining inside one coherent design system.

Do not convert all pages into identical rectangular card grids.

---

## 3. Status Vocabulary

- `[ ]` Todo
- `[~]` In progress
- `[R]` Ready for review
- `[x]` Done
- `[L]` Locked
- `[B]` Blocked

Claude MUST update roadmap status only when supported by repository evidence and passing validation.

---

## 4. Global Execution Rules for Claude

Claude MUST:

1. Read repository canonical startup documentation before work.
2. Read this roadmap completely.
3. Inspect the current branch, open PRs, CI state, and existing implementation before editing.
4. Work in scoped branches.
5. Keep each PR reviewable.
6. Run tests locally when a real worktree is available.
7. Push only validated commits.
8. keep PRs as draft until acceptance criteria are satisfied.
9. preserve all governance and security invariants.
10. update documentation in the same PR as behavior changes.
11. continue autonomously through routine implementation work.
12. stop only for a defined stop condition.
13. never merge.
14. never invent test results, runtime results, screenshots, provider output, or security evidence.

Claude MUST NOT:

- merge to `main`;
- store secrets in frontend, repository, logs, fixtures, screenshots, or receipts;
- let the desktop mint authorization;
- call external AI providers directly from UI code;
- silently bypass the supervisor;
- fabricate signed receipts;
- replace authentic receipts with ordinary JSON evidence;
- mark visual placeholders as completed functionality;
- redesign the approved UI into a generic SaaS dashboard;
- remove difficult functionality merely to make CI green;
- weaken schemas, tests, or security gates to pass validation.

---

## 5. Branch and PR Strategy

Recommended sequence:

1. `roadmap/master-execution-roadmap`
2. `fix/phase1-authentic-receipt-contract`
3. `feat/local-supervisor-sidecar`
4. `feat/governed-provider-runtime`
5. `feat/desktop-runtime-bridge`
6. `feat/ui-foundation-design-system`
7. `feat/ui-command-reactor`
8. `feat/ui-agent-mesh`
9. `feat/ui-projects-tasks`
10. `feat/ui-chat-groups`
11. `feat/ui-knowledge-memory`
12. `feat/ui-automations-integrations`
13. `feat/ui-analytics-settings`
14. `feat/end-to-end-agent-os`
15. `hardening/release-candidate`

A large phase MAY use several smaller PRs.

Each PR MUST contain:

- scope;
- changed contracts;
- implementation summary;
- security impact;
- tests run;
- known limitations;
- screenshots or recordings for UI work;
- exact acceptance criteria completed;
- explicit unresolved items.

---

# PHASE 0 — Repository and Canonical Baseline

## Objective

Establish one verified starting point before new implementation.

## Tasks

- [ ] Confirm current `main` HEAD.
- [ ] Inventory repository structure.
- [ ] Identify engine, bridge, desktop app, tests, schemas, workflows, and documentation.
- [ ] Identify current open PRs and their exact state.
- [ ] Confirm the current Phase 1 bridge branch and PR.
- [ ] Confirm whether `MASTER_EXECUTION_ROADMAP.md` already exists and replace or supersede incomplete skeletons.
- [ ] Add this document to canonical startup documentation or manifest.
- [ ] Add `brops-aios.html` as an explicit UI reference artifact, or document its canonical storage path.
- [ ] Record current test and CI baseline.
- [ ] Record all known architectural gaps.

## Acceptance Criteria

- Repository state is documented.
- No unknown active implementation branch is treated as canonical.
- This roadmap is discoverable from repository root documentation.
- The UI reference artifact has a stable canonical path.
- Existing CI status is recorded with real evidence.

## Stop Conditions

Stop if:

- repository identity is ambiguous;
- multiple incompatible canonical branches exist;
- current `main` cannot be verified;
- the UI artifact is missing or corrupted.

---

# PHASE 1 — Correct the Engine Bridge Contract

## Objective

Create a minimal, truthful, schema-validated bridge between the desktop-facing runtime and the Bro governance engine.

## Critical Existing Defect

The current bridge implementation synthesizes a JSON object called a `receipt` from task ID, status, exit code, and evidence.

That object is outcome evidence, not an authentic signed receipt.

This mismatch MUST be corrected before the bridge is considered complete.

## Required Decision

Use one of the following explicit models.

### Model A — Evidence now, signed receipt later

Rename the current object to:

- `run_evidence`; or
- `outcome_evidence`.

The schema MUST NOT label it as a receipt.

A later supervisor phase returns the authentic signed receipt.

### Model B — Authentic receipt in Phase 1

Define the complete signed receipt structure and verification contract now.

Minimum receipt fields:

- receipt version;
- receipt ID;
- task ID;
- command ID;
- issuer identity;
- issued timestamp;
- authorization reference;
- lease reference where applicable;
- execution status;
- normalized outcome digest;
- evidence digest;
- policy version;
- engine version;
- signature algorithm;
- key ID;
- signature;
- verification state.

## Tasks

- [ ] Rename false receipt types or implement authentic receipt types.
- [ ] Separate `run_evidence` from `signed_receipt`.
- [ ] Add strict versioned JSON schemas.
- [ ] Reject unknown critical fields where required.
- [ ] Add deterministic canonical serialization for signing.
- [ ] Add schema validation before transport.
- [ ] Add request and response correlation IDs.
- [ ] Add explicit error taxonomy.
- [ ] Add timeout behavior.
- [ ] Add cancellation behavior.
- [ ] Add supervisor unavailable behavior.
- [ ] Add engine rejection behavior.
- [ ] Add malformed response handling.
- [ ] Add tests for all contract boundaries.
- [ ] Update `bridge/DESIGN.md`.
- [ ] Update `bridge/README.md`.
- [ ] Update CI to validate schemas and bridge tests.

## Acceptance Criteria

- No unsigned ordinary evidence object is called a receipt.
- Bridge requests and responses are versioned.
- Invalid schemas fail closed.
- Errors are typed and user-presentable.
- Tests cover success, rejection, timeout, malformed response, invalid signature shape, and unavailable runtime.
- CI is green on supported platforms.

## Merge Gate

Do not merge Phase 1 until independent review confirms the receipt terminology and trust boundary are correct.

---

# PHASE 2 — Local Governed Supervisor / Sidecar

## Objective

Implement the trusted local runtime that sits between the desktop and the engine/provider execution path.

## Authority Boundary

The sidecar MAY own or access:

- local issuer keys;
- secure provider credentials;
- authorization verification;
- lease validation;
- receipt signing;
- runtime process control;
- provider adapters;
- audit log append;
- health and recovery state.

The desktop MUST NOT own these capabilities.

## Tasks

### Process Lifecycle

- [ ] Define sidecar executable/package.
- [ ] Define startup sequence.
- [ ] Define graceful shutdown.
- [ ] Define crash recovery.
- [ ] Define single-instance behavior.
- [ ] Define stale lock detection.
- [ ] Define health endpoint or IPC health method.
- [ ] Define protocol version negotiation.

### Secure IPC

- [ ] Choose local IPC transport.
- [ ] Bind only to local trusted scope.
- [ ] Authenticate desktop-to-sidecar communication.
- [ ] Prevent arbitrary local process invocation.
- [ ] Add request replay protection where applicable.
- [ ] Add message size limits.
- [ ] Add strict schema validation.
- [ ] Add rate and concurrency limits.

### Key and Secret Management

- [ ] Define OS-backed secure storage.
- [ ] Never persist plaintext secrets in repository or app config.
- [ ] Define key IDs and rotation.
- [ ] Define corrupted-key behavior.
- [ ] Define missing-key behavior.
- [ ] Define operator provisioning.
- [ ] Define credential removal and provider disable flow.

### Authorization

- [ ] Verify command authorization.
- [ ] Verify task authorization.
- [ ] Verify lease and expiration.
- [ ] Verify scope and capability.
- [ ] Reject unauthorized provider calls.
- [ ] Reject unauthorized filesystem/process/network operations.
- [ ] Record policy decision evidence.

### Signed Receipt

- [ ] Canonicalize receipt payload.
- [ ] Sign receipt.
- [ ] Return key ID and algorithm.
- [ ] Provide verification API or verifier library.
- [ ] Detect modified receipt.
- [ ] Detect unknown key.
- [ ] Detect expired or invalid authorization reference.
- [ ] Persist append-only receipt/audit evidence.

## Acceptance Criteria

- Desktop cannot execute governed work if sidecar is unavailable.
- Desktop cannot mint valid receipts.
- Tampered receipts fail verification.
- Secrets do not appear in logs.
- Authorization denial is visible and typed.
- Crash recovery does not silently claim completion.
- Sidecar health and protocol version are observable.

---

# PHASE 3 — Governed Provider Runtime

## Objective

Connect AI providers without giving providers governance authority.

## Initial Scope

Slice 1 remains non-streaming unless architecture explicitly upgrades it.

Provider default state is OFF.

## Providers

Initial adapters MAY include:

- OpenAI;
- Anthropic;
- local LM Studio;
- other approved local or remote model providers.

No provider is enabled merely because an adapter exists.

## Tasks

### Provider Abstraction

- [ ] Define provider adapter interface.
- [ ] Define model capability metadata.
- [ ] Define request normalization.
- [ ] Define response normalization.
- [ ] Define token/usage metadata.
- [ ] Define provider error mapping.
- [ ] Define cancellation and timeout.
- [ ] Define retry policy.
- [ ] Define provider health status.
- [ ] Define OFF / unavailable / degraded / ready states.

### Governed Execution

- [ ] Require authorized task envelope.
- [ ] Require sidecar mediation.
- [ ] Record selected provider and model.
- [ ] Record request digest, not raw secret material.
- [ ] Record response digest.
- [ ] Return outcome evidence.
- [ ] Produce signed receipt only after governed completion.
- [ ] Reject direct frontend provider calls.

### Local Provider Seating

- [ ] Detect LM Studio availability.
- [ ] Show loaded models.
- [ ] Show unavailable local provider.
- [ ] Do not auto-start external processes without explicit policy.
- [ ] Represent provider seating visually in UI.

## Acceptance Criteria

- Provider calls are impossible from UI without sidecar.
- Provider OFF state is respected.
- Failed provider requests never produce successful receipts.
- Provider/model identity appears in evidence.
- Local and remote providers share one normalized runtime contract.

---

# PHASE 4 — Desktop Runtime Bridge

## Objective

Connect the Tauri desktop application to the governed sidecar through a narrow typed interface.

## Tasks

- [ ] Define Tauri command surface.
- [ ] Keep secret-bearing logic outside frontend.
- [ ] Add runtime health polling/events.
- [ ] Add command submission.
- [ ] Add cancellation.
- [ ] Add task state updates.
- [ ] Add receipt retrieval and verification status.
- [ ] Add provider status.
- [ ] Add agent status.
- [ ] Add audit/event stream.
- [ ] Add reconnect behavior.
- [ ] Add offline/unavailable states.
- [ ] Add protocol mismatch state.
- [ ] Add typed frontend client.
- [ ] Add mock runtime for UI development only.
- [ ] Clearly label mocked development data.
- [ ] Ensure production builds cannot silently use mock success paths.

## Acceptance Criteria

- One typed runtime client is used across the app.
- All runtime state has explicit loading, ready, failed, blocked, and unavailable states.
- Mock runtime cannot be mistaken for production runtime.
- A full non-streaming governed command can travel UI → sidecar → engine/provider → evidence/receipt → UI.

---

# PHASE 5 — UI Foundation and Design System

## Objective

Convert the standalone HTML visual language into a maintainable, token-driven React/Tauri design system without flattening its identity.

## Design Direction

The product must feel:

- AI-native;
- futuristic;
- spatial;
- alive;
- premium;
- dark-first;
- technically credible;
- cinematic without becoming unreadable;
- unique page by page;
- coherent as one OS.

## Mandatory Design System Layers

### Tokens

- [ ] color primitives;
- [ ] semantic colors;
- [ ] surface levels;
- [ ] text hierarchy;
- [ ] agent-state colors;
- [ ] group/guild colors;
- [ ] provider states;
- [ ] governance states;
- [ ] task states;
- [ ] receipt verification states;
- [ ] spacing;
- [ ] radii;
- [ ] irregular shape tokens;
- [ ] shadows;
- [ ] glow;
- [ ] blur;
- [ ] border;
- [ ] typography;
- [ ] motion duration;
- [ ] easing;
- [ ] z-index;
- [ ] responsive breakpoints.

### Components

- [ ] buttons;
- [ ] icon buttons;
- [ ] command input;
- [ ] status chips;
- [ ] agent avatars;
- [ ] agent nodes;
- [ ] provider sockets;
- [ ] task nodes;
- [ ] receipt badges;
- [ ] evidence panels;
- [ ] floating dock;
- [ ] contextual rail;
- [ ] drawers;
- [ ] dialogs;
- [ ] tooltips;
- [ ] command palette;
- [ ] empty states;
- [ ] error states;
- [ ] blocked states;
- [ ] skeletons;
- [ ] connection indicators;
- [ ] timeline events;
- [ ] spatial cards with multiple silhouettes.

### Motion

- [ ] page reveal;
- [ ] command reactor pulse;
- [ ] agent activation;
- [ ] agent handoff beam;
- [ ] task conduit progress;
- [ ] memory mote recall;
- [ ] provider seat activation;
- [ ] integration tether activity;
- [ ] receipt verification transition;
- [ ] panel/drawer transitions;
- [ ] reduced-motion support.

## Prohibitions

Do not:

- use one identical card component everywhere;
- hard-code visual values throughout pages;
- make all layouts simple grids;
- use motion without state meaning;
- sacrifice accessibility for glow;
- hide critical errors inside decorative animation.

## Acceptance Criteria

- Tokens replace scattered hard-coded values.
- Components support real states.
- Reduced motion works.
- Keyboard navigation works.
- Visual identity remains recognizably derived from the reference HTML.
- Each major page has a distinct composition.

---

# PHASE 6 — Global Application Shell

## Objective

Build the OS frame around all working surfaces.

## Navigation

Canonical primary navigation:

1. Command
2. Projects
3. Tasks
4. Agents
5. Knowledge
6. Memory
7. Settings

Contextual or secondary surfaces:

- Chat;
- Groups;
- Automations;
- Integrations;
- Analytics;
- Notifications;
- Providers;
- Receipts / Audit;
- Command Palette.

## Tasks

- [ ] Application shell.
- [ ] Collapsible navigation.
- [ ] Active route state.
- [ ] Global runtime status.
- [ ] Provider status.
- [ ] Notification center.
- [ ] Global command dock.
- [ ] Keyboard shortcuts.
- [ ] Command palette.
- [ ] Window controls.
- [ ] Theme support.
- [ ] HY/EN runtime language switch.
- [ ] Persistent route and workspace state.
- [ ] Safe session restore.
- [ ] Global error boundary.

## Acceptance Criteria

- Core navigation works.
- Command dock is available from every major surface.
- Runtime unavailable state is globally visible.
- Theme and language persist.
- No page requires fake data to render safely.

---

# PHASE 7 — Command Reactor

## Objective

Implement the main command-first operating surface.

## Visual Identity

The Command page MUST use the Command Reactor concept from the HTML reference.

It should feel like the center of the operating system, not a chat box placed inside a dashboard.

## Required Regions

- command reactor core;
- floating command dock;
- live command readout;
- interpretation state;
- decomposition steps;
- selected/consulted agent council;
- governance decision;
- provider seat;
- task execution trace;
- evidence and signed receipt;
- failure/retry/recovery controls.

## States

- idle;
- focused;
- typing;
- parsing;
- awaiting authorization;
- authorized;
- blocked;
- dispatching;
- executing;
- awaiting provider;
- collecting evidence;
- signing receipt;
- complete;
- failed;
- cancelled;
- supervisor unavailable;
- provider unavailable;
- invalid receipt.

## Tasks

- [ ] Command input.
- [ ] Structured command envelope preview.
- [ ] Agent mentions.
- [ ] Attachment handling.
- [ ] Command history.
- [ ] Inline agent council.
- [ ] Task decomposition visualization.
- [ ] Governance hold visualization.
- [ ] Provider seating visualization.
- [ ] Real execution state.
- [ ] Evidence viewer.
- [ ] Receipt viewer.
- [ ] Receipt verification result.
- [ ] Retry only when policy permits.
- [ ] Cancel behavior.
- [ ] Keyboard-first UX.
- [ ] Accessible textual equivalents for spatial animation.

## Acceptance Criteria

- A real governed command completes end to end.
- Every state is driven by actual runtime events.
- No success state appears before receipt/evidence conditions are met.
- Blocked actions clearly explain why.
- The page is visually unique and recognizably AI-native.

---

# PHASE 8 — Living Agent Network

## Objective

Implement the full agent operating surface as a living spatial network.

## Visual Identity

The Agents page MUST preserve:

- honeycomb / mesh behavior;
- spatial groups;
- agent state carried by form;
- intra-group lines;
- focused agent lighting its network;
- active handoff visualization;
- group identity;
- live operational presence.

## Agent Model

Each agent needs:

- immutable ID;
- display name;
- domain;
- nickname;
- avatar;
- group/guild;
- capabilities;
- permissions;
- provider/model preferences;
- current state;
- workload;
- current command/task links;
- health;
- last activity;
- evidence references.

## States

- offline;
- idle;
- observing;
- selected;
- consulted;
- assigned;
- working;
- waiting;
- blocked;
- failed;
- reviewing;
- completed;
- unavailable.

## Tasks

- [ ] Agent registry.
- [ ] Group/guild layout.
- [ ] Responsive spatial mesh.
- [ ] Search/filter.
- [ ] Agent details.
- [ ] Capability viewer.
- [ ] Permission viewer.
- [ ] Current work.
- [ ] Handoff trace.
- [ ] Agent activity history.
- [ ] Agent invocation from command.
- [ ] Multi-select for explicit councils.
- [ ] Safe disabled/unavailable states.
- [ ] Real-time event updates.
- [ ] Performance strategy for 38+ nodes.

## Acceptance Criteria

- Full agent roster renders performantly.
- State is visually and textually represented.
- Handoffs correspond to real routed events.
- Agents cannot claim capabilities not present in registry.
- Selecting an agent reveals real status and work context.

---

# PHASE 9 — Projects

## Objective

Represent long-running workstreams and their AI participants.

## Visual Identity

Projects should appear as parallel work lanes, not a generic list of cards.

## Required Capabilities

- project creation;
- project status;
- goals;
- active commands;
- tasks;
- assigned agents;
- decisions;
- knowledge;
- memory;
- evidence;
- receipts;
- files;
- timeline;
- blockers;
- activity.

## Tasks

- [ ] Project model.
- [ ] Project list/workspace.
- [ ] Parallel project lanes.
- [ ] Project command context.
- [ ] Assigned agent band.
- [ ] Milestones.
- [ ] Task linkage.
- [ ] Knowledge linkage.
- [ ] Memory linkage.
- [ ] Receipt/evidence linkage.
- [ ] Activity timeline.
- [ ] Archive behavior.
- [ ] Search/filter.
- [ ] Empty and blocked states.

## Acceptance Criteria

- Commands can be scoped to a project.
- Tasks and evidence are traceable to the project.
- Agent participation is visible.
- Archived projects remain auditable.

---

# PHASE 10 — Tasks

## Objective

Expose command decomposition and execution as real governed tasks.

## Visual Identity

Tasks should use connected nodes, gating strings, frontier pulses, and agent lanes where useful.

## Task Model

- task ID;
- command ID;
- project ID;
- parent task;
- dependencies;
- assigned agent;
- authorization;
- lease;
- state;
- attempts;
- provider/model;
- timestamps;
- evidence;
- receipt;
- error;
- recovery action.

## States

- proposed;
- awaiting approval;
- authorized;
- queued;
- running;
- waiting;
- blocked;
- failed;
- cancelled;
- completed;
- verification failed.

## Tasks

- [ ] Task graph.
- [ ] Dependency handling.
- [ ] Gating task visualization.
- [ ] Frontier/current task visualization.
- [ ] Agent lanes.
- [ ] Task detail drawer.
- [ ] Evidence view.
- [ ] Receipt view.
- [ ] Retry rules.
- [ ] Cancellation.
- [ ] Blocker resolution.
- [ ] Timeline.
- [ ] Filters.
- [ ] Project/command linkage.

## Acceptance Criteria

- UI state matches runtime state.
- Dependencies are enforced.
- Unauthorized tasks cannot enter running state.
- Failed tasks preserve evidence.
- Completion is distinguishable from verification failure.

---

# PHASE 11 — Chat and Group Collaboration

## Objective

Provide conversational interaction without reducing BroPS to a normal messenger.

## Chat Types

- Gev ↔ Bro;
- Gev ↔ selected agent;
- Gev ↔ agent council;
- project chat;
- task chat;
- group/guild room;
- agent-to-agent trace view.

## Group Chat Requirement

Group chat is mandatory.

It must show:

- participants;
- requesting agent;
- consulted agents;
- handoffs;
- tool/runtime events;
- decisions;
- action proposals;
- governance holds;
- evidence links.

## Tasks

- [ ] Chat shell.
- [ ] Thread model.
- [ ] Agent mentions.
- [ ] Inline council.
- [ ] Group rooms.
- [ ] Project/task context.
- [ ] File/knowledge references.
- [ ] Proposed action cards.
- [ ] Approval/deny interactions.
- [ ] Runtime event messages.
- [ ] Receipt/evidence links.
- [ ] Search.
- [ ] Unread state.
- [ ] Notifications.
- [ ] Safe rendering.
- [ ] Streaming only after architecture approval.

## Acceptance Criteria

- Chat cannot bypass command authorization.
- Proposed actions remain proposals until governed execution.
- Agent identity is explicit.
- Group chat preserves an auditable collaboration trace.
- Runtime events are visually distinct from human/agent messages.

---

# PHASE 12 — Neural Knowledge Map

## Objective

Implement the knowledge base as a navigable connected intelligence surface.

## Visual Identity

Use the Neural Knowledge Map concept rather than a plain document table.

## Knowledge Model

- item ID;
- type;
- title;
- content/reference;
- source;
- project;
- tags;
- relationships;
- confidence;
- freshness;
- access scope;
- created/updated timestamps;
- embedding/index status;
- citations;
- usage history.

## Tasks

- [ ] Knowledge ingestion.
- [ ] Search.
- [ ] Semantic retrieval.
- [ ] Relationship graph.
- [ ] Source/citation display.
- [ ] Project linkage.
- [ ] Agent usage.
- [ ] Freshness state.
- [ ] Conflict/duplicate handling.
- [ ] Access controls.
- [ ] Knowledge telemetry.
- [ ] Empty/error/reindex states.
- [ ] Retrieval evidence attached to command/task.

## Acceptance Criteria

- Retrieved knowledge is traceable to sources.
- Unsupported claims are not displayed as sourced knowledge.
- Access controls are enforced.
- Knowledge used in execution is attached to evidence.

---

# PHASE 13 — Temporal Memory Field

## Objective

Represent memory across time with provenance, strength, relevance, and control.

## Visual Identity

Preserve:

- temporal field;
- memory motes;
- memory core;
- recall lines;
- selected memory state;
- recent memory operations;
- strength/weight visualization.

## Memory Types

- preference;
- fact;
- decision;
- project state;
- relationship;
- failure lesson;
- operational context;
- temporary working memory.

## Tasks

- [ ] Memory schema.
- [ ] Provenance.
- [ ] Confidence.
- [ ] Temporal validity.
- [ ] Project scope.
- [ ] Privacy/sensitivity.
- [ ] Recall.
- [ ] Create/update/delete controls.
- [ ] Memory conflict handling.
- [ ] User correction.
- [ ] Audit history.
- [ ] Memory selection UI.
- [ ] Recall visualization.
- [ ] Command evidence linkage.

## Acceptance Criteria

- Memory has provenance.
- User can inspect why memory was recalled.
- Corrections do not silently erase audit history.
- Sensitive memory is protected.
- Memory recall is never represented as certainty when confidence is low.

---

# PHASE 14 — Automations

## Objective

Create governed recurring and event-driven workflows.

## Visual Identity

Automations should appear as horizontal energy conduits with clear triggers, gates, agents, and outputs.

## Automation Model

- automation ID;
- trigger;
- schedule/event;
- authorization policy;
- agent route;
- actions;
- provider;
- state;
- last run;
- next run;
- evidence;
- receipt;
- failure policy.

## Tasks

- [ ] Automation builder.
- [ ] Trigger selection.
- [ ] Schedule configuration.
- [ ] Agent route.
- [ ] Governance gate.
- [ ] Dry run.
- [ ] Enable/disable.
- [ ] Run history.
- [ ] Failure handling.
- [ ] Receipt/evidence.
- [ ] Notification policy.
- [ ] Safe deletion.
- [ ] Real ISP/BroPS examples only when approved.

## Acceptance Criteria

- Automations default OFF.
- Each run is authorized.
- Each run produces evidence.
- Failed runs do not silently retry beyond policy.
- Destructive actions require explicit safeguards.

---

# PHASE 15 — Integrations

## Objective

Connect external systems through explicit governed adapters.

## Visual Identity

Use integration stars tethered to a central Bro integration core.

## Tasks

- [ ] Integration registry.
- [ ] Connection state.
- [ ] Credential provisioning.
- [ ] Capability scope.
- [ ] Health.
- [ ] Test connection.
- [ ] Enable/disable.
- [ ] Revocation.
- [ ] Audit history.
- [ ] Integration activity.
- [ ] Command/task usage.
- [ ] Failure state.
- [ ] Rate limits.
- [ ] Data minimization.

## Acceptance Criteria

- Integrations are OFF until configured.
- Credentials remain outside frontend.
- Every integration action is scoped and evidenced.
- Revoked integrations fail closed.
- The UI shows real connection state.

---

# PHASE 16 — Analytics

## Objective

Expose operational truth about the AI OS.

## Metrics

- command volume;
- completion rate;
- blocked rate;
- failure rate;
- agent utilization;
- handoff count;
- provider usage;
- model usage;
- latency;
- first-token latency when streaming exists;
- task duration;
- receipt verification failures;
- memory recalls;
- knowledge retrieval;
- automation runs;
- integration health;
- cost/usage where supported.

## Visual Identity

Analytics should feel like live operational telemetry, not decorative charts.

## Tasks

- [ ] Metric definitions.
- [ ] Real data pipeline.
- [ ] Time range.
- [ ] Project/agent/provider filters.
- [ ] Animated charts.
- [ ] Count-up KPIs.
- [ ] Data update transitions.
- [ ] Empty states.
- [ ] Partial-data warnings.
- [ ] Export.
- [ ] Performance.
- [ ] Accessibility.

## Motion Requirements

- bars grow from zero;
- lines draw left-to-right;
- donut/pie segments sweep in;
- duration 600–900ms;
- KPI values count up around 800ms;
- value changes animate;
- reduced motion disables nonessential animation.

## Acceptance Criteria

- No hard-coded fake metrics in production.
- Metric definitions are documented.
- Partial or unavailable telemetry is explicit.
- Charts are accessible and readable.

---

# PHASE 17 — Providers

## Objective

Provide a dedicated provider and model control surface.

## Visual Identity

Providers occupy sockets/seats around the system core.

## Tasks

- [ ] Provider list.
- [ ] Provider OFF/ready/degraded/unavailable.
- [ ] Model list.
- [ ] Model capabilities.
- [ ] Local model detection.
- [ ] Default model policy.
- [ ] Per-agent preference.
- [ ] Per-command override where authorized.
- [ ] Credential status without exposing credentials.
- [ ] Health test.
- [ ] Usage and latency.
- [ ] Disable/revoke.
- [ ] Provider audit events.

## Acceptance Criteria

- Provider default OFF.
- UI cannot reveal secrets.
- Model/provider changes rebuild relevant runtime state.
- Disabled provider cannot execute.

---

# PHASE 18 — Notifications

## Objective

Turn raw events into actionable, prioritized operational notifications.

## Types

- approval required;
- task blocked;
- command complete;
- command failed;
- provider unavailable;
- sidecar unavailable;
- receipt invalid;
- automation failed;
- integration revoked;
- memory conflict;
- knowledge stale;
- agent failure.

## Tasks

- [ ] Notification model.
- [ ] Priority.
- [ ] Read/unread.
- [ ] Grouping.
- [ ] Action buttons.
- [ ] Deep links.
- [ ] Persistence.
- [ ] Deduplication.
- [ ] Quiet mode.
- [ ] OS notifications.
- [ ] Security-sensitive redaction.

## Acceptance Criteria

- Notifications link to actual evidence/state.
- Sensitive data is not leaked into OS notifications.
- Duplicate storms are prevented.
- Critical governance failures remain visible.

---

# PHASE 19 — Settings

## Objective

Provide safe configuration without exposing dangerous internals casually.

## Sections

- profile;
- appearance;
- language;
- accessibility;
- runtime;
- providers;
- agents;
- memory;
- knowledge;
- notifications;
- automations;
- integrations;
- privacy;
- security;
- receipts/audit;
- data export;
- backup/recovery;
- developer mode;
- about/version.

## Tasks

- [ ] Token-based settings UI.
- [ ] HY/EN.
- [ ] dark/light.
- [ ] reduced motion.
- [ ] font/scale controls.
- [ ] provider configuration through sidecar.
- [ ] runtime diagnostics.
- [ ] secure reset.
- [ ] export.
- [ ] delete/revoke flows.
- [ ] developer mode warning.
- [ ] version/protocol display.

## Acceptance Criteria

- Dangerous changes require confirmation.
- Secret values are never displayed after save.
- Runtime protocol/version is visible.
- Accessibility settings apply globally.

---

# PHASE 20 — Security and Governance Hardening

## Objective

Verify the entire system against hostile and accidental misuse.

## Threat Areas

- direct provider bypass;
- forged receipt;
- replayed authorization;
- expired lease;
- local IPC abuse;
- malicious frontend;
- compromised integration;
- prompt injection;
- tool injection;
- data exfiltration;
- secret logging;
- path traversal;
- command injection;
- unsafe file handling;
- stale locks;
- interrupted execution;
- fake recovery;
- cross-project access;
- excessive permissions;
- dependency compromise.

## Tasks

- [ ] Threat model.
- [ ] Trust boundary diagram.
- [ ] Abuse cases.
- [ ] Receipt tamper tests.
- [ ] Replay tests.
- [ ] Expiration tests.
- [ ] Sidecar impersonation tests.
- [ ] Unauthorized local client tests.
- [ ] Schema fuzzing.
- [ ] IPC size/rate tests.
- [ ] Secret scanning.
- [ ] Dependency audit.
- [ ] Path/process/network capability tests.
- [ ] Prompt/tool injection tests.
- [ ] Recovery tests.
- [ ] Audit log integrity.
- [ ] Redaction tests.
- [ ] Backup/restore tests.
- [ ] Windows-specific hardening.
- [ ] Linux CI compatibility where applicable.

## Acceptance Criteria

- No known P0/P1 issue remains open.
- All critical invariants are machine-tested.
- Interrupted work cannot produce false success.
- Original state recovery is verified.
- Security documentation matches implementation.

---

# PHASE 21 — Testing Strategy

## Unit Tests

- schemas;
- validators;
- canonical serialization;
- receipt verification;
- authorization decisions;
- provider adapters;
- state reducers;
- UI components;
- formatting and redaction.

## Contract Tests

- desktop ↔ sidecar;
- sidecar ↔ engine;
- sidecar ↔ provider;
- engine ↔ receipt;
- frontend runtime client.

## Integration Tests

- governed command success;
- governance rejection;
- provider unavailable;
- sidecar crash;
- invalid receipt;
- timeout;
- cancellation;
- retry;
- memory recall;
- knowledge retrieval;
- multi-agent handoff.

## End-to-End Tests

- issue command;
- authorize;
- dispatch agents;
- call provider;
- collect evidence;
- sign receipt;
- verify receipt;
- display completion.

## UI Tests

- routing;
- keyboard navigation;
- loading/error/blocked states;
- language switch;
- theme switch;
- reduced motion;
- responsive behavior;
- visual regression;
- no fake success fallback.

## CI Requirements

- Windows green;
- Ubuntu green where supported;
- formatting;
- lint;
- typecheck;
- unit tests;
- contract tests;
- integration tests;
- schema validation;
- secret scan;
- dependency audit;
- build;
- artifact checks.

---

# PHASE 22 — Performance and Reliability

## Targets

- fast shell startup;
- responsive command input;
- smooth agent mesh;
- bounded memory usage;
- no unbounded event history in frontend;
- resilient reconnect;
- safe background processing;
- predictable animations;
- graceful degraded state.

## Tasks

- [ ] Performance budgets.
- [ ] Startup profiling.
- [ ] Mesh rendering profiling.
- [ ] Event batching.
- [ ] Virtualization where appropriate.
- [ ] Lazy route loading.
- [ ] Cache policy.
- [ ] Indexed local storage strategy.
- [ ] Log rotation.
- [ ] Receipt/audit retention.
- [ ] Crash reporting with redaction.
- [ ] Recovery UX.
- [ ] Long-running soak tests.

---

# PHASE 23 — Documentation

## Required Canonical Documents

- [ ] root README;
- [ ] architecture;
- [ ] trust boundaries;
- [ ] engine bridge contract;
- [ ] sidecar design;
- [ ] provider adapter contract;
- [ ] signed receipt specification;
- [ ] UI architecture;
- [ ] design system;
- [ ] agent model;
- [ ] project/task model;
- [ ] memory model;
- [ ] knowledge model;
- [ ] automation model;
- [ ] integration model;
- [ ] testing strategy;
- [ ] security model;
- [ ] operations/runbook;
- [ ] recovery guide;
- [ ] roadmap;
- [ ] changelog;
- [ ] next-chat / handoff state.

Documentation MUST remain bilingual Armenian and English where the repository canon requires bilingual content.

Documentation MUST be updated with implementation, not after the fact.

---

# PHASE 24 — Release Candidate

## Objective

Prepare one independently auditable candidate without merging automatically.

## Tasks

- [ ] Freeze candidate HEAD.
- [ ] Record exact commit SHA.
- [ ] Run full CI.
- [ ] Run full local validation.
- [ ] Run clean install/build.
- [ ] Run E2E governed command.
- [ ] Verify receipts.
- [ ] Verify provider OFF default.
- [ ] Verify no direct frontend provider path.
- [ ] Verify secret scan.
- [ ] Verify recovery.
- [ ] Verify UI routes.
- [ ] Verify HY/EN.
- [ ] Verify dark/light.
- [ ] Verify reduced motion.
- [ ] Capture screenshots/video.
- [ ] Produce release evidence.
- [ ] Produce unresolved limitations.
- [ ] Request independent audit.
- [ ] Wait for Owner approval.

## Final Merge Gate

Only the Owner may approve the exact final candidate HEAD for merge.

Any commit after approval invalidates that approval and requires a new review.

---

# 25. Mandatory Stop Conditions

Claude MUST stop and report clearly when:

1. a security invariant requires weakening;
2. a receipt cannot be made authentic;
3. secrets or issuer keys would need to move into desktop/frontend;
4. direct provider calls appear necessary;
5. canonical documents conflict materially;
6. repository or branch identity is uncertain;
7. destructive migration risks user data;
8. a required external credential or Owner decision is missing;
9. tests reveal a P0/P1 issue that cannot be safely fixed in scope;
10. final candidate approval is required.

Claude MUST NOT stop for:

- routine implementation decisions;
- ordinary refactors;
- normal test failures that can be fixed safely;
- documentation updates;
- expected PR creation;
- routine CI iteration;
- visual polish inside approved direction.

---

# 26. Definition of Done for Every Feature

A feature is done only when:

- implementation exists;
- real state is connected;
- security boundary is preserved;
- loading state exists;
- empty state exists;
- error state exists;
- blocked state exists where relevant;
- keyboard interaction works;
- accessibility is checked;
- HY/EN content is supported where required;
- dark/light behavior is supported;
- reduced motion is supported;
- tests exist;
- CI passes;
- documentation is updated;
- screenshots/evidence are attached;
- no fake production data is used;
- acceptance criteria are satisfied;
- independent review has no unresolved blocker.

---

# 27. Immediate Next Actions

Claude should begin with this exact order:

1. Add this roadmap to the repository root as `MASTER_EXECUTION_ROADMAP.md`.
2. Link it from root `README.md`, `AGENTS.md`, `CLAUDE.md`, or the canonical read manifest as appropriate.
3. Preserve `brops-aios.html` in a stable repository path such as:
   - `design/reference/brops-aios.html`
4. Document that file as the canonical UI interaction reference.
5. Audit the open Phase 1 bridge PR.
6. Correct the false `receipt` contract.
7. Add tests proving the distinction between outcome evidence and authentic signed receipt.
8. Bring Phase 1 CI to green.
9. Leave the PR unmerged for independent review.
10. Continue with Phase 2 sidecar only after the Phase 1 contract is correct.
11. Build runtime foundations before connecting production UI actions.
12. Begin UI foundation in parallel only with clearly mocked development adapters.
13. Never allow UI mock success to enter production behavior.

---

# 28. Required Progress Reporting

At each completed slice, Claude must update:

- current branch;
- current HEAD;
- PR number;
- changed files;
- tests run;
- CI status;
- completed roadmap items;
- open blockers;
- next autonomous step.

Progress reports must distinguish:

- implemented;
- tested;
- verified;
- merged;
- planned.

These words are not interchangeable.

---

# 29. Canonical Outcome

The roadmap is complete only when BroPS operates as one governed AI Agent OS in which:

- Gev can issue commands;
- Bro can orchestrate agents;
- agents can collaborate;
- tasks are governed;
- providers are controlled;
- memory and knowledge are traceable;
- projects preserve context;
- automations are authorized;
- integrations are scoped;
- the UI visibly reflects real runtime state;
- every meaningful execution leaves evidence;
- every governed completion has an authentic verifiable receipt;
- no component lies about what ran or succeeded.

