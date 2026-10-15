# AWX PostgreSQL 15.19: production security/compatibility closure

## Current findings (15 October 2026)
- Existing AWX-managed PostgreSQL: 15.12. Do NOT alter existing PVC or StatefulSet as part of CI.
- Experimental cross-vendor image: PostgreSQL 15.19; SQL+restart persistence PASS.
- The experimental image mixes CentOS Stream 9 and Rocky Linux 9 RPM families: **NOT vendor supported**.
- Native Trivy OS scan returned zero OS results; Rocky9 advisory comparison showed **70 HIGH**, **0 CRITICAL**. This is a comparison, NOT a reliable CentOS Stream risk clearance.
- Previous AWX/Operator/EE: 0 CRITICAL, 13 HIGH, incomplete OS coverage in some images. No production approval.

## Supported candidate route
Use `registry.redhat.io/rhel9/postgresql-15` **only if** the authenticated Red Hat-provided image is verified to contain 15.19. A major-version 15 package backport might have a different patch number; the pipeline deliberately requires exact 15.19 until reviewed. Do not cross-install Rocky Linux, PGDG or community RPMs into the Red Hat image.

`.github/workflows/postgres-vendor-qualification.yml` performs:
1. Registry authentication using GitHub Actions secrets `REDHAT_REGISTRY_USER` and `REDHAT_REGISTRY_TOKEN` (service account, not committed).
2. Pull official Red Hat vendor image and record immutable `repo@sha256` digest.
3. Verify PostgreSQL server/client 15.19, UID 26, SCL startup interface, SQL, and disposable volume persistence/restart.
4. Scan native RHEL9 advisories with Trivy and **reject any CRITICAL/HIGH or missing OS-pkg coverage**.
5. Upload JSON + digest evidence only. Do **not** export restricted RHEL image into a public repository or artifact.

If credentials are absent, vendor image is inaccessible, binary version differs, or security gate fails, the pipeline must fail. There is NO fallback to the mixed-vendor image.

## Required before production
- Independent RHEL vendor image entitlement/support review, CVE analysis and qualified SHA256 digest.
- Secure internal registry / imagePullSecret for K3s if a mirror is required. Pin digest in AWX CR `postgres_image` and `postgres_image_version` as supported by AWX Operator.
- Entirely isolated K3s staging instance with matching AWX, Operator, EE and candidate PostgreSQL; not just ephemeral smoke Jobs on existing AWX.
- Exercise PostgreSQL 15.12 -> 15.19 *on a COPY of the database*, not original PVC. Verify AWX migrations, API, job launch, schedules, RBAC, backup and data restore. Do not overwrite AWX production.
- Confirm 15.19 release notes: configuration and possible extension reindex requirements.
- Obtain signed/recorded risk review for unresolved AWX/Operator/EE findings and OS scanner gaps; do not suppress reports.
- Prepare operator-backed database backup and tested restore / maintenance and approval. A Kubernetes rollout alone cannot reverse a database change.
- Formal human change approval and dev->prd PR. This repository's CI must **never** deploy to production.

## No implied certification
CI unit tests and disposable SQL smoke tests are necessary but **not** sufficient for AWX integration or production sign-off. The green lab image export from the previous run cannot authorize a deployment.
