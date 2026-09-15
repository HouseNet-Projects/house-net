# HouseNet policy · 1.4.2 <!-- housenet-version: policy_version -->

## English

Generated from machine authority. Do not edit by hand. Original approved text is preserved in [source](source/HouseNet-GitHub-Policy-v1.0.md).

### HN-ARCH-AI-PROVIDER-INDEPENDENCE · architecture.ai_provider_independence

MANDATORY · repository · Classes A, B, C

```json
{
  "build_time_agent_is_not_runtime_dependency": true,
  "runtime_ai_requires": [
    "registered_external_dependency",
    "explicit_owner_approval",
    "business_justification",
    "fallback_or_outage_impact"
  ],
  "unapproved_provider_credentials_in_ci_or_deployment": "forbidden"
}
```

Approval: explicit_owner. Enforcement: dependency_registry_and_deterministic_gate. Source sections: .

### HN-AUTHOR-EMAIL · git.user.email

MANDATORY · environment · Classes A, B, C

```json
"329470240+HouseNet-Projects@users.noreply.github.com"
```

Approval: explicit_owner. Enforcement: preflight. Source sections: 12.

### HN-AUTHOR-NAME · git.user.name

MANDATORY · environment · Classes A, B, C

```json
"ohanyan"
```

Approval: explicit_owner. Enforcement: preflight. Source sections: 12.

### HN-BRANCH · git.default_branch

MANDATORY · repository · Classes A, B, C

```json
"main"
```

Approval: explicit_owner. Enforcement: repository_settings_audit. Source sections: 8.

### HN-BRANCH-NAMES · git.branch_names

RECOMMENDED · repository · Classes A, B, C

```json
[
  "feat/",
  "fix/",
  "chore/",
  "docs/",
  "refactor/"
]
```

Approval: explicit_owner. Enforcement: owner_review. Source sections: 8.

### HN-CI · actions.ci

MANDATORY · repository · Classes A, B, C

```json
{
  "purpose": "real_failure_modes",
  "required_checks": "only_stable_meaningful_checks",
  "examples": [
    "tests",
    "lint",
    "types",
    "build",
    "schema",
    "migrations",
    "packaging",
    "deployment_validation"
  ]
}
```

Approval: explicit_owner. Enforcement: owner_review. Source sections: 15.

### HN-CLASS-A · classification.A

MANDATORY · repository · Classes A

```json
{
  "name": "CRITICAL",
  "triggers": [
    "production",
    "customer_data",
    "billing",
    "authentication",
    "infrastructure",
    "privileged_integration",
    "deployment_control",
    "secrets",
    "high_impact"
  ],
  "required_files": [
    "README.md"
  ],
  "ci": "required_meaningful",
  "protection": "strongest_supported",
  "conditional_files": {
    "SECURITY.md": "meaningful_security_reporting",
    "PR_template": "recurring_risk_review",
    "CODEOWNERS": "multiple_responsible_people"
  },
  "deployment": "explicit_design_and_approval",
  "rollback": "document_where_applicable",
  "releases": "when_production_releases_exist"
}
```

Approval: explicit_owner. Enforcement: repository_validator. Source sections: 5.

### HN-CLASS-B · classification.B

MANDATORY · repository · Classes B

```json
{
  "name": "STANDARD",
  "triggers": [
    "maintained_software",
    "api",
    "dashboard",
    "analytics",
    "internal_service",
    "automation",
    "integration"
  ],
  "required_files": [
    "README.md",
    ".gitignore",
    ".editorconfig",
    ".gitattributes"
  ],
  "ci": "only_meaningful_checks",
  "protection": "important_repositories_where_supported",
  "conditional_files": {},
  "deployment": "repository_specific",
  "rollback": "when_applicable",
  "releases": "when_lifecycle_exists"
}
```

Approval: explicit_owner. Enforcement: repository_validator. Source sections: 5.

### HN-CLASS-C · classification.C

MANDATORY · repository · Classes C

```json
{
  "name": "LIGHTWEIGHT",
  "triggers": [
    "documentation",
    "low_risk_utility",
    "experiment",
    "prototype",
    "approved_reference_data"
  ],
  "required_files": [
    "README.md"
  ],
  "ci": "none_unless_justified",
  "protection": "optional_proportional",
  "conditional_files": {
    ".gitignore": "when_relevant"
  },
  "deployment": "none_unless_justified",
  "rollback": "when_applicable",
  "releases": "not_forced"
}
```

Approval: explicit_owner. Enforcement: repository_validator. Source sections: 5.

### HN-CLASSIFICATION · repository.classification

MANDATORY · repository · Classes A, B, C

```json
{
  "required_before_creation": true,
  "allowed": [
    "A",
    "B",
    "C"
  ]
}
```

Approval: explicit_owner. Enforcement: repository_validator. Source sections: 5.

### HN-COMMITS · git.commit_messages

RECOMMENDED · repository · Classes A, B, C

```json
{
  "meaningful": true,
  "suggested_prefixes": [
    "feat",
    "fix",
    "docs",
    "chore"
  ],
  "avoid": [
    "update",
    "stuff",
    "final",
    "changes2"
  ]
}
```

Approval: explicit_owner. Enforcement: owner_review. Source sections: 23.

### HN-CONFIGURATION · github.configuration_change

MANDATORY · account · Classes A, B, C

```json
{
  "requires": "explicit_owner_approval",
  "silence_is_approval": false
}
```

Approval: explicit_owner. Enforcement: owner_review. Source sections: 2.

### HN-CREATE · repository.creation_baseline

MANDATORY · repository · Classes A, B, C

```json
{
  "owner": "HouseNet-Projects",
  "visibility": "private",
  "default_branch": "main",
  "automatic_import": false,
  "automatic_framework": false,
  "automatic_license": false,
  "proposal_fields": [
    "name",
    "purpose",
    "separate_repository_justification",
    "classification",
    "technology",
    "ci_requirement",
    "deployment_model",
    "data_sensitivity",
    "baseline"
  ],
  "then": "wait_for_owner"
}
```

Approval: explicit_owner. Enforcement: owner_review. Source sections: 4.

### HN-CREATION · repository.creation

MANDATORY · repository · Classes A, B, C

```json
{
  "requires": "explicit_owner_instruction",
  "recommendation_is_not_approval": true
}
```

Approval: explicit_owner. Enforcement: registry_and_owner_review. Source sections: 2.

### HN-DATA-CLASSIFICATION · repository.data_classification

MANDATORY · repository · Classes A, B, C

```json
{
  "levels": [
    "PUBLIC",
    "INTERNAL",
    "CONFIDENTIAL",
    "RESTRICTED"
  ],
  "independent_of_operational_class": true,
  "unknown_requires_owner_decision": true
}
```

Approval: explicit_owner. Enforcement: registration_schema_and_owner_review. Source sections: .

### HN-DEPENDENCIES · security.dependencies

MANDATORY · repository · Classes A, B, C

```json
{
  "dependency_graph": true,
  "dependabot_alerts": true,
  "security_updates": true,
  "when": "available_and_applicable",
  "version_updates": "real_ecosystem_only",
  "cadence": "weekly",
  "auto_merge": "separate_explicit_automation_approval"
}
```

Approval: explicit_owner. Enforcement: repository_validator. Source sections: 17.

### HN-DEPLOYMENT · actions.deployment

REPO_SPECIFIC · repository · Classes A, B, C

```json
{
  "A": {
    "explicit_design": [
      "environment",
      "credentials",
      "approval",
      "trigger",
      "rollback",
      "auditability"
    ],
    "production_automation": "explicit_owner_approval"
  },
  "B": "repository_specific",
  "C": "none_unless_justified"
}
```

Approval: explicit_owner. Enforcement: registration_and_owner_review. Source sections: 16.

### HN-DEPRECATION · repository.deprecation

MANDATORY · repository · Classes A, B, C

```json
{
  "approval": "explicit_owner",
  "document_when_applicable": [
    "status",
    "replacement",
    "migration_path",
    "last_supported_version"
  ],
  "preserve_history": true
}
```

Approval: explicit_owner. Enforcement: owner_review. Source sections: 26.

### HN-DESIGN-SYSTEM-ADOPTION · repository.design_system_adoption

MANDATORY · repository · Classes A, B, C

```json
{
  "contract": "required",
  "version": "certified_design_system_release",
  "category": "registered_visual_repository_category",
  "asset_source": "HouseNet-owned_design_system",
  "readme": "bilingual_status_navigation",
  "human_docs": "en_hy_required",
  "social_preview": "present_or_justified_exemption"
}
```

Approval: explicit_owner. Enforcement: registration_schema_and_repository_validator. Source sections: .

### HN-DESTRUCTIVE · operation.destructive

MANDATORY · repository · Classes A, B, C

```json
{
  "requires": "exact_owner_approval",
  "actions": [
    "repository_delete",
    "repository_archive",
    "important_branch_delete",
    "force_push",
    "shared_history_rewrite",
    "visibility_change",
    "credential_change",
    "authentication_change",
    "token_create_or_revoke",
    "secret_rotate_or_remove",
    "destructive_migration",
    "release_or_tag_delete",
    "destructive_environment_change"
  ],
  "remediation": "report_before_acting"
}
```

Approval: exact_owner. Enforcement: owner_review. Source sections: 3.

### HN-DEVELOPMENT · git.development_flow

MANDATORY · repository · Classes A, B, C

```json
[
  "branch",
  "change",
  "test",
  "PR",
  "merge"
]
```

Approval: explicit_owner. Enforcement: owner_review. Source sections: 8.

### HN-DOC-HUMAN-VISIBLE-BILINGUAL · documentation.human_visible_bilingual

MANDATORY · repository · Classes A, B, C

```json
{
  "human_facing": true,
  "required_languages": [
    "en",
    "hy"
  ],
  "contract": "English and Հայերեն sections are both non-empty",
  "classification": "deterministic_path_and_marker_convention"
}
```

Approval: explicit_owner. Enforcement: bilingual_document_validator. Source sections: .

### HN-EXPLICIT-IDENTITY · git.user.useConfigOnly

MANDATORY · environment · Classes A, B, C

```json
"true"
```

Approval: explicit_owner. Enforcement: preflight. Source sections: 12.

### HN-FILES · repository.files

RECOMMENDED · repository · Classes A, B, C

```json
{
  "normal_code": [
    "README.md",
    ".gitignore",
    ".editorconfig",
    ".gitattributes"
  ],
  "readme": [
    "purpose",
    "setup",
    "run",
    "tests",
    "ownership"
  ]
}
```

Approval: explicit_owner. Enforcement: repository_validator. Source sections: 19.

### HN-GOVERNANCE · repository.governance_files

REPO_SPECIFIC · repository · Classes A, B, C

```json
{
  "only_when_justified": [
    "SECURITY.md",
    "CONTRIBUTING.md",
    "CODEOWNERS",
    "issue_templates",
    "PR_template",
    "dependabot.yml",
    ".github/workflows",
    "architecture_docs",
    "release_docs"
  ],
  "mechanical_scaffolding": false
}
```

Approval: explicit_owner. Enforcement: registration_and_owner_review. Source sections: 20.

### HN-IDENTITY · github.identity

MANDATORY · environment · Classes A, B, C

```json
"HouseNet-Projects"
```

Approval: explicit_owner. Enforcement: preflight. Source sections: 2.

### HN-INIT-BRANCH · git.init.defaultBranch

MANDATORY · environment · Classes A, B, C

```json
"main"
```

Approval: explicit_owner. Enforcement: preflight. Source sections: 12.

### HN-LEVELS · policy.levels

MANDATORY · control_plane · Classes A, B, C

```json
{
  "MANDATORY": "owner_override_only",
  "RECOMMENDED": "preferred_unless_justified",
  "REPO_SPECIFIC": "purpose_class_technology_risk_deployment_sensitivity",
  "missing_context": "ask_or_recommend"
}
```

Approval: explicit_owner. Enforcement: schema_validator. Source sections: 28.

### HN-LICENSE · repository.license

MANDATORY · repository · Classes A, B, C

```json
{
  "automatic_open_source": false,
  "public_transition": "separate_license_review"
}
```

Approval: explicit_owner. Enforcement: repository_validator. Source sections: 21.

### HN-METHODS · merge.methods

RECOMMENDED · repository · Classes A, B, C

```json
{
  "squash": true,
  "merge_commit": false,
  "rebase": false,
  "auto_merge": false,
  "delete_merged_working_branches": true,
  "exception": "owner_approved_architectural_reason"
}
```

Approval: explicit_owner. Enforcement: repository_settings_audit. Source sections: 11.

### HN-MIGRATION-STAGED-ADOPTION · migration.lifecycle

MANDATORY · repository · Classes A, B, C

```json
{
  "stages": [
    "DISCOVERED",
    "QUARANTINED",
    "AUDITED",
    "PROPOSED",
    "OWNER_APPROVED",
    "MIGRATED",
    "CERTIFIED",
    "CANONICAL"
  ],
  "direct_legacy_to_canonical": false,
  "destructive_cleanup_during_intake": false
}
```

Approval: explicit_owner. Enforcement: migration_registry_and_import_validator. Source sections: .

### HN-NAMESPACE · github.namespace

MANDATORY · repository · Classes A, B, C

```json
"HouseNet-Projects"
```

Approval: explicit_owner. Enforcement: repository_validator. Source sections: 2.

### HN-NAMING · repository.naming

MANDATORY · repository · Classes A, B, C

```json
{
  "format": "^house-net-[a-z0-9]+(?:-[a-z0-9]+)*$",
  "avoid": [
    "final",
    "final-v2",
    "test123",
    "new-project",
    "stuff"
  ],
  "exception": "justified_product_convention",
  "exceptions": [
    ".github",
    "account-profile"
  ]
}
```

Approval: explicit_owner. Enforcement: repository_registration_schema_and_validator. Source sections: 7.

### HN-OPERATING-FLOW · engineering.operating_flow

MANDATORY · environment · Classes A, B, C

```json
[
  "verify_identity",
  "read",
  "understand",
  "classify",
  "recommend",
  "owner_ok",
  "execute",
  "verify",
  "report"
]
```

Approval: explicit_owner. Enforcement: owner_review. Source sections: 29.

### HN-OUT-OF-SCOPE · engineering.out_of_scope

MANDATORY · environment · Classes A, B, C

```json
{
  "report": true,
  "apply": false
}
```

Approval: explicit_owner. Enforcement: owner_review. Source sections: 29.

### HN-PERMISSIONS · actions.permissions

MANDATORY · repository · Classes A, B, C

```json
{
  "default": "read",
  "broad_write": false,
  "job_permissions": "minimum_required",
  "enable_only_when_useful": true
}
```

Approval: explicit_owner. Enforcement: workflow_validator. Source sections: 13.

### HN-PERSON-INDEPENDENT-AUTHORITY · architecture.person_independent_authority

MANDATORY · repository · Classes A, B, C

```json
{
  "machine_authority_uses": [
    "OWNER",
    "AUTHORIZED_OWNER",
    "HOUSE_NET_OWNER",
    "stable_principal_id"
  ],
  "display_names_optional": true,
  "historical_evidence_exempt": true,
  "literal_person_names_as_machine_keys": "forbidden"
}
```

Approval: explicit_owner. Enforcement: registration_schema_and_target_validator. Source sections: .

### HN-PROPORTIONALITY · engineering.proportionality

MANDATORY · environment · Classes A, B, C

```json
{
  "qualities": [
    "simple",
    "private",
    "secure",
    "auditable",
    "reproducible",
    "intentional"
  ],
  "maximize_configuration": false
}
```

Approval: explicit_owner. Enforcement: owner_review. Source sections: 30.

### HN-PROTECTION · merge.protection

MANDATORY · repository · Classes A, B, C

```json
{
  "A": "strongest_practical_supported",
  "B": "important_repositories_where_supported",
  "C": "optional_proportional",
  "main": [
    "pull_request",
    "stable_required_checks",
    "block_force_push",
    "block_deletion",
    "resolve_conversations",
    "linear_history_where_appropriate",
    "no_permanent_bypass"
  ],
  "invent_checks": false
}
```

Approval: explicit_owner. Enforcement: repository_settings_audit. Source sections: 9.

### HN-PRS · repository.pull_requests

RECOMMENDED · repository · Classes A, B, C

```json
{
  "answer": [
    "what",
    "why",
    "verification"
  ],
  "risky_add": [
    "risk",
    "rollback"
  ],
  "excessive_paperwork": false
}
```

Approval: explicit_owner. Enforcement: owner_review. Source sections: 24.

### HN-PULL · git.pull.ff

MANDATORY · environment · Classes A, B, C

```json
"only"
```

Approval: explicit_owner. Enforcement: preflight. Source sections: 12.

### HN-PURPOSE · engineering.purpose

MANDATORY · environment · Classes A, B, C

```json
{
  "principle": "Minimum correct configuration for actual risk and purpose; every primitive must have a real purpose."
}
```

Approval: explicit_owner. Enforcement: owner_review. Source sections: 1.

### HN-RECLASSIFY · repository.reclassification

MANDATORY · repository · Classes A, B, C

```json
{
  "requires": "explicit_owner_approval",
  "automatic_governance_change": false
}
```

Approval: explicit_owner. Enforcement: owner_review. Source sections: 6.

### HN-REVIEW · merge.review

MANDATORY · repository · Classes A, B, C

```json
{
  "single_identity_required_approvals": 0,
  "independent_approval_requires_additional_human": "recommend_when_introduced",
  "impossible_requirements": false
}
```

Approval: explicit_owner. Enforcement: owner_review. Source sections: 10.

### HN-SCOPE · engineering.scope

MANDATORY · repository · Classes A, B, C

```json
{
  "clear_purpose": true,
  "unrelated_functionality": false,
  "restructure": "recommend_then_owner_approval"
}
```

Approval: explicit_owner. Enforcement: owner_review. Source sections: 25.

### HN-SECRETS · security.secrets

MANDATORY · repository · Classes A, B, C

```json
{
  "git_history": false,
  "hardcoded": false,
  "storage": [
    "GitHub Secrets",
    "environment secrets",
    "approved external manager",
    "ignored local environment files"
  ],
  "incident": [
    "stop",
    "report_repository_and_secret_identifier_without_value",
    "report_exposure",
    "propose_remediation"
  ],
  "rotation_or_history_rewrite": "exact_owner_approval"
}
```

Approval: explicit_owner. Enforcement: content_scan_and_owner_review. Source sections: 18.

### HN-SIGNAL · notifications.delivery

MANDATORY · account · Classes A, B, C

```json
{
  "wanted": [
    "security_alerts",
    "failed_actions",
    "direct_mentions",
    "participating_conversations"
  ],
  "avoid": [
    "all_activity",
    "every_push",
    "unnecessary_watching",
    "noisy_digests",
    "spam"
  ]
}
```

Approval: explicit_owner. Enforcement: owner_review. Source sections: 27.

### HN-SOURCE-OF-TRUTH · migration.source_of_truth

MANDATORY · repository · Classes A, B, C

```json
{
  "one_canonical_source": true,
  "conflicting_candidates": "block_canonicalization",
  "legacy_preserved": true
}
```

Approval: explicit_owner. Enforcement: migration_evidence_and_validator. Source sections: .

### HN-SOURCES · actions.sources

MANDATORY · repository · Classes A, B, C

```json
{
  "official": [
    "actions/*"
  ],
  "housenet": "HouseNet-Projects/*",
  "third_party": "reviewed_trusted_and_justified",
  "important_workflows": "prefer_full_commit_sha",
  "read_only_due_diligence": "allowed_for_required_dependency_verification",
  "external_mutations": false
}
```

Approval: explicit_owner. Enforcement: workflow_validator. Source sections: 14.

### HN-VERSION-SINGLE-SOURCE · repository.version_single_source

MANDATORY · repository · Classes A, B, C

```json
{
  "when": "versioned=true",
  "canonical_source": "one_registered_machine_readable_source",
  "preferred_path": "release/manifest.json",
  "version_scheme": "MAJOR.MINOR.PATCH",
  "surface_registry": "required",
  "derived_surfaces": "generated_or_validated",
  "drift": "ci_failure",
  "consumer_versions": "explicit_and_distinct_from_own_version"
}
```

Approval: explicit_owner. Enforcement: repository_validator_and_ci. Source sections: .

### HN-VERSIONING · repository.versioning

RECOMMENDED · repository · Classes A, B, C

```json
{
  "when": "real_release_lifecycle",
  "preferred": "SemVer vX.Y.Z",
  "mandatory_for_notes_or_experiments": false
}
```

Approval: explicit_owner. Enforcement: owner_review. Source sections: 22.

---

## Հայերեն

# HouseNet-ի քաղաքականություն · 1.4.2

Մեքենայական հեղինակությունից ստեղծված ներկայացում է։ Խմբագրել միայն մեքենայական կանոնները։ Սկզբնական հաստատված քաղաքականությունը պահպանված է [աղբյուրում](source/HouseNet-GitHub-Policy-v1.0.md)։

### HN-ARCH-AI-PROVIDER-INDEPENDENCE · architecture.ai_provider_independence

Մակարդակ՝ MANDATORY · Տիրույթ՝ repository · Դասեր՝ A, B, C

```json
{
  "build_time_agent_is_not_runtime_dependency": true,
  "runtime_ai_requires": [
    "registered_external_dependency",
    "explicit_owner_approval",
    "business_justification",
    "fallback_or_outage_impact"
  ],
  "unapproved_provider_credentials_in_ci_or_deployment": "forbidden"
}
```

Հաստատում՝ explicit_owner։ Կիրարկում՝ dependency_registry_and_deterministic_gate։ Աղբյուրի բաժիններ՝ ։

### HN-AUTHOR-EMAIL · git.user.email

Մակարդակ՝ MANDATORY · Տիրույթ՝ environment · Դասեր՝ A, B, C

```json
"329470240+HouseNet-Projects@users.noreply.github.com"
```

Հաստատում՝ explicit_owner։ Կիրարկում՝ preflight։ Աղբյուրի բաժիններ՝ 12։

### HN-AUTHOR-NAME · git.user.name

Մակարդակ՝ MANDATORY · Տիրույթ՝ environment · Դասեր՝ A, B, C

```json
"ohanyan"
```

Հաստատում՝ explicit_owner։ Կիրարկում՝ preflight։ Աղբյուրի բաժիններ՝ 12։

### HN-BRANCH · git.default_branch

Մակարդակ՝ MANDATORY · Տիրույթ՝ repository · Դասեր՝ A, B, C

```json
"main"
```

Հաստատում՝ explicit_owner։ Կիրարկում՝ repository_settings_audit։ Աղբյուրի բաժիններ՝ 8։

### HN-BRANCH-NAMES · git.branch_names

Մակարդակ՝ RECOMMENDED · Տիրույթ՝ repository · Դասեր՝ A, B, C

```json
[
  "feat/",
  "fix/",
  "chore/",
  "docs/",
  "refactor/"
]
```

Հաստատում՝ explicit_owner։ Կիրարկում՝ owner_review։ Աղբյուրի բաժիններ՝ 8։

### HN-CI · actions.ci

Մակարդակ՝ MANDATORY · Տիրույթ՝ repository · Դասեր՝ A, B, C

```json
{
  "purpose": "real_failure_modes",
  "required_checks": "only_stable_meaningful_checks",
  "examples": [
    "tests",
    "lint",
    "types",
    "build",
    "schema",
    "migrations",
    "packaging",
    "deployment_validation"
  ]
}
```

Հաստատում՝ explicit_owner։ Կիրարկում՝ owner_review։ Աղբյուրի բաժիններ՝ 15։

### HN-CLASS-A · classification.A

Մակարդակ՝ MANDATORY · Տիրույթ՝ repository · Դասեր՝ A

```json
{
  "name": "CRITICAL",
  "triggers": [
    "production",
    "customer_data",
    "billing",
    "authentication",
    "infrastructure",
    "privileged_integration",
    "deployment_control",
    "secrets",
    "high_impact"
  ],
  "required_files": [
    "README.md"
  ],
  "ci": "required_meaningful",
  "protection": "strongest_supported",
  "conditional_files": {
    "SECURITY.md": "meaningful_security_reporting",
    "PR_template": "recurring_risk_review",
    "CODEOWNERS": "multiple_responsible_people"
  },
  "deployment": "explicit_design_and_approval",
  "rollback": "document_where_applicable",
  "releases": "when_production_releases_exist"
}
```

Հաստատում՝ explicit_owner։ Կիրարկում՝ repository_validator։ Աղբյուրի բաժիններ՝ 5։

### HN-CLASS-B · classification.B

Մակարդակ՝ MANDATORY · Տիրույթ՝ repository · Դասեր՝ B

```json
{
  "name": "STANDARD",
  "triggers": [
    "maintained_software",
    "api",
    "dashboard",
    "analytics",
    "internal_service",
    "automation",
    "integration"
  ],
  "required_files": [
    "README.md",
    ".gitignore",
    ".editorconfig",
    ".gitattributes"
  ],
  "ci": "only_meaningful_checks",
  "protection": "important_repositories_where_supported",
  "conditional_files": {},
  "deployment": "repository_specific",
  "rollback": "when_applicable",
  "releases": "when_lifecycle_exists"
}
```

Հաստատում՝ explicit_owner։ Կիրարկում՝ repository_validator։ Աղբյուրի բաժիններ՝ 5։

### HN-CLASS-C · classification.C

Մակարդակ՝ MANDATORY · Տիրույթ՝ repository · Դասեր՝ C

```json
{
  "name": "LIGHTWEIGHT",
  "triggers": [
    "documentation",
    "low_risk_utility",
    "experiment",
    "prototype",
    "approved_reference_data"
  ],
  "required_files": [
    "README.md"
  ],
  "ci": "none_unless_justified",
  "protection": "optional_proportional",
  "conditional_files": {
    ".gitignore": "when_relevant"
  },
  "deployment": "none_unless_justified",
  "rollback": "when_applicable",
  "releases": "not_forced"
}
```

Հաստատում՝ explicit_owner։ Կիրարկում՝ repository_validator։ Աղբյուրի բաժիններ՝ 5։

### HN-CLASSIFICATION · repository.classification

Մակարդակ՝ MANDATORY · Տիրույթ՝ repository · Դասեր՝ A, B, C

```json
{
  "required_before_creation": true,
  "allowed": [
    "A",
    "B",
    "C"
  ]
}
```

Հաստատում՝ explicit_owner։ Կիրարկում՝ repository_validator։ Աղբյուրի բաժիններ՝ 5։

### HN-COMMITS · git.commit_messages

Մակարդակ՝ RECOMMENDED · Տիրույթ՝ repository · Դասեր՝ A, B, C

```json
{
  "meaningful": true,
  "suggested_prefixes": [
    "feat",
    "fix",
    "docs",
    "chore"
  ],
  "avoid": [
    "update",
    "stuff",
    "final",
    "changes2"
  ]
}
```

Հաստատում՝ explicit_owner։ Կիրարկում՝ owner_review։ Աղբյուրի բաժիններ՝ 23։

### HN-CONFIGURATION · github.configuration_change

Մակարդակ՝ MANDATORY · Տիրույթ՝ account · Դասեր՝ A, B, C

```json
{
  "requires": "explicit_owner_approval",
  "silence_is_approval": false
}
```

Հաստատում՝ explicit_owner։ Կիրարկում՝ owner_review։ Աղբյուրի բաժիններ՝ 2։

### HN-CREATE · repository.creation_baseline

Մակարդակ՝ MANDATORY · Տիրույթ՝ repository · Դասեր՝ A, B, C

```json
{
  "owner": "HouseNet-Projects",
  "visibility": "private",
  "default_branch": "main",
  "automatic_import": false,
  "automatic_framework": false,
  "automatic_license": false,
  "proposal_fields": [
    "name",
    "purpose",
    "separate_repository_justification",
    "classification",
    "technology",
    "ci_requirement",
    "deployment_model",
    "data_sensitivity",
    "baseline"
  ],
  "then": "wait_for_owner"
}
```

Հաստատում՝ explicit_owner։ Կիրարկում՝ owner_review։ Աղբյուրի բաժիններ՝ 4։

### HN-CREATION · repository.creation

Մակարդակ՝ MANDATORY · Տիրույթ՝ repository · Դասեր՝ A, B, C

```json
{
  "requires": "explicit_owner_instruction",
  "recommendation_is_not_approval": true
}
```

Հաստատում՝ explicit_owner։ Կիրարկում՝ registry_and_owner_review։ Աղբյուրի բաժիններ՝ 2։

### HN-DATA-CLASSIFICATION · repository.data_classification

Մակարդակ՝ MANDATORY · Տիրույթ՝ repository · Դասեր՝ A, B, C

```json
{
  "levels": [
    "PUBLIC",
    "INTERNAL",
    "CONFIDENTIAL",
    "RESTRICTED"
  ],
  "independent_of_operational_class": true,
  "unknown_requires_owner_decision": true
}
```

Հաստատում՝ explicit_owner։ Կիրարկում՝ registration_schema_and_owner_review։ Աղբյուրի բաժիններ՝ ։

### HN-DEPENDENCIES · security.dependencies

Մակարդակ՝ MANDATORY · Տիրույթ՝ repository · Դասեր՝ A, B, C

```json
{
  "dependency_graph": true,
  "dependabot_alerts": true,
  "security_updates": true,
  "when": "available_and_applicable",
  "version_updates": "real_ecosystem_only",
  "cadence": "weekly",
  "auto_merge": "separate_explicit_automation_approval"
}
```

Հաստատում՝ explicit_owner։ Կիրարկում՝ repository_validator։ Աղբյուրի բաժիններ՝ 17։

### HN-DEPLOYMENT · actions.deployment

Մակարդակ՝ REPO_SPECIFIC · Տիրույթ՝ repository · Դասեր՝ A, B, C

```json
{
  "A": {
    "explicit_design": [
      "environment",
      "credentials",
      "approval",
      "trigger",
      "rollback",
      "auditability"
    ],
    "production_automation": "explicit_owner_approval"
  },
  "B": "repository_specific",
  "C": "none_unless_justified"
}
```

Հաստատում՝ explicit_owner։ Կիրարկում՝ registration_and_owner_review։ Աղբյուրի բաժիններ՝ 16։

### HN-DEPRECATION · repository.deprecation

Մակարդակ՝ MANDATORY · Տիրույթ՝ repository · Դասեր՝ A, B, C

```json
{
  "approval": "explicit_owner",
  "document_when_applicable": [
    "status",
    "replacement",
    "migration_path",
    "last_supported_version"
  ],
  "preserve_history": true
}
```

Հաստատում՝ explicit_owner։ Կիրարկում՝ owner_review։ Աղբյուրի բաժիններ՝ 26։

### HN-DESIGN-SYSTEM-ADOPTION · repository.design_system_adoption

Մակարդակ՝ MANDATORY · Տիրույթ՝ repository · Դասեր՝ A, B, C

```json
{
  "contract": "required",
  "version": "certified_design_system_release",
  "category": "registered_visual_repository_category",
  "asset_source": "HouseNet-owned_design_system",
  "readme": "bilingual_status_navigation",
  "human_docs": "en_hy_required",
  "social_preview": "present_or_justified_exemption"
}
```

Հաստատում՝ explicit_owner։ Կիրարկում՝ registration_schema_and_repository_validator։ Աղբյուրի բաժիններ՝ ։

### HN-DESTRUCTIVE · operation.destructive

Մակարդակ՝ MANDATORY · Տիրույթ՝ repository · Դասեր՝ A, B, C

```json
{
  "requires": "exact_owner_approval",
  "actions": [
    "repository_delete",
    "repository_archive",
    "important_branch_delete",
    "force_push",
    "shared_history_rewrite",
    "visibility_change",
    "credential_change",
    "authentication_change",
    "token_create_or_revoke",
    "secret_rotate_or_remove",
    "destructive_migration",
    "release_or_tag_delete",
    "destructive_environment_change"
  ],
  "remediation": "report_before_acting"
}
```

Հաստատում՝ exact_owner։ Կիրարկում՝ owner_review։ Աղբյուրի բաժիններ՝ 3։

### HN-DEVELOPMENT · git.development_flow

Մակարդակ՝ MANDATORY · Տիրույթ՝ repository · Դասեր՝ A, B, C

```json
[
  "branch",
  "change",
  "test",
  "PR",
  "merge"
]
```

Հաստատում՝ explicit_owner։ Կիրարկում՝ owner_review։ Աղբյուրի բաժիններ՝ 8։

### HN-DOC-HUMAN-VISIBLE-BILINGUAL · documentation.human_visible_bilingual

Մակարդակ՝ MANDATORY · Տիրույթ՝ repository · Դասեր՝ A, B, C

```json
{
  "human_facing": true,
  "required_languages": [
    "en",
    "hy"
  ],
  "contract": "English and Հայերեն sections are both non-empty",
  "classification": "deterministic_path_and_marker_convention"
}
```

Հաստատում՝ explicit_owner։ Կիրարկում՝ bilingual_document_validator։ Աղբյուրի բաժիններ՝ ։

### HN-EXPLICIT-IDENTITY · git.user.useConfigOnly

Մակարդակ՝ MANDATORY · Տիրույթ՝ environment · Դասեր՝ A, B, C

```json
"true"
```

Հաստատում՝ explicit_owner։ Կիրարկում՝ preflight։ Աղբյուրի բաժիններ՝ 12։

### HN-FILES · repository.files

Մակարդակ՝ RECOMMENDED · Տիրույթ՝ repository · Դասեր՝ A, B, C

```json
{
  "normal_code": [
    "README.md",
    ".gitignore",
    ".editorconfig",
    ".gitattributes"
  ],
  "readme": [
    "purpose",
    "setup",
    "run",
    "tests",
    "ownership"
  ]
}
```

Հաստատում՝ explicit_owner։ Կիրարկում՝ repository_validator։ Աղբյուրի բաժիններ՝ 19։

### HN-GOVERNANCE · repository.governance_files

Մակարդակ՝ REPO_SPECIFIC · Տիրույթ՝ repository · Դասեր՝ A, B, C

```json
{
  "only_when_justified": [
    "SECURITY.md",
    "CONTRIBUTING.md",
    "CODEOWNERS",
    "issue_templates",
    "PR_template",
    "dependabot.yml",
    ".github/workflows",
    "architecture_docs",
    "release_docs"
  ],
  "mechanical_scaffolding": false
}
```

Հաստատում՝ explicit_owner։ Կիրարկում՝ registration_and_owner_review։ Աղբյուրի բաժիններ՝ 20։

### HN-IDENTITY · github.identity

Մակարդակ՝ MANDATORY · Տիրույթ՝ environment · Դասեր՝ A, B, C

```json
"HouseNet-Projects"
```

Հաստատում՝ explicit_owner։ Կիրարկում՝ preflight։ Աղբյուրի բաժիններ՝ 2։

### HN-INIT-BRANCH · git.init.defaultBranch

Մակարդակ՝ MANDATORY · Տիրույթ՝ environment · Դասեր՝ A, B, C

```json
"main"
```

Հաստատում՝ explicit_owner։ Կիրարկում՝ preflight։ Աղբյուրի բաժիններ՝ 12։

### HN-LEVELS · policy.levels

Մակարդակ՝ MANDATORY · Տիրույթ՝ control_plane · Դասեր՝ A, B, C

```json
{
  "MANDATORY": "owner_override_only",
  "RECOMMENDED": "preferred_unless_justified",
  "REPO_SPECIFIC": "purpose_class_technology_risk_deployment_sensitivity",
  "missing_context": "ask_or_recommend"
}
```

Հաստատում՝ explicit_owner։ Կիրարկում՝ schema_validator։ Աղբյուրի բաժիններ՝ 28։

### HN-LICENSE · repository.license

Մակարդակ՝ MANDATORY · Տիրույթ՝ repository · Դասեր՝ A, B, C

```json
{
  "automatic_open_source": false,
  "public_transition": "separate_license_review"
}
```

Հաստատում՝ explicit_owner։ Կիրարկում՝ repository_validator։ Աղբյուրի բաժիններ՝ 21։

### HN-METHODS · merge.methods

Մակարդակ՝ RECOMMENDED · Տիրույթ՝ repository · Դասեր՝ A, B, C

```json
{
  "squash": true,
  "merge_commit": false,
  "rebase": false,
  "auto_merge": false,
  "delete_merged_working_branches": true,
  "exception": "owner_approved_architectural_reason"
}
```

Հաստատում՝ explicit_owner։ Կիրարկում՝ repository_settings_audit։ Աղբյուրի բաժիններ՝ 11։

### HN-MIGRATION-STAGED-ADOPTION · migration.lifecycle

Մակարդակ՝ MANDATORY · Տիրույթ՝ repository · Դասեր՝ A, B, C

```json
{
  "stages": [
    "DISCOVERED",
    "QUARANTINED",
    "AUDITED",
    "PROPOSED",
    "OWNER_APPROVED",
    "MIGRATED",
    "CERTIFIED",
    "CANONICAL"
  ],
  "direct_legacy_to_canonical": false,
  "destructive_cleanup_during_intake": false
}
```

Հաստատում՝ explicit_owner։ Կիրարկում՝ migration_registry_and_import_validator։ Աղբյուրի բաժիններ՝ ։

### HN-NAMESPACE · github.namespace

Մակարդակ՝ MANDATORY · Տիրույթ՝ repository · Դասեր՝ A, B, C

```json
"HouseNet-Projects"
```

Հաստատում՝ explicit_owner։ Կիրարկում՝ repository_validator։ Աղբյուրի բաժիններ՝ 2։

### HN-NAMING · repository.naming

Մակարդակ՝ MANDATORY · Տիրույթ՝ repository · Դասեր՝ A, B, C

```json
{
  "format": "^house-net-[a-z0-9]+(?:-[a-z0-9]+)*$",
  "avoid": [
    "final",
    "final-v2",
    "test123",
    "new-project",
    "stuff"
  ],
  "exception": "justified_product_convention",
  "exceptions": [
    ".github",
    "account-profile"
  ]
}
```

Հաստատում՝ explicit_owner։ Կիրարկում՝ repository_registration_schema_and_validator։ Աղբյուրի բաժիններ՝ 7։

### HN-OPERATING-FLOW · engineering.operating_flow

Մակարդակ՝ MANDATORY · Տիրույթ՝ environment · Դասեր՝ A, B, C

```json
[
  "verify_identity",
  "read",
  "understand",
  "classify",
  "recommend",
  "owner_ok",
  "execute",
  "verify",
  "report"
]
```

Հաստատում՝ explicit_owner։ Կիրարկում՝ owner_review։ Աղբյուրի բաժիններ՝ 29։

### HN-OUT-OF-SCOPE · engineering.out_of_scope

Մակարդակ՝ MANDATORY · Տիրույթ՝ environment · Դասեր՝ A, B, C

```json
{
  "report": true,
  "apply": false
}
```

Հաստատում՝ explicit_owner։ Կիրարկում՝ owner_review։ Աղբյուրի բաժիններ՝ 29։

### HN-PERMISSIONS · actions.permissions

Մակարդակ՝ MANDATORY · Տիրույթ՝ repository · Դասեր՝ A, B, C

```json
{
  "default": "read",
  "broad_write": false,
  "job_permissions": "minimum_required",
  "enable_only_when_useful": true
}
```

Հաստատում՝ explicit_owner։ Կիրարկում՝ workflow_validator։ Աղբյուրի բաժիններ՝ 13։

### HN-PERSON-INDEPENDENT-AUTHORITY · architecture.person_independent_authority

Մակարդակ՝ MANDATORY · Տիրույթ՝ repository · Դասեր՝ A, B, C

```json
{
  "machine_authority_uses": [
    "OWNER",
    "AUTHORIZED_OWNER",
    "HOUSE_NET_OWNER",
    "stable_principal_id"
  ],
  "display_names_optional": true,
  "historical_evidence_exempt": true,
  "literal_person_names_as_machine_keys": "forbidden"
}
```

Հաստատում՝ explicit_owner։ Կիրարկում՝ registration_schema_and_target_validator։ Աղբյուրի բաժիններ՝ ։

### HN-PROPORTIONALITY · engineering.proportionality

Մակարդակ՝ MANDATORY · Տիրույթ՝ environment · Դասեր՝ A, B, C

```json
{
  "qualities": [
    "simple",
    "private",
    "secure",
    "auditable",
    "reproducible",
    "intentional"
  ],
  "maximize_configuration": false
}
```

Հաստատում՝ explicit_owner։ Կիրարկում՝ owner_review։ Աղբյուրի բաժիններ՝ 30։

### HN-PROTECTION · merge.protection

Մակարդակ՝ MANDATORY · Տիրույթ՝ repository · Դասեր՝ A, B, C

```json
{
  "A": "strongest_practical_supported",
  "B": "important_repositories_where_supported",
  "C": "optional_proportional",
  "main": [
    "pull_request",
    "stable_required_checks",
    "block_force_push",
    "block_deletion",
    "resolve_conversations",
    "linear_history_where_appropriate",
    "no_permanent_bypass"
  ],
  "invent_checks": false
}
```

Հաստատում՝ explicit_owner։ Կիրարկում՝ repository_settings_audit։ Աղբյուրի բաժիններ՝ 9։

### HN-PRS · repository.pull_requests

Մակարդակ՝ RECOMMENDED · Տիրույթ՝ repository · Դասեր՝ A, B, C

```json
{
  "answer": [
    "what",
    "why",
    "verification"
  ],
  "risky_add": [
    "risk",
    "rollback"
  ],
  "excessive_paperwork": false
}
```

Հաստատում՝ explicit_owner։ Կիրարկում՝ owner_review։ Աղբյուրի բաժիններ՝ 24։

### HN-PULL · git.pull.ff

Մակարդակ՝ MANDATORY · Տիրույթ՝ environment · Դասեր՝ A, B, C

```json
"only"
```

Հաստատում՝ explicit_owner։ Կիրարկում՝ preflight։ Աղբյուրի բաժիններ՝ 12։

### HN-PURPOSE · engineering.purpose

Մակարդակ՝ MANDATORY · Տիրույթ՝ environment · Դասեր՝ A, B, C

```json
{
  "principle": "Minimum correct configuration for actual risk and purpose; every primitive must have a real purpose."
}
```

Հաստատում՝ explicit_owner։ Կիրարկում՝ owner_review։ Աղբյուրի բաժիններ՝ 1։

### HN-RECLASSIFY · repository.reclassification

Մակարդակ՝ MANDATORY · Տիրույթ՝ repository · Դասեր՝ A, B, C

```json
{
  "requires": "explicit_owner_approval",
  "automatic_governance_change": false
}
```

Հաստատում՝ explicit_owner։ Կիրարկում՝ owner_review։ Աղբյուրի բաժիններ՝ 6։

### HN-REVIEW · merge.review

Մակարդակ՝ MANDATORY · Տիրույթ՝ repository · Դասեր՝ A, B, C

```json
{
  "single_identity_required_approvals": 0,
  "independent_approval_requires_additional_human": "recommend_when_introduced",
  "impossible_requirements": false
}
```

Հաստատում՝ explicit_owner։ Կիրարկում՝ owner_review։ Աղբյուրի բաժիններ՝ 10։

### HN-SCOPE · engineering.scope

Մակարդակ՝ MANDATORY · Տիրույթ՝ repository · Դասեր՝ A, B, C

```json
{
  "clear_purpose": true,
  "unrelated_functionality": false,
  "restructure": "recommend_then_owner_approval"
}
```

Հաստատում՝ explicit_owner։ Կիրարկում՝ owner_review։ Աղբյուրի բաժիններ՝ 25։

### HN-SECRETS · security.secrets

Մակարդակ՝ MANDATORY · Տիրույթ՝ repository · Դասեր՝ A, B, C

```json
{
  "git_history": false,
  "hardcoded": false,
  "storage": [
    "GitHub Secrets",
    "environment secrets",
    "approved external manager",
    "ignored local environment files"
  ],
  "incident": [
    "stop",
    "report_repository_and_secret_identifier_without_value",
    "report_exposure",
    "propose_remediation"
  ],
  "rotation_or_history_rewrite": "exact_owner_approval"
}
```

Հաստատում՝ explicit_owner։ Կիրարկում՝ content_scan_and_owner_review։ Աղբյուրի բաժիններ՝ 18։

### HN-SIGNAL · notifications.delivery

Մակարդակ՝ MANDATORY · Տիրույթ՝ account · Դասեր՝ A, B, C

```json
{
  "wanted": [
    "security_alerts",
    "failed_actions",
    "direct_mentions",
    "participating_conversations"
  ],
  "avoid": [
    "all_activity",
    "every_push",
    "unnecessary_watching",
    "noisy_digests",
    "spam"
  ]
}
```

Հաստատում՝ explicit_owner։ Կիրարկում՝ owner_review։ Աղբյուրի բաժիններ՝ 27։

### HN-SOURCE-OF-TRUTH · migration.source_of_truth

Մակարդակ՝ MANDATORY · Տիրույթ՝ repository · Դասեր՝ A, B, C

```json
{
  "one_canonical_source": true,
  "conflicting_candidates": "block_canonicalization",
  "legacy_preserved": true
}
```

Հաստատում՝ explicit_owner։ Կիրարկում՝ migration_evidence_and_validator։ Աղբյուրի բաժիններ՝ ։

### HN-SOURCES · actions.sources

Մակարդակ՝ MANDATORY · Տիրույթ՝ repository · Դասեր՝ A, B, C

```json
{
  "official": [
    "actions/*"
  ],
  "housenet": "HouseNet-Projects/*",
  "third_party": "reviewed_trusted_and_justified",
  "important_workflows": "prefer_full_commit_sha",
  "read_only_due_diligence": "allowed_for_required_dependency_verification",
  "external_mutations": false
}
```

Հաստատում՝ explicit_owner։ Կիրարկում՝ workflow_validator։ Աղբյուրի բաժիններ՝ 14։

### HN-VERSION-SINGLE-SOURCE · repository.version_single_source

Մակարդակ՝ MANDATORY · Տիրույթ՝ repository · Դասեր՝ A, B, C

```json
{
  "when": "versioned=true",
  "canonical_source": "one_registered_machine_readable_source",
  "preferred_path": "release/manifest.json",
  "version_scheme": "MAJOR.MINOR.PATCH",
  "surface_registry": "required",
  "derived_surfaces": "generated_or_validated",
  "drift": "ci_failure",
  "consumer_versions": "explicit_and_distinct_from_own_version"
}
```

Հաստատում՝ explicit_owner։ Կիրարկում՝ repository_validator_and_ci։ Աղբյուրի բաժիններ՝ ։

### HN-VERSIONING · repository.versioning

Մակարդակ՝ RECOMMENDED · Տիրույթ՝ repository · Դասեր՝ A, B, C

```json
{
  "when": "real_release_lifecycle",
  "preferred": "SemVer vX.Y.Z",
  "mandatory_for_notes_or_experiments": false
}
```

Հաստատում՝ explicit_owner։ Կիրարկում՝ owner_review։ Աղբյուրի բաժիններ՝ 22։


