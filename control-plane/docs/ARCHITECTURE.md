# Architecture

## English

### Ownership

`policy/*.json` owns machine decisions. Each rule has a unique ID, primitive, scope, level, class applicability, expected value/decision rule, approval requirement, enforcement mechanism, and source sections. A primitive has exactly one owning rule. Shared Git, merge and security primitives are referenced by class applicability rather than redefined per class.

`policy/manifest.json` records owner, version, effective date, source checksum, canonical inventory, file digests and all 30 section mappings. `docs/POLICY.md` is generated; the original document is an immutable provenance artifact. A coverage mapping verifies structural completeness and source integrity, not a mathematical proof of semantic equivalence. Owner review remains essential for policy changes.

### Two immutable revisions

The policy snapshot commit is recorded in each registration and lock. `policy-snapshot.json` binds that commit to the distributed machine files. In a Git checkout the validator also compares those files directly to the pinned Git objects.

The executable action/workflow revision is a separate full commit SHA. It contains the validator, dependencies and trusted registry. Separating these revisions avoids embedding a commit's own SHA inside itself. A private composite action is downloaded by GitHub's action service, which makes cross-repository use possible without creating a PAT or pretending the caller's token can clone another private repository.

Future registry changes require a new reviewed executable snapshot. The caller must pin a revision containing its approved registration; it cannot register itself in a caller-local file. Update the workflow pin deliberately after green CI. Never resolve a moving branch as an unreviewed runtime dependency.

### Runtime

- `housenet/control.py`: the single validator implementation.
- `bin/validate-control-plane`: offline policy, registry, template and self-validation.
- `bin/validate-repository`: caller lock, trusted registration, applicable file/content/workflow checks.
- `bin/housenet-preflight`: adds live identity, remote, local Git settings, clean checkout and remote-main freshness.
- Root `action.yml`: immutable composite gate; installs hash-locked parser dependencies in a temporary isolated environment and validates caller content.
- Reusable workflow: checks out caller content with read-only credentials, then invokes the pinned composite action. It never runs caller-provided validator code.

### Trust boundaries

A caller cannot supply the authoritative registry or expected repository name. GitHub supplies the caller context. Registry approval records are auditable assertions tied to owner review, not cryptographic proof that the owner approved a specific change. A person who can change the trusted validator can change enforcement; protect its branch where the plan supports it.

The content validator checks known dangerous patterns. It cannot prove that arbitrary shell code is safe, detect all secrets, or replace deployment review. Third-party dependency review and policy exceptions remain explicit decisions.

---

## Հայերեն

# Ճարտարապետություն

`policy/*.json`-ը պահում է մեքենայական որոշումները։ Յուրաքանչյուր կանոն ունի եզակի ID, տիրույթ, մակարդակ, դասերի կիրառելիություն, ակնկալվող որոշում, հաստատման պահանջ և enforcement-ի եղանակ։ `policy/manifest.json`-ը գրանցում է տարբերակը, աղբյուրի checksum-ը, ֆայլերի ցանկը և բաժինների ծածկույթը։ `docs/POLICY.md`-ը ստեղծված մարդկային ներկայացումն է, իսկ սկզբնական փաստաթուղթը մնում է անփոփոխ provenance աղբյուր։

Policy snapshot-ը և executable gate-ի revision-ը առանձին immutable հղումներ են։ Gate-ը ստուգում է caller-ի namespace-ը, registry-ն, ֆայլերը, workflow-ները և երկլեզու փաստաթղթերը։ Այս control plane-ը չի ապացուցում shell code-ի անվտանգությունը, բոլոր գաղտնիքների բացակայությունը կամ մարդու հաստատման մտադրությունը։
