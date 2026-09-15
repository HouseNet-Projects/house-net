# HouseNet policy · 1.0.0

Generated from machine authority. Do not edit by hand. Original approved text is preserved in [source](source/HouseNet-GitHub-Policy-v1.0.md).

## HN-AUTHOR-EMAIL · git.user.email

MANDATORY · environment · Classes A, B, C

```json
"329470240+HouseNet-Projects@users.noreply.github.com"
```

Approval: explicit_owner. Enforcement: preflight. Source sections: 12.

## HN-AUTHOR-NAME · git.user.name

MANDATORY · environment · Classes A, B, C

```json
"ohanyan"
```

Approval: explicit_owner. Enforcement: preflight. Source sections: 12.

## HN-BRANCH · git.default_branch

MANDATORY · repository · Classes A, B, C

```json
"main"
```

Approval: explicit_owner. Enforcement: repository_settings_audit. Source sections: 8.

## HN-BRANCH-NAMES · git.branch_names

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

## HN-CI · actions.ci

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

## HN-CLASS-A · classification.A

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

## HN-CLASS-B · classification.B

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

## HN-CLASS-C · classification.C

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

## HN-CLASSIFICATION · repository.classification

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

## HN-COMMITS · git.commit_messages

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

## HN-CONFIGURATION · github.configuration_change

MANDATORY · account · Classes A, B, C

```json
{
  "requires": "explicit_owner_approval",
  "silence_is_approval": false
}
```

Approval: explicit_owner. Enforcement: owner_review. Source sections: 2.

## HN-CREATE · repository.creation_baseline

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

## HN-CREATION · repository.creation

MANDATORY · repository · Classes A, B, C

```json
{
  "requires": "explicit_owner_instruction",
  "recommendation_is_not_approval": true
}
```

Approval: explicit_owner. Enforcement: registry_and_owner_review. Source sections: 2.

## HN-DEPENDENCIES · security.dependencies

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

## HN-DEPLOYMENT · actions.deployment

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

## HN-DEPRECATION · repository.deprecation

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

## HN-DESTRUCTIVE · operation.destructive

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

## HN-DEVELOPMENT · git.development_flow

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

## HN-EXPLICIT-IDENTITY · git.user.useConfigOnly

MANDATORY · environment · Classes A, B, C

```json
"true"
```

Approval: explicit_owner. Enforcement: preflight. Source sections: 12.

## HN-FILES · repository.files

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

## HN-GOVERNANCE · repository.governance_files

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

## HN-IDENTITY · github.identity

MANDATORY · environment · Classes A, B, C

```json
"HouseNet-Projects"
```

Approval: explicit_owner. Enforcement: preflight. Source sections: 2.

## HN-INIT-BRANCH · git.init.defaultBranch

MANDATORY · environment · Classes A, B, C

```json
"main"
```

Approval: explicit_owner. Enforcement: preflight. Source sections: 12.

## HN-LEVELS · policy.levels

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

## HN-LICENSE · repository.license

MANDATORY · repository · Classes A, B, C

```json
{
  "automatic_open_source": false,
  "public_transition": "separate_license_review"
}
```

Approval: explicit_owner. Enforcement: repository_validator. Source sections: 21.

## HN-METHODS · merge.methods

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

## HN-NAMESPACE · github.namespace

MANDATORY · repository · Classes A, B, C

```json
"HouseNet-Projects"
```

Approval: explicit_owner. Enforcement: repository_validator. Source sections: 2.

## HN-NAMING · repository.naming

RECOMMENDED · repository · Classes A, B, C

```json
{
  "format": "lowercase-kebab-case",
  "avoid": [
    "final",
    "final-v2",
    "test123",
    "new-project",
    "stuff"
  ],
  "exception": "justified_product_convention"
}
```

Approval: explicit_owner. Enforcement: repository_validator. Source sections: 7.

## HN-OPERATING-FLOW · engineering.operating_flow

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

## HN-OUT-OF-SCOPE · engineering.out_of_scope

MANDATORY · environment · Classes A, B, C

```json
{
  "report": true,
  "apply": false
}
```

Approval: explicit_owner. Enforcement: owner_review. Source sections: 29.

## HN-PERMISSIONS · actions.permissions

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

## HN-PROPORTIONALITY · engineering.proportionality

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

## HN-PROTECTION · merge.protection

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

## HN-PRS · repository.pull_requests

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

## HN-PULL · git.pull.ff

MANDATORY · environment · Classes A, B, C

```json
"only"
```

Approval: explicit_owner. Enforcement: preflight. Source sections: 12.

## HN-PURPOSE · engineering.purpose

MANDATORY · environment · Classes A, B, C

```json
{
  "principle": "Minimum correct configuration for actual risk and purpose; every primitive must have a real purpose."
}
```

Approval: explicit_owner. Enforcement: owner_review. Source sections: 1.

## HN-RECLASSIFY · repository.reclassification

MANDATORY · repository · Classes A, B, C

```json
{
  "requires": "explicit_owner_approval",
  "automatic_governance_change": false
}
```

Approval: explicit_owner. Enforcement: owner_review. Source sections: 6.

## HN-REVIEW · merge.review

MANDATORY · repository · Classes A, B, C

```json
{
  "single_identity_required_approvals": 0,
  "independent_approval_requires_additional_human": "recommend_when_introduced",
  "impossible_requirements": false
}
```

Approval: explicit_owner. Enforcement: owner_review. Source sections: 10.

## HN-SCOPE · engineering.scope

MANDATORY · repository · Classes A, B, C

```json
{
  "clear_purpose": true,
  "unrelated_functionality": false,
  "restructure": "recommend_then_owner_approval"
}
```

Approval: explicit_owner. Enforcement: owner_review. Source sections: 25.

## HN-SECRETS · security.secrets

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

## HN-SIGNAL · notifications.delivery

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

## HN-SOURCES · actions.sources

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

## HN-VERSIONING · repository.versioning

RECOMMENDED · repository · Classes A, B, C

```json
{
  "when": "real_release_lifecycle",
  "preferred": "SemVer vX.Y.Z",
  "mandatory_for_notes_or_experiments": false
}
```

Approval: explicit_owner. Enforcement: owner_review. Source sections: 22.

