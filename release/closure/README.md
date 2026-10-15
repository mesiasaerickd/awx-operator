# AWX + Operator + EE: one coordinated closure

This single dev change implements four gates. A successful packaging workflow is not production authorization.

## 1. Security

Known latest Trivy evidence: AWX 0 critical/0 high (limited OS coverage), Operator 0/9 (Red Hat RPM pending vendor fixes), EE 0/4 (SBOM-derived old Python versions despite patched active packages, not proven false positives).

Retrieve the three original Trivy JSON artifacts corresponding to runs in baseline.json. Execute:

    python3 release/closure/closure.py audit --awx awx.json --operator operator.json --ee ee.json --output audit.json

Exit code 2 blocks production for any CRITICAL, HIGH without individual signed/recorded acceptance, incomplete OS-coverage review, missing security approver, ticket or expiry. The optional --review JSON includes fields: approver, ticket, expires (YYYY-MM-DD), os_coverage_review (awx/operator/ee each approved), and accepted_findings (objects with component, id and package). This is a record of independent human approval, not a self-generated waiver. Risk acceptance does not equal zero vulnerabilities. Never suppress Trivy findings or use ignore-unfixed.

## 2. Integration

Publish immutable images to a private registry only after registry/publishing approval. Confirm tag, digest and image identity; fill images.lock.template.json with all three image references and the digests from that registry. Render staging manifests:

    python3 release/closure/closure.py render --lock <approved-lock.json> --output release/closure/generated

Use a non-production isolated Kubernetes cluster. Apply the generated Kustomize overlay to install Operator, wait for CRD awxs.awx.ansible.com to become ready and apply the generated AWX CR. Ensure AWX and EE images come from the locked release. Do not use production.

## 3. Acceptance

In an isolated staging cluster, test Backup and Restore custom resources using disposable data and verify recovery. Provide secret AWX_TOKEN and AWX_DENIED_TOKEN via environment, plus KUBE_CONTEXT (must include staging or test), AWX_URL, AWX_TEST_TEMPLATE_ID, AWX_DENIED_TEMPLATE_ID, AWX_BACKUP_NAME and AWX_RESTORE_NAME. Then run:

    python3 release/closure/closure.py staging --lock <approved-lock.json>

This gate checks Operator and AWX rollouts; live image digest identities; AWX CR; Kubernetes default ServiceAccount RBAC; evidence of completed AWXBackup/AWXRestore; AWX API authentication; denial to a restricted AWX token; and successful actual launch of a staging test job. It aborts on missing data, privileges, images or unsuccessful job. Database restore is never invoked automatically. Run after creating the staging environment and verifying backup/restore in the disposable cluster.

## 4. Production preparation and rollback

The render command creates awx-cr.json, kustomization.yaml, images.lock.json and ROLLBACK.md under its output folder. Collect security audit, staging acceptance log, immutable image attestations, verified database restore, maintenance window and human approvals. Only then review a PR from dev to prd. Production deployment is separate and requires explicit approval. Image publishing, applying manifests to a Kubernetes cluster and prod rollback have NOT occurred in this change.

Required blockers right now: 13 HIGH, limited OS coverage, no published candidate image or staging connection, no signed risk review, and no live Kubernetes integration. A green Actions workflow only confirms the closure tools and pinned earlier CI successes.

## Consolidated CI sanity validation
The closure workflow performs all gate unit tests and renders the actual Operator
Kustomize overlay and AWX CR using deliberately invalid placeholder image names.
It does not apply manifests or publish images. Runtime staging acceptance is still
required and only runs when an authorized tester supplies a real Kubernetes test
context, registry image digests and AWX staging credentials.

The expensive Operator build/Molecule workflow ignores changes confined to this
closure package or engineering documentation, avoiding redundant CI cycles.

## PostgreSQL as a mandatory fourth release image (October 2026)

The image lock now requires a PostgreSQL entry with an immutable tag and a 64-character sha256 digest, in addition to AWX, Operator and EE. The generated AWX custom resource sets `postgres_image` and `postgres_image_version`. Runtime staging acceptance checks all four image digests.

This DOES NOT certify the Rocky/CentOS mixed-vendor PostgreSQL laboratory image (70 HIGH approximation, missing native OS advisory coverage). The separate `postgres-vendor-qualification.yml` job must first validate an entitled RHEL9 vendor image and version 15.19 without CRITICAL or HIGH detections, including OS scan coverage. Backups, isolated Kubernetes integration and human approval remain mandatory.
