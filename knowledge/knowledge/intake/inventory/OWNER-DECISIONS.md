## English

# Knowledge migration owner decisions

This packet is intentionally compact. Machine review preceded it; no source is promoted to canonical by this document.

## Decision 01 — `provider-specific execution documentation / Activation-inputs.md`

**Found:** execution/session input documentation owned by Command Center. It is implementation context, not durable business knowledge.

**Why owner input:** confirm whether any durable operational concept should be extracted later; the file itself should not become a Knowledge authority.

**Recommendation:** `REJECT FROM KNOWLEDGE` and retain under Command Center.

**Options:** A) reject from Knowledge (recommended); B) place a future extracted concept in intake after semantic review.

**Consequences:** A preserves single ownership; B requires a later concept-level extraction with provenance.

## Decision 02 — `provider-specific migration log` and `registry audit evidence`

**Found:** migration/audit evidence tied to a historical implementation event, not current business truth.

**Why owner input:** decide whether the evidence has continuing audit value after the migration record is closed.

**Recommendation:** `HISTORICAL / REJECT FROM CANONICAL KNOWLEDGE` (recommended).

**Options:** A) retain as Command Center historical evidence (recommended); B) preserve a metadata-only reference in Knowledge intake.

**Consequences:** A avoids duplicating audit authority; B improves discovery but must remain explicitly historical.

## Decision 03 — Remaining source families

**Found:** Office files are pointer snapshots whose contents are unavailable in this workspace; active/reference Markdown and chat exports contain operational claims, questions, and potentially sensitive business context.

**Why owner input:** promotion requires confirmed currentness, sensitivity, business owner and contradiction resolution.

**Recommendation:** keep as `BLOCKED_SOURCE_SNAPSHOT` or `INTAKE / NEEDS REVIEW`; do not canonicalize yet.

**Options:** A) continue conservative intake (recommended); B) provide accessible originals and owner/domain decisions for a later concept-level normalization pass.

**Consequences:** A preserves evidence and avoids false facts; B enables migration after source integrity and ownership are verified.

## Հայերեն

Այս compact decision packet-ը ներկայացնում է machine review-ից հետո մնացած երեք owner որոշումները։ Աղբյուրները canonical Knowledge չեն դարձել․ պահպանվում են ownership, provenance և reversible intake սահմանները։
